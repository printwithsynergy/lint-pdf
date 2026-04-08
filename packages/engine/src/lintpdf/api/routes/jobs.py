"""Job submission and retrieval endpoints."""

from __future__ import annotations

import asyncio
import logging
import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.config import get_settings
from lintpdf.api.database import get_db
from lintpdf.api.middleware import check_rate_limit
from lintpdf.api.models import Job, JobFinding, JobStatus, Tenant
from lintpdf.api.schemas import (
    FindingResponse,
    JobCreateResponse,
    JobListResponse,
    JobResponse,
    JobSummaryResponse,
)
from lintpdf.api.storage import get_storage
from lintpdf.api.upload_security import PDF_TYPES, validate_upload
from lintpdf.tenants.models import RATE_LIMIT_WARN_THRESHOLD

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

_file_param = File(..., description="PDF file to preflight")
_profile_param = Form(default="lintpdf-default", description="Profile to use")
_ai_enabled_param = Form(
    default=None,
    description=(
        "Per-job AI override. If true, AI analyzers run regardless of the "
        "profile's ai.enabled setting (subject to tenant entitlements). "
        "If false, AI is force-disabled. If unset, profile setting wins."
    ),
)
_ai_categories_param = Form(
    default=None,
    description=(
        "Comma-separated AI categories to enable for this job (overrides "
        "profile.ai.categories). Only applies when ``ai_enabled`` is true."
    ),
)
_ai_features_param = Form(
    default=None,
    description=(
        "Comma-separated AI feature slugs to enable for this job (overrides "
        "profile.ai.features). Only applies when ``ai_enabled`` is true."
    ),
)


def _send_rate_warning_if_needed(tenant: Tenant, usage: object) -> None:  # skipcq: PY-R1000
    """Fire a rate-limit warning or overage notice email.

    Uses a Redis key to deduplicate — only one email per threshold per day.
    """
    from lintpdf.api.middleware import UsageInfo, get_redis_client
    from lintpdf.tenants.models import RATE_LIMIT_OVERAGE_THRESHOLD

    if not isinstance(usage, UsageInfo):
        return

    contact = getattr(tenant, "contact_email", None)
    if not contact:
        return

    threshold = None
    if usage.percentage >= RATE_LIMIT_OVERAGE_THRESHOLD:
        threshold = RATE_LIMIT_OVERAGE_THRESHOLD
    elif usage.percentage >= RATE_LIMIT_WARN_THRESHOLD:
        threshold = RATE_LIMIT_WARN_THRESHOLD
    else:
        return

    # Deduplicate via Redis — one warning per threshold per day
    redis = get_redis_client()
    if redis is not None:
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        warn_key = f"rate_warn:{tenant.id}:{today}:{threshold}"
        try:
            already_sent = redis.set(warn_key, "1", nx=True, ex=86400)
            if not already_sent:
                return
        except Exception:
            logger.debug("Redis dedup check failed — sending warning anyway")

    try:
        if threshold == RATE_LIMIT_OVERAGE_THRESHOLD and usage.overage_enabled:
            from lintpdf.email.service import send_overage_started

            send_overage_started(
                to=contact,
                tenant_name=tenant.name,
                used=usage.used,
                limit=usage.limit,
                rate_cents=usage.overage_rate_cents,
                cost_cents=usage.overage_cost_cents,
            )
        else:
            from lintpdf.email.service import send_rate_limit_warning

            send_rate_limit_warning(
                to=contact,
                tenant_name=tenant.name,
                used=usage.used,
                limit=usage.limit,
            )
    except Exception:
        logger.exception("Failed to send rate limit warning email")


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(  # skipcq: PY-R1000
    file: UploadFile = _file_param,
    profile_id: str = _profile_param,
    jdf_file: UploadFile | None = File(default=None, description="Optional JDF/XJDF sidecar"),
    ai_enabled: bool | None = _ai_enabled_param,
    ai_categories: str | None = _ai_categories_param,
    ai_features: str | None = _ai_features_param,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JSONResponse:
    """Submit a PDF for preflight checking.

    The job is processed asynchronously. Use GET /api/v1/jobs/{job_id}
    to check status and retrieve results.
    """
    # Check rate limit (raises 429 if hard limit exceeded)
    usage = check_rate_limit(tenant)

    # Validate ``profile_id`` exists at submit time so clients get a clean
    # 404 instead of a queued job that silently fails in the worker. This
    # also matches the test contract: nonexistent profile → 404.
    from lintpdf.profiles.registry import ProfileRegistry

    if not ProfileRegistry().has(profile_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found",
        )

    content = await validate_upload(
        file,
        allowed_types=PDF_TYPES,
        max_size_bytes=tenant.max_file_size_mb * 1024 * 1024,
        settings=get_settings(),
    )

    job_id = uuid_mod.uuid4()

    # Upload PDF to storage (run in thread to avoid blocking event loop)
    storage = get_storage()
    loop = asyncio.get_running_loop()
    file_key = await loop.run_in_executor(
        None,
        storage.upload_pdf,
        str(tenant.id),
        str(job_id),
        content,
    )

    # Parse JDF sidecar if provided
    jdf_overrides = None
    if jdf_file is not None:
        try:
            jdf_content = await jdf_file.read()
            from lintpdf.integrations.jdf_parser import params_to_overrides, parse_jdf

            jdf_params = parse_jdf(jdf_content)
            jdf_overrides = params_to_overrides(jdf_params)
        except Exception:
            logger.warning("Failed to parse JDF sidecar for job %s — ignoring", job_id)

    job = Job(
        id=job_id,
        tenant_id=tenant.id,
        status=JobStatus.PENDING,
        profile_id=profile_id,
        file_key=file_key,
        file_name=file.filename,
        file_size=len(content),
        jdf_overrides=jdf_overrides,
    )
    db.add(job)
    db.commit()

    # Queue the job for async processing
    from lintpdf.queue.tasks import run_preflight
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    # Cache PDF in Redis so the worker can fetch it even if R2 is unreachable
    try:
        from lintpdf.api.middleware import get_redis_client

        redis = get_redis_client()
        if redis is not None:
            cache_key = f"pdf_cache:{file_key}"
            redis.set(cache_key, content, ex=600)  # 10 min TTL
    except Exception:
        logger.debug("Failed to cache PDF in Redis — worker will use R2")

    queue_name = "priority" if entitlements.priority_processing else "default"
    task_args = [str(job_id), profile_id, file_key]
    task_kwargs: dict[str, Any] = {}
    if jdf_overrides:
        task_kwargs["jdf_overrides"] = jdf_overrides
    if ai_enabled is not None:
        task_kwargs["ai_enabled"] = ai_enabled
    if ai_categories:
        task_kwargs["ai_categories"] = [c.strip() for c in ai_categories.split(",") if c.strip()]
    if ai_features:
        task_kwargs["ai_features"] = [f.strip() for f in ai_features.split(",") if f.strip()]
    run_preflight.apply_async(
        args=task_args,
        kwargs=task_kwargs,
        queue=queue_name,
    )

    # Send rate warning email if approaching or exceeding limit
    if usage is not None and (usage.warning or usage.in_overage):
        _send_rate_warning_if_needed(tenant, usage)

    # Build response with rate limit headers
    response_data = JobCreateResponse(job_id=job_id).model_dump(mode="json")
    headers = {}
    if usage is not None:
        headers["X-RateLimit-Limit"] = str(usage.limit)
        headers["X-RateLimit-Remaining"] = str(usage.remaining_included)
        headers["X-RateLimit-Used"] = str(usage.used)
        if usage.in_overage:
            headers["X-RateLimit-Overage"] = "true"
            headers["X-RateLimit-Overage-Count"] = str(usage.overage_count)
            headers["X-RateLimit-Overage-Cost-Cents"] = str(usage.overage_cost_cents)
            headers["X-RateLimit-Overage-Rate-Cents"] = str(usage.overage_rate_cents)

    return JSONResponse(content=response_data, status_code=202, headers=headers)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JobResponse:
    """Get job status and results."""
    # A malformed UUID is just one form of "this job does not exist" — return
    # 404 rather than 422 so clients can rely on a single status code for the
    # "not found" case regardless of how the ID was constructed.
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        ) from exc

    job: Job | None = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    response = JobResponse(
        job_id=job.id,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        profile_id=job.profile_id,
        file_name=job.file_name,
        file_size=job.file_size,
        page_count=job.page_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
        duration_ms=job.duration_ms,
        error_message=job.error_message,
    )

    if job.status == JobStatus.COMPLETE and job.result_json:
        result = job.result_json
        summary = result.get("summary", {})
        response.summary = JobSummaryResponse(
            total_findings=summary.get("total_findings", 0),
            error_count=summary.get("error_count", 0),
            warning_count=summary.get("warning_count", 0),
            advisory_count=summary.get("advisory_count", 0),
            passed=summary.get("passed", True),
            page_count=summary.get("page_count", 0),
            file_size_bytes=summary.get("file_size_bytes", 0),
        )

        findings: list[JobFinding] = db.query(JobFinding).filter(JobFinding.job_id == uid).all()
        response.findings = [
            FindingResponse(
                inspection_id=f.inspection_id,
                severity=f.severity,
                message=f.message,
                page_num=f.page_num,
                details=f.details,
                source=f.source,
                category=f.category,
                bbox=[f.bbox_x0, f.bbox_y0, f.bbox_x1, f.bbox_y1]
                if f.bbox_x0 is not None
                else None,
                object_id=f.object_id,
                object_type=f.object_type,
            )
            for f in findings
        ]

    return response


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JobListResponse:
    """List jobs for the current tenant (paginated)."""
    # Clamp pagination parameters to safe ranges
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    base_query = db.query(Job).filter(Job.tenant_id == tenant.id)
    total = base_query.count()
    offset = (page - 1) * page_size
    jobs: list[Job] = (
        base_query.order_by(Job.created_at.desc()).offset(offset).limit(page_size).all()
    )

    return JobListResponse(
        jobs=[
            JobResponse(
                job_id=j.id,
                status=j.status.value if hasattr(j.status, "value") else str(j.status),
                profile_id=j.profile_id,
                file_name=j.file_name,
                file_size=j.file_size,
                page_count=j.page_count,
                created_at=j.created_at,
                completed_at=j.completed_at,
                duration_ms=j.duration_ms,
            )
            for j in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Cancel or delete a job."""
    # See ``get_job`` — malformed UUID returns 404, not 422.
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        ) from exc

    job: Job | None = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    db.delete(job)
    db.commit()
