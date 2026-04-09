"""Trial submission endpoints for public PDF upload and admin management."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid as uuid_mod

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import verify_admin_key
from lintpdf.api.database import get_db
from lintpdf.api.models import (
    Job,
    JobFinding,
    JobStatus,
    Tenant,
    TrialFile,
    TrialSubmission,
    TrialSubmissionStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["trial"])

MAX_TRIAL_FILES = 5
MAX_TRIAL_FILE_SIZE_MB = 50
MAX_TRIAL_FILE_SIZE_BYTES = MAX_TRIAL_FILE_SIZE_MB * 1024 * 1024
TRIAL_TENANT_NAME = "__trial__"


# ── Helpers ──────────────────────────────────────────────────


def _verify_trial_secret(x_trial_secret: str | None = Header(None)) -> str:
    """Verify the shared trial secret from the marketing site."""
    expected = os.environ.get("LINTPDF_TRIAL_SECRET", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trial submissions not configured.",
        )
    if not x_trial_secret or x_trial_secret != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized.",
        )
    return x_trial_secret


def _get_or_create_trial_tenant(db: Session) -> Tenant:
    """Get or create the dedicated trial tenant."""
    from lintpdf.api.auth import generate_api_key, hash_api_key
    from lintpdf.tenants.models import TenantPlan

    tenant = db.query(Tenant).filter(Tenant.name == TRIAL_TENANT_NAME).first()
    if tenant is not None:
        return tenant

    raw_key = generate_api_key()
    tenant = Tenant(
        name=TRIAL_TENANT_NAME,
        api_key_hash=hash_api_key(raw_key),
        plan=TenantPlan.FREE,
        rate_limit_daily=9999,
        max_file_size_mb=MAX_TRIAL_FILE_SIZE_MB,
        contact_email=None,
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def _check_trial_rate_limit(email: str) -> None:
    """Rate limit: max 3 trial submissions per email per day."""
    try:
        from lintpdf.api.middleware import get_redis_client

        redis = get_redis_client()
        if redis is None:
            return
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"trial_rate:{email.lower()}:{today}"
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 86400)
        if count > 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many trial submissions. Please try again tomorrow.",
            )
    except HTTPException:
        raise
    except Exception:
        logger.debug("Trial rate limit check failed — allowing submission")


async def _queue_preflight_for_file(
    db: Session,
    submission: TrialSubmission,
    tf: TrialFile,
    profile_id: str,
) -> uuid_mod.UUID:
    """Create a preflight job for a trial file and queue the Celery task.

    Shared by the admin manual trigger and the auto-submit path. Caller is
    responsible for commit()'ing the session after one or more calls.
    """
    from lintpdf.api.storage import get_storage

    trial_tenant = _get_or_create_trial_tenant(db)

    storage = get_storage()
    loop = asyncio.get_running_loop()
    pdf_bytes = await loop.run_in_executor(None, storage.download_pdf, tf.file_key)

    job_id = uuid_mod.uuid4()
    file_key = await loop.run_in_executor(
        None, storage.upload_pdf, str(trial_tenant.id), str(job_id), pdf_bytes
    )

    job = Job(
        id=job_id,
        tenant_id=trial_tenant.id,
        status=JobStatus.PENDING,
        profile_id=profile_id,
        file_key=file_key,
        file_name=tf.file_name,
        file_size=tf.file_size,
    )
    db.add(job)

    tf.job_id = job_id
    if submission.status == TrialSubmissionStatus.PENDING:
        submission.status = TrialSubmissionStatus.PROCESSING

    # Queue the preflight task
    from lintpdf.queue.tasks import run_preflight

    run_preflight.apply_async(
        args=[str(job_id), profile_id, file_key],
        queue="default",
    )

    return job_id


# ── Request/Response schemas ─────────────────────────────────


class TrialSubmitResponse(BaseModel):
    submission_id: str
    file_count: int
    message: str


class TrialFileInfo(BaseModel):
    id: str
    file_name: str
    file_size: int
    scan_clean: bool
    job_id: str | None
    job_status: str | None
    created_at: str


class TrialSubmissionDetail(BaseModel):
    id: str
    name: str
    email: str
    company: str | None
    phone: str | None
    file_count: int
    status: str
    admin_notes: str | None
    files: list[TrialFileInfo]
    created_at: str
    updated_at: str


class TrialSubmissionSummary(BaseModel):
    id: str
    name: str
    email: str
    company: str | None
    file_count: int
    status: str
    created_at: str


class TrialListResponse(BaseModel):
    submissions: list[TrialSubmissionSummary]
    total: int
    page: int
    page_size: int


class UpdateTrialRequest(BaseModel):
    status: str | None = None
    admin_notes: str | None = None


# ── Public endpoint ──────────────────────────────────────────


@router.post(
    "/api/v1/trial/submit",
    response_model=TrialSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_trial(
    name: str = Form(..., min_length=1, max_length=255),
    email: str = Form(..., min_length=1, max_length=255),
    company: str = Form(default=""),
    phone: str = Form(default=""),
    files: list[UploadFile] = File(..., description="PDF files to test"),
    db: Session = Depends(get_db),
    _secret: str = Depends(_verify_trial_secret),
) -> JSONResponse:
    """Accept trial PDF uploads from the marketing site."""
    import re

    # Basic email validation
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email."
        )

    if len(files) > MAX_TRIAL_FILES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Maximum {MAX_TRIAL_FILES} files allowed.",
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one PDF file is required.",
        )

    _check_trial_rate_limit(email)

    from lintpdf.api.config import get_settings
    from lintpdf.api.storage import get_storage
    from lintpdf.api.upload_security import PDF_TYPES, validate_upload

    settings = get_settings()
    storage = get_storage()

    submission_id = uuid_mod.uuid4()
    trial_files: list[TrialFile] = []

    for upload_file in files:
        content = await validate_upload(
            upload_file,
            allowed_types=PDF_TYPES,
            max_size_bytes=MAX_TRIAL_FILE_SIZE_BYTES,
            settings=settings,
        )

        file_id = uuid_mod.uuid4()
        file_key = f"trial/{submission_id}/{file_id}.pdf"

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda k=file_key, c=content: storage._get_client().put_object(
                Bucket=storage._bucket_name,
                Key=k,
                Body=c,
                ContentType="application/pdf",
            ),
        )

        trial_files.append(
            TrialFile(
                id=file_id,
                submission_id=submission_id,
                file_name=upload_file.filename or "unnamed.pdf",
                file_size=len(content),
                file_key=file_key,
                scan_clean=True,
            )
        )

    submission = TrialSubmission(
        id=submission_id,
        name=name.strip(),
        email=email.strip().lower(),
        company=company.strip() or None,
        phone=phone.strip() or None,
        file_count=len(trial_files),
        status=TrialSubmissionStatus.PENDING,
    )
    db.add(submission)
    for tf in trial_files:
        db.add(tf)
    db.commit()

    # Auto-submit preflight if enabled via LINTPDF_TRIAL_AUTO_SUBMIT.
    # Failures here must NOT reject the upload — the submission is already saved
    # and an admin can re-run from the dashboard.
    auto_submitted = False
    if settings.trial_auto_submit:
        logger.info(
            "trial.auto_submit",
            extra={"submission_id": str(submission_id), "file_count": len(trial_files)},
        )
        queued_any = False
        for tf in trial_files:
            try:
                await _queue_preflight_for_file(
                    db, submission, tf, settings.trial_auto_submit_profile_id
                )
                queued_any = True
            except Exception:
                logger.exception(
                    "Auto-submit preflight failed for trial file %s", tf.id
                )
        if queued_any:
            db.commit()
            auto_submitted = True

    # Notify admin via email
    try:
        from lintpdf.email.service import get_email_client

        if get_email_client() is not None:
            from lintpdf.email.service import _send

            status_note = (
                "Auto-Submit: ON — preflight queued automatically. "
                "Review the results in your admin dashboard and send the report."
                if auto_submitted
                else "Review and run preflight in your admin dashboard."
            )
            _send(
                to=os.environ.get("LINTPDF_ADMIN_EMAIL", "hello@thinkneverland.com"),
                subject=f"New Trial Submission — {name.strip()} ({len(trial_files)} files)",
                html=f"""\
<div style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #1e293b;">New Trial Upload</h2>
  <table style="border-collapse: collapse; width: 100%; margin: 16px 0;">
    <tr><td style="padding: 8px; color: #64748b;">Name</td><td style="padding: 8px;"><strong>{name.strip()}</strong></td></tr>
    <tr><td style="padding: 8px; color: #64748b;">Email</td><td style="padding: 8px;">{email.strip()}</td></tr>
    <tr><td style="padding: 8px; color: #64748b;">Company</td><td style="padding: 8px;">{company.strip() or "—"}</td></tr>
    <tr><td style="padding: 8px; color: #64748b;">Phone</td><td style="padding: 8px;">{phone.strip() or "—"}</td></tr>
    <tr><td style="padding: 8px; color: #64748b;">Files</td><td style="padding: 8px;"><strong>{len(trial_files)}</strong></td></tr>
  </table>
  <p style="font-size: 14px; color: #64748b;">{status_note}</p>
</div>""",
            )
    except Exception:
        logger.debug("Failed to send admin notification for trial submission")

    return JSONResponse(
        content=TrialSubmitResponse(
            submission_id=str(submission_id),
            file_count=len(trial_files),
            message="Files uploaded successfully. We'll review them and get back to you.",
        ).model_dump(),
        status_code=201,
    )


# ── Admin endpoints ──────────────────────────────────────────


@router.get("/api/v1/admin/trials/config")
async def get_trials_config(
    _key: str = Depends(verify_admin_key),
) -> JSONResponse:
    """Expose the trial auto-submit flag to the admin UI.

    Registered BEFORE ``/api/v1/admin/trials/{submission_id}`` so it doesn't
    get shadowed by the UUID-parameterized route.
    """
    from lintpdf.api.config import get_settings

    settings = get_settings()
    return JSONResponse(
        content={
            "auto_submit": bool(settings.trial_auto_submit),
            "auto_submit_profile_id": settings.trial_auto_submit_profile_id,
        }
    )


@router.get("/api/v1/admin/trials", response_model=TrialListResponse)
async def list_trials(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _key: str = Depends(verify_admin_key),
) -> TrialListResponse:
    """List trial submissions (admin only)."""
    query = db.query(TrialSubmission)
    if status_filter:
        query = query.filter(TrialSubmission.status == status_filter)

    total = query.count()
    submissions = (
        query.order_by(desc(TrialSubmission.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TrialListResponse(
        submissions=[
            TrialSubmissionSummary(
                id=str(s.id),
                name=s.name,
                email=s.email,
                company=s.company,
                file_count=s.file_count,
                status=s.status,
                created_at=s.created_at.isoformat(),
            )
            for s in submissions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/api/v1/admin/trials/{submission_id}", response_model=TrialSubmissionDetail)
async def get_trial(
    submission_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_admin_key),
) -> TrialSubmissionDetail:
    """Get trial submission details with files (admin only)."""
    try:
        uid = uuid_mod.UUID(submission_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid ID.") from exc

    sub = db.query(TrialSubmission).filter(TrialSubmission.id == uid).first()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    files = db.query(TrialFile).filter(TrialFile.submission_id == uid).all()

    # Batch-fetch job statuses
    job_ids = [f.job_id for f in files if f.job_id is not None]
    job_statuses: dict[str, str] = {}
    if job_ids:
        jobs = db.query(Job).filter(Job.id.in_(job_ids)).all()
        job_statuses = {str(j.id): j.status for j in jobs}

    return TrialSubmissionDetail(
        id=str(sub.id),
        name=sub.name,
        email=sub.email,
        company=sub.company,
        phone=sub.phone,
        file_count=sub.file_count,
        status=sub.status,
        admin_notes=sub.admin_notes,
        files=[
            TrialFileInfo(
                id=str(f.id),
                file_name=f.file_name,
                file_size=f.file_size,
                scan_clean=f.scan_clean,
                job_id=str(f.job_id) if f.job_id else None,
                job_status=job_statuses.get(str(f.job_id)) if f.job_id else None,
                created_at=f.created_at.isoformat(),
            )
            for f in files
        ],
        created_at=sub.created_at.isoformat(),
        updated_at=sub.updated_at.isoformat(),
    )


@router.get("/api/v1/admin/trials/{submission_id}/files/{file_id}/download")
async def download_trial_file(
    submission_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_admin_key),
) -> JSONResponse:
    """Get a presigned download URL for a trial file (admin only)."""
    try:
        s_uid = uuid_mod.UUID(submission_id)
        f_uid = uuid_mod.UUID(file_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid ID.") from exc

    tf = db.query(TrialFile).filter(TrialFile.id == f_uid, TrialFile.submission_id == s_uid).first()
    if tf is None:
        raise HTTPException(status_code=404, detail="File not found.")

    from lintpdf.api.storage import get_storage

    storage = get_storage()
    url = storage.generate_presigned_url(tf.file_key, expires_in=3600)

    return JSONResponse(content={"url": url, "file_name": tf.file_name})


@router.post("/api/v1/admin/trials/{submission_id}/files/{file_id}/preflight")
async def run_trial_preflight(
    submission_id: str,
    file_id: str,
    profile_id: str = "lintpdf-default",
    db: Session = Depends(get_db),
    _key: str = Depends(verify_admin_key),
) -> JSONResponse:
    """Run preflight on a trial file (admin only)."""
    try:
        s_uid = uuid_mod.UUID(submission_id)
        f_uid = uuid_mod.UUID(file_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid ID.") from exc

    tf = db.query(TrialFile).filter(TrialFile.id == f_uid, TrialFile.submission_id == s_uid).first()
    if tf is None:
        raise HTTPException(status_code=404, detail="File not found.")

    if tf.job_id is not None:
        # Check if the existing job is still processing
        existing_job = db.query(Job).filter(Job.id == tf.job_id).first()
        if existing_job and existing_job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Preflight already running for this file.",
            )

    sub = db.query(TrialSubmission).filter(TrialSubmission.id == s_uid).first()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    job_id = await _queue_preflight_for_file(db, sub, tf, profile_id)
    db.commit()

    return JSONResponse(
        content={"job_id": str(job_id), "message": "Preflight queued."},
        status_code=202,
    )


@router.post("/api/v1/admin/trials/{submission_id}/send-report")
async def send_trial_report(
    submission_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_admin_key),
) -> JSONResponse:
    """Generate and send a branded report to the trial submitter (admin only)."""
    try:
        s_uid = uuid_mod.UUID(submission_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid ID.") from exc

    sub = db.query(TrialSubmission).filter(TrialSubmission.id == s_uid).first()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    # Find completed jobs
    files = db.query(TrialFile).filter(TrialFile.submission_id == s_uid).all()
    completed_files = [f for f in files if f.job_id is not None]
    if not completed_files:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No preflighted files. Run preflight first.",
        )

    # Check at least one job is complete
    job_ids = [f.job_id for f in completed_files]
    completed_jobs = (
        db.query(Job).filter(Job.id.in_(job_ids), Job.status == JobStatus.COMPLETE).all()
    )
    if not completed_jobs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No preflight jobs have completed yet.",
        )

    trial_tenant = _get_or_create_trial_tenant(db)

    from lintpdf.api.config import get_settings
    from lintpdf.api.storage import get_storage
    from lintpdf.reports.service import BrandingContext, ReportService

    settings = get_settings()
    storage = get_storage()
    service = ReportService(storage, db)

    report_urls: list[str] = []
    total_findings = 0
    all_passed = True

    for job in completed_jobs:
        if job.result_json is None:
            continue

        result_json = dict(job.result_json)
        result_json["job_id"] = str(job.id)
        result_json["profile_id"] = job.profile_id
        result_json["duration_ms"] = job.duration_ms or 0

        findings = db.query(JobFinding).filter(JobFinding.job_id == job.id).all()
        result_json["findings"] = [
            {
                "inspection_id": f.inspection_id,
                "severity": f.severity,
                "message": f.message,
                "page_num": f.page_num,
                "object_id": None,
                "object_type": None,
            }
            for f in findings
        ]

        summary = result_json.get("summary", {})
        total_findings += summary.get("total_findings", 0)
        if not summary.get("passed", True):
            all_passed = False

        branding = BrandingContext()  # Default LintPDF branding

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda _job=job, _result=result_json, _br=branding: service.generate_and_store(
                job_id=str(_job.id),
                tenant_id=str(trial_tenant.id),
                result_json=_result,
                formats=["html"],
                expiry_days=30,
                branding=_br,
                report_base_url=settings.report_base_url,
            ),
        )

        for r in result.reports:
            report_urls.append(r["url"])

    # Send email to the submitter
    if report_urls:
        from lintpdf.email.service import send_trial_report_email

        send_trial_report_email(
            to=sub.email,
            name=sub.name,
            report_urls=report_urls,
            finding_count=total_findings,
            passed=all_passed,
        )

    sub.status = TrialSubmissionStatus.CONTACTED
    db.commit()

    return JSONResponse(
        content={
            "message": f"Report sent to {sub.email}.",
            "report_count": len(report_urls),
        }
    )


@router.patch("/api/v1/admin/trials/{submission_id}")
async def update_trial(
    submission_id: str,
    body: UpdateTrialRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_admin_key),
) -> JSONResponse:
    """Update trial submission status or notes (admin only)."""
    try:
        uid = uuid_mod.UUID(submission_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid ID.") from exc

    sub = db.query(TrialSubmission).filter(TrialSubmission.id == uid).first()
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    if body.status is not None:
        try:
            sub.status = TrialSubmissionStatus(body.status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid status: {body.status}") from exc
    if body.admin_notes is not None:
        sub.admin_notes = body.admin_notes

    db.commit()

    return JSONResponse(content={"id": str(sub.id), "status": sub.status, "updated": True})
