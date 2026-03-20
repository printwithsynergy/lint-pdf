"""Report generation and serving endpoints."""

from __future__ import annotations

import asyncio
import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from grounded.api.auth import get_current_tenant
from grounded.api.database import get_db
from grounded.api.models import Job, JobFinding, ReportToken, Tenant

router = APIRouter(tags=["reports"])


# --- Request/Response schemas ---


class BrandingOverride(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    hide_footer: bool | None = None


class GenerateReportsRequest(BaseModel):
    formats: list[str] = ["html", "pdf"]
    expiry_days: int | None = None
    email_to: str | None = None
    branding: BrandingOverride | None = None


class ReportInfo(BaseModel):
    format: str
    url: str
    token: str
    expires_at: str | None = None


class GenerateReportsResponse(BaseModel):
    reports: list[ReportInfo]


class ReportListItem(BaseModel):
    token: str
    format: str
    expires_at: str | None = None
    created_at: str
    accessed_count: int


class ReportListResponse(BaseModel):
    reports: list[ReportListItem]


# --- Authenticated endpoints ---


@router.post(
    "/api/v1/jobs/{job_id}/reports",
    response_model=GenerateReportsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_reports(  # skipcq: PY-R1000
    job_id: str,
    body: GenerateReportsRequest | None = None,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> GenerateReportsResponse:
    """Generate hosted reports for a completed job."""
    if body is None:
        body = GenerateReportsRequest()

    # Enforce tier-based restrictions
    from grounded.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    # Check report format restrictions
    disallowed = set(body.formats) - set(entitlements.allowed_report_formats)
    if disallowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Your plan does not include report format(s): {', '.join(sorted(disallowed))}. "
                f"Allowed formats: {', '.join(entitlements.allowed_report_formats)}."
            ),
        )

    # Check white-label branding restriction
    if body.branding and not entitlements.whitelabel_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="White-label branding (Livery) requires Scale or Enterprise plan.",
        )

    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid job ID format.",
        ) from exc

    job: Job | None = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if job.result_json is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job has not completed yet.",
        )

    from grounded.api.config import get_settings
    from grounded.api.storage import get_storage
    from grounded.reports.service import BrandingContext, ReportService
    from grounded.tenants.models import PLAN_LIMITS, TenantPlan

    settings = get_settings()
    storage = get_storage()
    service = ReportService(storage, db)

    # Build branding context — only apply tenant brand fields if whitelabel is enabled
    if entitlements.whitelabel_enabled:
        branding = BrandingContext(
            name=tenant.brand_name or "Grounded",
            logo_url=tenant.brand_logo_url,
            primary_color=tenant.brand_primary_color or "#1a3a7a",
            accent_color=tenant.brand_accent_color or "#2563eb",
            footer_text=None if tenant.brand_hide_footer else "Powered by Grounded",
        )
    else:
        branding = BrandingContext()
    if body.branding:
        if body.branding.name:
            branding.name = body.branding.name
        if body.branding.logo_url:
            branding.logo_url = body.branding.logo_url
        if body.branding.primary_color:
            branding.primary_color = body.branding.primary_color
        if body.branding.accent_color:
            branding.accent_color = body.branding.accent_color
        if body.branding.hide_footer is not None:
            branding.footer_text = None if body.branding.hide_footer else "Powered by Grounded"

    # Determine expiry
    expiry_days = body.expiry_days
    if expiry_days is None:
        plan_limits = PLAN_LIMITS.get(TenantPlan(tenant.plan), {})
        expiry_days = tenant.report_default_expiry_days or plan_limits.get(
            "report_default_expiry_days", 7
        )

    # Enrich result_json with job details for template
    result_json = dict(job.result_json)
    result_json["job_id"] = str(job.id)
    result_json["profile_id"] = job.profile_id
    result_json["duration_ms"] = job.duration_ms or 0

    # Add findings from DB
    findings = db.query(JobFinding).filter(JobFinding.job_id == uid).all()
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

    # Run in thread to avoid blocking event loop (storage uploads are sync)
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: service.generate_and_store(
            job_id=str(job.id),
            tenant_id=str(tenant.id),
            result_json=result_json,
            formats=body.formats,
            expiry_days=expiry_days,
            branding=branding,
            report_base_url=settings.report_base_url,
        ),
    )

    return GenerateReportsResponse(
        reports=[ReportInfo(**r) for r in result.reports],
    )


@router.get("/api/v1/jobs/{job_id}/reports", response_model=ReportListResponse)
async def list_reports(
    job_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> ReportListResponse:
    """List existing report tokens for a job."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid job ID format.",
        ) from exc

    tokens = (
        db.query(ReportToken)
        .filter(ReportToken.job_id == uid, ReportToken.tenant_id == tenant.id)
        .all()
    )

    return ReportListResponse(
        reports=[
            ReportListItem(
                token=t.token,
                format=t.format,
                expires_at=t.expires_at.isoformat() if t.expires_at else None,
                created_at=t.created_at.isoformat(),
                accessed_count=t.accessed_count,
            )
            for t in tokens
        ]
    )


@router.delete(
    "/api/v1/jobs/{job_id}/reports/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_report(
    job_id: str,
    token: str,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> None:
    """Revoke a report token and delete from storage."""
    record: ReportToken | None = (
        db.query(ReportToken)
        .filter(
            ReportToken.token == token,
            ReportToken.tenant_id == tenant.id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    # Delete storage file
    try:
        from grounded.api.storage import get_storage

        storage = get_storage()
        file_key = f"reports/{record.tenant_id}/{record.job_id}/report.{record.format}"
        storage.delete_file(file_key)
    except Exception:
        pass  # Best-effort cleanup

    db.delete(record)
    db.commit()


# --- Public endpoints (token-based, no auth) ---


@router.get("/r/{token}")
async def serve_html_report(
    token: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    """Serve an interactive HTML report by token (public, no auth)."""
    from datetime import UTC, datetime

    record: ReportToken | None = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if record.expires_at is not None and datetime.now(UTC) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Report has expired.")

    if record.format != "html":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTML report not found for this token.",
        )

    # Increment access count
    record.accessed_count += 1
    record.last_accessed_at = datetime.now(UTC)
    db.commit()

    # Fetch from storage (run in thread to avoid blocking event loop)
    from grounded.api.storage import get_storage

    storage = get_storage()
    loop = asyncio.get_running_loop()
    content = await loop.run_in_executor(
        None, storage.download_report, str(record.tenant_id), str(record.job_id), "html"
    )

    return HTMLResponse(content=content)


@router.get("/r/{token}.pdf")
async def serve_pdf_report(
    token: str,
    download: int = 0,
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    """Serve a PDF report by token (public, no auth)."""
    from datetime import UTC, datetime

    record: ReportToken | None = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if record.expires_at is not None and datetime.now(UTC) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Report has expired.")

    if record.format != "pdf":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report not found for this token.",
        )

    # Increment access count
    record.accessed_count += 1
    record.last_accessed_at = datetime.now(UTC)
    db.commit()

    # Fetch from storage (run in thread to avoid blocking event loop)
    from grounded.api.storage import get_storage

    storage = get_storage()
    loop = asyncio.get_running_loop()
    content = await loop.run_in_executor(
        None, storage.download_report, str(record.tenant_id), str(record.job_id), "pdf"
    )

    disposition = "attachment" if download else "inline"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="report.pdf"'},
    )
