"""Report generation and serving endpoints."""

from __future__ import annotations

import asyncio
import uuid as uuid_mod
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import BrandProfile, BrandProfileType, Job, JobFinding, ReportToken, Tenant

if TYPE_CHECKING:
    from lintpdf.reports.service import BrandingContext

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
    detail_level: str = "standard"  # "executive", "standard", "comprehensive"
    summary_page: str | None = None  # "prepend" (default ON), "only", "off"
    # When true, anonymous share-link viewers at /view/{token} can draw
    # annotations on the interactive viewer after providing an email via
    # the X-Visitor-Email header. Defaults to read-only (false) so
    # existing share behaviour is unchanged.
    allow_annotations: bool = False


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


# --- Branding resolution ---


def _resolve_branding(
    tenant: Tenant,
    override: object | None,
    whitelabel_enabled: bool,
    db: Session,
) -> tuple[BrandingContext, BrandProfile | None]:
    """Resolve branding using the hierarchy: per-call > brand profile > tenant defaults > LintPDF.

    Profile types:
    - CUSTOM: use the profile's brand fields
    - LINTPDF: use LintPDF default branding
    - NONE: blank everything (blind/neutral mode)

    Returns:
        (branding_context, active_brand_profile) — the active profile is
        returned alongside so callers can pass it to
        ``resolve_report_base_url()`` without re-querying the DB.
    """
    from lintpdf.reports.service import BrandingContext

    # Start with LintPDF defaults
    branding = BrandingContext()
    profile: BrandProfile | None = None

    # If whitelabel enabled, check for a default brand profile
    if whitelabel_enabled and tenant.default_brand_profile_id:
        profile = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.id == tenant.default_brand_profile_id,
                BrandProfile.tenant_id == tenant.id,
            )
            .first()
        )
        if profile:
            if profile.profile_type == BrandProfileType.NONE:
                # Blind mode: generic "Preflight Report" with no branding
                branding = BrandingContext(
                    name="",
                    logo_url=None,
                    primary_color="#6b7280",
                    accent_color="#9ca3af",
                    footer_text=None,
                )
            elif profile.profile_type == BrandProfileType.CUSTOM:
                branding = BrandingContext(
                    name=profile.brand_name or "LintPDF",
                    logo_url=profile.logo_url,
                    primary_color=profile.primary_color or "#1a3a7a",
                    accent_color=profile.accent_color or "#2563eb",
                    footer_text=None
                    if profile.hide_footer
                    else (profile.footer_text or "Powered by LintPDF"),
                )
            # LINTPDF type: keep defaults (already set)

    elif whitelabel_enabled:
        # No brand profile but whitelabel enabled — use legacy tenant brand fields
        branding = BrandingContext(
            name=tenant.brand_name or "LintPDF",
            logo_url=tenant.brand_logo_url,
            primary_color=tenant.brand_primary_color or "#1a3a7a",
            accent_color=tenant.brand_accent_color or "#2563eb",
            footer_text=None if tenant.brand_hide_footer else "Powered by LintPDF",
        )

    # Per-call overrides (highest priority)
    if override:
        override if isinstance(override, dict) else (
            override.__dict__ if hasattr(override, "__dict__") else {}
        )
        if hasattr(override, "name") and override.name:  # type: ignore[union-attr]
            branding.name = override.name  # type: ignore[union-attr]
        if hasattr(override, "logo_url") and override.logo_url:  # type: ignore[union-attr]
            branding.logo_url = override.logo_url  # type: ignore[union-attr]
        if hasattr(override, "primary_color") and override.primary_color:  # type: ignore[union-attr]
            branding.primary_color = override.primary_color  # type: ignore[union-attr]
        if hasattr(override, "accent_color") and override.accent_color:  # type: ignore[union-attr]
            branding.accent_color = override.accent_color  # type: ignore[union-attr]
        if hasattr(override, "hide_footer") and override.hide_footer is not None:  # type: ignore[union-attr]
            branding.footer_text = None if override.hide_footer else "Powered by LintPDF"  # type: ignore[union-attr]

    return branding, profile


# --- Authenticated endpoints ---


@router.post(
    "/api/v1/jobs/{job_id}/reports",
    response_model=GenerateReportsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_reports(  # skipcq: PY-R1000
    job_id: str,
    body: GenerateReportsRequest | None = None,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> GenerateReportsResponse:
    """Generate hosted reports for a completed job."""
    if body is None:
        body = GenerateReportsRequest()

    # Enforce tier-based restrictions
    from lintpdf.tenants.entitlements import resolve_entitlements

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
            detail=f"Invalid job id: '{job_id}' is not a valid UUID.",
        ) from exc

    job: Job | None = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if job.result_json is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job has not completed yet.",
        )

    from lintpdf.api.config import get_settings
    from lintpdf.api.storage import get_storage
    from lintpdf.reports.service import ReportService, resolve_report_base_url
    from lintpdf.tenants.models import PLAN_LIMITS, TenantPlan

    settings = get_settings()
    storage = get_storage()
    service = ReportService(storage, db)

    # Build branding context — resolve from brand profile hierarchy.
    # We also get the active profile back so we can pass it to the report
    # base URL resolver (per-profile custom domains beat tenant ones).
    branding, active_profile = _resolve_branding(
        tenant, body.branding, entitlements.whitelabel_enabled, db
    )

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

    # Add findings from DB (include bbox + object data for annotated reports)
    findings = db.query(JobFinding).filter(JobFinding.job_id == uid).all()
    result_json["findings"] = [
        {
            "inspection_id": f.inspection_id,
            "severity": f.severity,
            "message": f.message,
            "page_num": f.page_num,
            "object_id": f.object_id,
            "object_type": f.object_type,
            "source": f.source or "engine",
            "category": f.category,
            "details": f.details,
            "bbox": [f.bbox_x0, f.bbox_y0, f.bbox_x1, f.bbox_y1] if f.bbox_x0 is not None else None,
        }
        for f in findings
    ]

    # Ensure file_key is available for page screenshot rendering
    if "metadata" not in result_json:
        result_json["metadata"] = {}
    if "file_key" not in result_json["metadata"]:
        result_json["metadata"]["file_key"] = job.file_key

    # Validate detail level
    from lintpdf.reports.service import ReportDetailLevel

    detail_level = body.detail_level
    if detail_level not in ReportDetailLevel.__members__.values():
        detail_level = ReportDetailLevel.STANDARD

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
            report_base_url=resolve_report_base_url(tenant, active_profile, entitlements, settings),
            detail_level=detail_level,
            summary_page=body.summary_page
            or getattr(tenant, "report_summary_page", None)
            or "prepend",
            allow_annotations=body.allow_annotations,
        ),
    )

    return GenerateReportsResponse(
        reports=[ReportInfo(**r) for r in result.reports],
    )


@router.get("/api/v1/jobs/{job_id}/reports", response_model=ReportListResponse)
async def list_reports(
    job_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ReportListResponse:
    """List existing report tokens for a job."""
    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job id: '{job_id}' is not a valid UUID.",
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
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
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
        from lintpdf.api.storage import get_storage

        storage = get_storage()
        file_key = f"reports/{record.tenant_id}/{record.job_id}/report.{record.format}"
        storage.delete_file(file_key)
    except Exception:
        pass  # Best-effort cleanup

    db.delete(record)
    db.commit()


# --- Public endpoints (token-based, no auth) ---
#
# IMPORTANT: the PDF route must be registered BEFORE the HTML route.
# Starlette matches routes in declaration order, and the ``{token}`` path
# converter is greedy (matches any non-slash characters, including dots).
# If ``/r/{token}`` comes first, a request for ``/r/abc.pdf`` captures
# ``token='abc.pdf'`` and 404s because the DB stores ``abc``. Declaring the
# ``.pdf``-suffixed route first lets Starlette try the specific pattern
# before falling back to the catch-all.


async def _serve_report_by_extension(
    token: str,
    expected_format: str,
    media_type: str,
    download: bool,
    db: Session,
) -> Response:
    """Shared lookup + storage fetch for the public ``/r/{token}.{ext}`` routes.

    Centralises the token expiry check, the format-mismatch 404, and the
    storage 404 so JSON, XML, PDF, and (future) annotated PDF token routes
    behave identically.
    """
    from datetime import datetime, timezone

    record: ReportToken | None = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if record.expires_at is not None and datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Report has expired.")

    if record.format != expected_format:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{expected_format.upper()} report not found for this token.",
        )

    from lintpdf.api.storage import get_storage

    storage = get_storage()
    loop = asyncio.get_running_loop()
    try:
        content = await loop.run_in_executor(
            None,
            storage.download_report,
            str(record.tenant_id),
            str(record.job_id),
            expected_format,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{expected_format.upper()} report not found for this token.",
        ) from exc

    record.accessed_count += 1
    record.last_accessed_at = datetime.now(timezone.utc)
    db.commit()

    headers: dict[str, str] = {}
    if download:
        ext = "pdf" if expected_format == "pdf" else expected_format
        if record.brand_mode == "anonymous":
            from lintpdf.reports.service import build_anonymous_filename

            filename = build_anonymous_filename(str(record.job_id), extension=ext)
        else:
            filename = f"report.{ext}"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return Response(content=content, media_type=media_type, headers=headers)


@router.get("/r/{token}.json")
async def serve_json_report(
    token: str,
    download: int = 0,
    db: Session = Depends(get_db),
) -> Response:
    """Serve a JSON report by token (public, no auth).

    Same shape as the LintPDF v1 import schema — re-importable via
    ``preflight_source=external``, ``external_format=lintpdf_json``.
    """
    return await _serve_report_by_extension(
        token=token,
        expected_format="json",
        media_type="application/json",
        download=bool(download),
        db=db,
    )


@router.get("/r/{token}.xml")
async def serve_xml_report(
    token: str,
    download: int = 0,
    db: Session = Depends(get_db),
) -> Response:
    """Serve an XML report by token (public, no auth).

    Same field taxonomy as the JSON report — for Switch / MIS / other
    XML-only consumers.
    """
    return await _serve_report_by_extension(
        token=token,
        expected_format="xml",
        media_type="application/xml",
        download=bool(download),
        db=db,
    )


@router.get("/r/{token}.pdf")
async def serve_pdf_report(
    token: str,
    download: int = 0,
    db: Session = Depends(get_db),
) -> Response:
    """Serve a PDF-flavoured report by token (public, no auth).

    Handles all three PDF-bearing token formats — plain ``pdf``, the
    findings-overlay ``annotated_pdf``, and the reviewer-markup
    ``annotated_pdf_markup`` — since every one of them lives behind a
    ``{report_base}/r/{token}.pdf`` URL. The storage key encodes the
    specific format (see ``InMemoryStorage.upload_report`` /
    ``S3Storage.upload_report`` — ``reports/{tenant}/{job}/report.{fmt}``),
    so we must pass ``record.format`` through rather than hard-coding
    ``"pdf"``.
    """
    from datetime import datetime, timezone

    record: ReportToken | None = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if record.expires_at is not None and datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Report has expired.")

    _PDF_FORMATS = {"pdf", "annotated_pdf", "annotated_pdf_markup"}
    if record.format not in _PDF_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report not found for this token.",
        )

    # Fetch from storage (run in thread to avoid blocking event loop).
    # Missing file means the token points at a report that was never stored
    # (or was evicted) — treat as 404 rather than leaking a 500.
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    loop = asyncio.get_running_loop()
    try:
        content = await loop.run_in_executor(
            None,
            storage.download_report,
            str(record.tenant_id),
            str(record.job_id),
            record.format,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF report not found for this token.",
        ) from exc

    # Increment access count only after we've successfully fetched the payload.
    record.accessed_count += 1
    record.last_accessed_at = datetime.now(timezone.utc)
    db.commit()

    disposition = "attachment" if download else "inline"
    if record.brand_mode == "anonymous":
        from lintpdf.reports.service import build_anonymous_filename

        filename = build_anonymous_filename(str(record.job_id), extension="pdf")
    else:
        filename = "report.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@router.get("/r/{token}")
async def serve_html_report(
    token: str,
    db: Session = Depends(get_db),
) -> Response:
    """Serve an interactive HTML report by token (public, no auth)."""
    from datetime import datetime, timezone

    record: ReportToken | None = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

    if record.expires_at is not None and datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Report has expired.")

    if record.format != "html":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTML report not found for this token.",
        )

    # Fetch from storage (run in thread to avoid blocking event loop).
    # Missing file means the token points at a report that was never stored
    # (or was evicted) — treat as 404 rather than leaking a 500.
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    loop = asyncio.get_running_loop()
    try:
        content = await loop.run_in_executor(
            None, storage.download_report, str(record.tenant_id), str(record.job_id), "html"
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HTML report not found for this token.",
        ) from exc

    # Increment access count only after we've successfully fetched the payload.
    record.accessed_count += 1
    record.last_accessed_at = datetime.now(timezone.utc)
    db.commit()

    return HTMLResponse(content=content)


# --- Token validation endpoint (used by plugin proxy for public viewer) ---


@router.get("/api/v1/reports/tokens/{token}")
async def validate_report_token(
    token: str,
    db: Session = Depends(get_db),
) -> dict:
    """Validate a report token and return job metadata.

    Used by the Fairy Ring plugin to verify public viewer access tokens
    before proxying viewer API requests to the engine.
    """
    from datetime import datetime, timezone

    record: ReportToken | None = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")

    if record.expires_at is not None and datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token has expired.")

    job: Job | None = db.query(Job).filter(Job.id == record.job_id).first()
    file_name = job.file_name if job else "Untitled"

    # Respect the tenant's ``share_email_required`` setting instead of
    # the old hard-coded ``True``. Gating every public share-link behind
    # an email prompt is correct for brokers who need lead-gen, but
    # wrong for tenants sharing internally — the gate looked like a
    # "link invalid" error to anyone who hit it without context.
    # ``getattr`` with a ``True`` fallback keeps the old behaviour if a
    # row predates the column being added (stale schema, startup.sh
    # hasn't run yet, etc.).
    tenant = db.query(Tenant).filter(Tenant.id == record.tenant_id).first()
    email_required = bool(getattr(tenant, "share_email_required", True)) if tenant else True

    return {
        "job_id": str(record.job_id),
        "tenant_id": str(record.tenant_id),
        "file_name": file_name,
        "email_required": email_required,
    }


@router.get("/api/v1/reports/tokens/{token}/findings")
async def get_token_findings(
    token: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get findings for a job via report token (public, no auth).

    Returns the same finding data as GET /api/v1/jobs/{job_id} but
    authenticated by report token instead of tenant API key.
    """
    from datetime import datetime, timezone

    record: ReportToken | None = db.query(ReportToken).filter(ReportToken.token == token).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")

    if record.expires_at is not None and datetime.now(timezone.utc) > record.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token has expired.")

    findings = db.query(JobFinding).filter(JobFinding.job_id == record.job_id).all()

    return {
        "findings": [
            {
                "inspection_id": f.inspection_id,
                "severity": f.severity,
                "message": f.message,
                "page_num": f.page_num,
                "details": f.details,
                "source": f.source or "engine",
                "category": f.category,
                "bbox": [f.bbox_x0, f.bbox_y0, f.bbox_x1, f.bbox_y1]
                if f.bbox_x0 is not None
                else None,
                "object_id": f.object_id,
                "object_type": f.object_type,
            }
            for f in findings
        ]
    }


# --- Check name registry endpoint ---


@router.get("/api/v1/check-names")
async def get_check_names() -> dict:
    """Return the human-friendly check name registry.

    Static data — clients should cache aggressively.
    """
    try:
        from lintpdf.reports.check_names import CHECK_NAMES

        return {
            check_id: {"name": info.name, "description": info.description}
            for check_id, info in CHECK_NAMES.items()
        }
    except ImportError:
        return {}
