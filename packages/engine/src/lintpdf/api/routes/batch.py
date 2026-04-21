"""Batch operations API endpoints.

Allows submitting multiple PDFs for preflight in a single request,
checking batch status, and getting aggregated results.

Batches are not persisted in a dedicated table — instead we store the
batch_id → [job_ids] mapping in Redis. This keeps the implementation
lightweight (no DB migration required) while still giving users a single
ID to poll against.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.config import get_settings
from lintpdf.api.database import get_db
from lintpdf.api.middleware import check_burst_rate_limit, check_rate_limit, get_redis_client
from lintpdf.api.models import Job, JobStatus, Tenant
from lintpdf.api.storage import get_storage
from lintpdf.api.upload_security import PDF_TYPES, validate_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])

# Redis key prefix for batch metadata
_BATCH_KEY_PREFIX = "batch:"
# TTL for batch records (24 hours — enough for long-running preflights)
_BATCH_TTL_SECONDS = 86_400

# Matches field names used by various multipart clients for file arrays:
#   files, files[], files[0], files[1], file_0, file_1, file
_FILE_FIELD_RE = re.compile(r"^(files?)(\[\d*\]|_\d+)?$")


class BatchJobInfo(BaseModel):
    """Information about a single job in a batch."""

    job_id: str
    file_name: str
    status: str = "pending"


class BatchSubmitResponse(BaseModel):
    """Response after submitting a batch."""

    batch_id: str
    job_count: int
    jobs: list[BatchJobInfo]
    status: str = "submitted"


class BatchStatusResponse(BaseModel):
    """Status of a batch operation."""

    batch_id: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    status: str  # submitted, processing, complete, failed, partial
    jobs: list[BatchJobInfo] = Field(default_factory=list)
    summary: dict[str, Any] | None = None


def _store_batch(batch_id: str, tenant_id: str, job_ids: list[str]) -> None:
    """Persist batch_id → job_ids mapping in Redis (best-effort)."""
    redis = get_redis_client()
    if redis is None:
        logger.warning("Redis not configured — batch %s won't be retrievable via GET", batch_id)
        return
    key = f"{_BATCH_KEY_PREFIX}{batch_id}"
    payload = json.dumps({"tenant_id": tenant_id, "job_ids": job_ids})
    try:
        redis.set(key, payload, ex=_BATCH_TTL_SECONDS)
    except Exception:
        logger.exception("Failed to store batch %s in Redis", batch_id)


def _load_batch(batch_id: str, tenant_id: str) -> list[str]:
    """Load job_ids for a batch from Redis. Raises 404 if not found."""
    redis = get_redis_client()
    if redis is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch tracking requires Redis, which is not configured.",
        )
    key = f"{_BATCH_KEY_PREFIX}{batch_id}"
    try:
        raw = redis.get(key)
    except Exception as exc:
        logger.exception("Redis lookup failed for batch %s", batch_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batch storage unavailable.",
        ) from exc

    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found or expired.",
        )

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)

    if data.get("tenant_id") != tenant_id:
        # Don't leak that the batch exists for another tenant
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found or expired.",
        )

    return list(data.get("job_ids", []))


def _aggregate_status(jobs: list[Job]) -> str:
    """Derive a batch-level status from the set of job statuses."""
    if not jobs:
        return "submitted"

    statuses = {job.status for job in jobs}
    if JobStatus.PENDING in statuses or JobStatus.PROCESSING in statuses:
        return "processing"
    if statuses == {JobStatus.COMPLETE}:
        return "complete"
    if statuses == {JobStatus.FAILED}:
        return "failed"
    # Mixed terminal states
    return "partial"


async def _extract_batch_form(
    request: Request,
) -> tuple[list[UploadFile], str]:
    """Parse multipart form, returning (uploads, profile_id).

    Accepts flexible field names for files: ``files``, ``files[]``,
    ``files[0]``, ``files[1]``, ``file_0``, ``file``. This matches the
    variations different HTTP clients produce when sending arrays.
    """
    try:
        form = await request.form()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse multipart form: {exc}",
        ) from exc

    uploads: list[UploadFile] = []
    profile_id = "lintpdf-default"

    # Iterate keys so we can use getlist — multi_items() isn't consistently
    # available across Starlette versions for FormData.
    for key in list(form.keys()):
        if key == "profile_id":
            raw = form.get("profile_id")
            if isinstance(raw, str) and raw:
                profile_id = raw
            continue
        if not _FILE_FIELD_RE.match(key):
            continue
        for value in form.getlist(key):
            # Duck-type check for UploadFile — the canonical attributes are
            # ``filename`` and ``read``. This avoids isinstance pitfalls when
            # Starlette's UploadFile is re-exported or shadowed.
            if hasattr(value, "filename") and hasattr(value, "read"):
                uploads.append(value)  # type: ignore[arg-type]

    if not uploads:
        # Log received keys once to help debug unexpected client formats —
        # they'll show up in engine logs without leaking file contents.
        logger.info(
            "batch submit: no files matched; received keys=%s",
            list(form.keys()),
        )

    return uploads, profile_id


@router.post(
    "/submit",
    response_model=BatchSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_batch(
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BatchSubmitResponse:
    """Submit a batch of PDFs for preflight processing.

    Accepts multipart form data with one or more file fields and an
    optional ``profile_id`` (defaults to ``lintpdf-default``). Each file
    becomes an individual Job; they are linked by a synthetic
    ``batch_id`` stored in Redis with a 24h TTL.

    File fields are accepted in any of these shapes:
        files=...&files=...          (repeated, traditional HTML)
        files[]=...&files[]=...      (PHP-style array)
        files[0]=...&files[1]=...    (indexed array, what Playwright sends)
        file_0=...&file_1=...        (numbered singular)
    """
    files, profile_id = await _extract_batch_form(request)

    if not files:
        # Echo back what we actually saw so clients can debug mismatched
        # field names without having to inspect server logs.
        try:
            form = await request.form()
            debug_keys = list(form.keys())
        except Exception:
            debug_keys = []
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "At least one file is required. Expected fields named "
                "'files', 'files[]', 'files[N]', 'file', or 'file_N'. "
                f"Received keys: {debug_keys}"
            ),
        )

    batch_id = str(uuid_mod.uuid4())
    storage = get_storage()
    loop = asyncio.get_running_loop()
    settings = get_settings()

    from lintpdf.queue.tasks import run_preflight
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    queue_name = "priority" if entitlements.priority_processing else "default"

    job_infos: list[BatchJobInfo] = []
    job_ids: list[str] = []
    # Collect (job_id, file_key) pairs so we can queue tasks AFTER commit.
    # Queueing before commit is racy: a worker may pick up the task and
    # query the DB before the row is visible, causing the job to silently
    # never run.
    pending_queue: list[tuple[str, str]] = []

    for upload in files:
        # Each file counts against the rate limit individually.
        check_burst_rate_limit(tenant)
        check_rate_limit(tenant)

        content = await validate_upload(
            upload,
            allowed_types=PDF_TYPES,
            max_size_bytes=tenant.max_file_size_mb * 1024 * 1024,
            settings=settings,
        )

        job_id = uuid_mod.uuid4()
        file_key = await loop.run_in_executor(
            None,
            storage.upload_pdf,
            str(tenant.id),
            str(job_id),
            content,
        )

        job = Job(
            id=job_id,
            tenant_id=tenant.id,
            status=JobStatus.PENDING,
            profile_id=profile_id,
            file_key=file_key,
            file_name=upload.filename or "unnamed.pdf",
            file_size=len(content),
        )
        db.add(job)

        # Cache PDF in Redis so the worker can fetch it even if storage is slow
        try:
            redis = get_redis_client()
            if redis is not None:
                redis.set(f"pdf_cache:{file_key}", content, ex=600)
        except Exception:
            logger.debug("Failed to cache PDF in Redis — worker will use storage")

        pending_queue.append((str(job_id), file_key))
        job_ids.append(str(job_id))
        job_infos.append(
            BatchJobInfo(
                job_id=str(job_id),
                file_name=upload.filename or "unnamed.pdf",
                status="pending",
            )
        )

    db.commit()

    # Queue Celery tasks only after the DB transaction commits, so that
    # the worker is guaranteed to see the row when it loads the job.
    for queued_job_id, queued_file_key in pending_queue:
        run_preflight.apply_async(
            args=[queued_job_id, profile_id, queued_file_key],
            queue=queue_name,
        )

    _store_batch(batch_id, str(tenant.id), job_ids)

    return BatchSubmitResponse(
        batch_id=batch_id,
        job_count=len(job_infos),
        jobs=job_infos,
    )


@router.get("/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BatchStatusResponse:
    """Get the status of a batch operation."""
    job_ids = _load_batch(batch_id, str(tenant.id))

    try:
        uids = [uuid_mod.UUID(jid) for jid in job_ids]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch contains malformed job IDs.",
        ) from exc

    jobs: list[Job] = db.query(Job).filter(Job.id.in_(uids), Job.tenant_id == tenant.id).all()

    completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETE)
    failed = sum(1 for j in jobs if j.status == JobStatus.FAILED)
    pending = sum(1 for j in jobs if j.status in (JobStatus.PENDING, JobStatus.PROCESSING))

    job_infos = [
        BatchJobInfo(
            job_id=str(j.id),
            file_name=j.file_name or "unnamed.pdf",
            status=str(j.status),
        )
        for j in jobs
    ]

    return BatchStatusResponse(
        batch_id=batch_id,
        total_jobs=len(job_ids),
        completed_jobs=completed,
        failed_jobs=failed,
        pending_jobs=pending,
        status=_aggregate_status(jobs),
        jobs=job_infos,
    )


@router.get("/{batch_id}/summary")
async def get_batch_summary(
    batch_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    """Get aggregated summary of all completed jobs in a batch."""
    job_ids = _load_batch(batch_id, str(tenant.id))

    try:
        uids = [uuid_mod.UUID(jid) for jid in job_ids]
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch contains malformed job IDs.",
        ) from exc

    jobs: list[Job] = db.query(Job).filter(Job.id.in_(uids), Job.tenant_id == tenant.id).all()

    # Roll up severity counts across all jobs' result_json summaries.
    total_findings = 0
    total_errors = 0
    total_warnings = 0
    total_info = 0

    for j in jobs:
        result = j.result_json or {}
        summary = result.get("summary") if isinstance(result, dict) else None
        if not isinstance(summary, dict):
            continue
        total_findings += int(summary.get("total", 0) or 0)
        total_errors += int(summary.get("error", summary.get("errors", 0)) or 0)
        total_warnings += int(summary.get("warning", summary.get("warnings", 0)) or 0)
        total_info += int(summary.get("info", summary.get("advisory", 0)) or 0)

    return {
        "batch_id": batch_id,
        "total_jobs": len(job_ids),
        "completed_jobs": sum(1 for j in jobs if j.status == JobStatus.COMPLETE),
        "failed_jobs": sum(1 for j in jobs if j.status == JobStatus.FAILED),
        "status": _aggregate_status(jobs),
        "summary": {
            "total_findings": total_findings,
            "errors": total_errors,
            "warnings": total_warnings,
            "info": total_info,
        },
        "jobs": [
            {
                "job_id": str(j.id),
                "file_name": j.file_name,
                "status": str(j.status),
                "page_count": j.page_count,
            }
            for j in jobs
        ],
    }
