"""Report generation and serving endpoints."""

from __future__ import annotations

import asyncio
import uuid as uuid_mod
from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import BrandProfile, BrandProfileType, Job, JobFinding, ReportToken, Tenant
from lintpdf.overrides import (
    EntitlementDenied,
    OverridesEnvelope,
    enforce_report_entitlements,
)

if TYPE_CHECKING:
    from lintpdf.reports.service import BrandingContext

router = APIRouter(tags=["reports"])


# --- Format specs ---
#
# Inline return is supported only for text-oriented formats. Binary
# formats are always delivered via signed token URL; asking for them
# inline is a validation error so clients fail fast instead of getting
# a surprising base64 blob. Keep these sets in sync with the report
# generator dispatch in ``lintpdf.reports.service``.
TEXT_FORMATS: frozenset[str] = frozenset({"json", "xml"})
BINARY_FORMATS: frozenset[str] = frozenset({"html", "pdf", "annotated_pdf", "annotated_pdf_markup"})


class FormatSpec(BaseModel):
    """Per-format return-mode spec.

    Accepted in ``GenerateReportsRequest.formats`` alongside bare
    strings. A bare string (back-compat) normalizes to
    ``FormatSpec(format=s, return_="url")`` so existing callers are
    unaffected.

    ``return`` is the JSON key because ``return`` is a Python keyword; we
    expose it via an alias while keeping ``return_`` as the attribute.
    """

    format: str
    return_: Literal["url", "inline", "both"] = Field("url", alias="return")

    model_config = {"populate_by_name": True}


def _normalize_format_list(
    v: list[str | FormatSpec | dict],
) -> list[FormatSpec]:
    """Normalize heterogeneous format input to ``list[FormatSpec]``.

    Shared between the Pydantic ``@field_validator`` on
    ``GenerateReportsRequest.formats`` and the overrides-fold path in
    the handler, which may receive a fresh list of strings from the
    nested envelope and needs the same back-compat + binary-format
    validation behavior.
    """
    out: list[FormatSpec] = []
    for item in v:
        if isinstance(item, FormatSpec):
            spec = item
        elif isinstance(item, str):
            spec = FormatSpec(format=item)
        elif isinstance(item, dict):
            spec = FormatSpec.model_validate(item)
        else:  # pragma: no cover — defensive, validator should reject
            raise ValueError(f"Unexpected format entry type: {type(item).__name__}")
        if spec.return_ in ("inline", "both") and spec.format in BINARY_FORMATS:
            raise ValueError(
                f"Inline return is not supported for binary format "
                f"'{spec.format}'. Use 'url' (default) for binary formats."
            )
        out.append(spec)
    return out


# --- Request/Response schemas ---


class BrandingOverride(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    hide_footer: bool | None = None


class GenerateReportsRequest(BaseModel):
    # ``validate_default=True`` so the default list is routed through
    # ``_normalize_formats`` — otherwise a caller sending an empty body
    # would reach the handler with ``body.formats`` still as bare
    # strings and every downstream ``spec.format`` access would blow up.
    formats: list[str | FormatSpec] = Field(default=["html", "pdf"], validate_default=True)
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
    # Per-mint override for the email-capture gate on ``/view/{token}``.
    #   - ``None`` (default) → inherit the tenant's ``share_email_required``
    #     setting; brokers who need lead-gen keep the gate on, internal
    #     shares from tenants that flipped the tenant flag off don't.
    #   - ``True``  → gate on regardless of tenant setting.
    #   - ``False`` → gate off regardless of tenant setting — use when
    #     sharing with a trusted party who shouldn't be prompted.
    # Persisted on the minted ReportToken row so the validator endpoint
    # can resolve it without re-reading the tenant later.
    require_visitor_email: bool | None = None
    # Universal per-call override envelope. Everything the tenant has
    # access to is toggleable through this single field — viewer UI
    # defaults, report knobs, branding, share-link gating. Flat fields
    # above are still honoured for back-compat; when both are provided,
    # the nested envelope wins because it's more explicit.
    # See ``lintpdf.overrides.OverridesEnvelope``.
    overrides: OverridesEnvelope | None = None

    @field_validator("formats", mode="after")
    @classmethod
    def _normalize_formats(cls, v: list[str | FormatSpec]) -> list[FormatSpec]:
        """Normalize bare strings → FormatSpec and reject inline for binary.

        Back-compat: ``"json"`` becomes ``FormatSpec(format="json")`` with
        the default ``return="url"``. Requesting
        ``{"format": "pdf", "return": "inline"}`` raises a validation
        error because PDFs would otherwise inflate the response ~33% as
        base64; use the default URL flow for binary formats.
        """
        return _normalize_format_list(v)


class ReportInfo(BaseModel):
    """One generated report entry in the POST /reports response.

    Fields are nullable because callers can now opt into inline-only
    delivery (no token minted, no URL generated) per format. Old
    callers receive ``url``/``token``/``expires_at`` as before and
    simply ignore the additive ``data``/``content_type`` fields.
    """

    format: str
    url: str | None = None
    viewer_url: str | None = Field(
        default=None,
        description=(
            "Public interactive viewer URL (Next.js app at "
            "``{viewer_base}/view/{token}``). Populated for the ``html`` "
            "format when a token is minted; null for non-HTML formats and "
            "for inline-only HTML deliveries. ``viewer_base`` honors the "
            "tenant's verified ``app_custom_domain`` for white-labeled "
            "share links, falls back to the global default otherwise."
        ),
    )
    token: str | None = None
    expires_at: str | None = None
    data: Any | None = None  # dict for JSON, str for XML; None for url-only
    content_type: str | None = None
    skipped_reason: str | None = Field(
        default=None,
        description=(
            "When the caller requested a format the engine could not produce a URL for, "
            "this carries the machine-readable reason instead of dropping the format "
            "from the response. Values: `no_content` (generator returned None by design "
            "-- e.g. `annotated_pdf_markup` requested but no viewer annotations exist), "
            "`generation_failed` (unexpected exception, details in engine logs)."
        ),
    )


class GenerateReportsResponse(BaseModel):
    reports: list[ReportInfo]


# ---------------------------------------------------------------------------
# Bulk report-mint (bulk-files step 5)
#
# For N-independent-submissions workloads (100 separate POST /api/v1/jobs,
# each producing a completed Job that the client then wants reports for),
# clients previously had to call POST /api/v1/jobs/{id}/reports N times.
# Today's tier-1 smoke dropped 6 / 13 links because 13 simultaneous mint
# POSTs from the harness overran default timeouts. A single POST
# /api/v1/reports:batchMint collapses that into one round trip; the
# engine dispatches each job through the same per-job pipeline so the
# minted tokens are indistinguishable from the single-endpoint result.
# ---------------------------------------------------------------------------


class BatchMintRequest(BaseModel):
    """Request body for POST /api/v1/reports:batchMint.

    Subset of ``GenerateReportsRequest`` — the common bulk-mint knobs.
    Advanced per-job overrides (idempotency, inline returns, universal
    overrides envelope, per-call branding) are still only available on
    the single-job endpoint; callers who need them should stick with
    POST /api/v1/jobs/{id}/reports.
    """

    job_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "List of job IDs (UUID strings) owned by the authenticated "
            "tenant. Each job must be in ``complete`` status; jobs in "
            "other states return per-item errors rather than failing "
            "the whole request. Hard-capped at 500 to avoid pathological "
            "requests; split larger batches client-side."
        ),
    )
    formats: list[str | FormatSpec] = Field(
        default=["html", "pdf"],
        validate_default=True,
        description=(
            "Formats to mint per job. Identical shape to the single-job "
            "endpoint — bare strings or FormatSpec objects."
        ),
    )
    expiry_days: int | None = None
    allow_annotations: bool = False
    require_visitor_email: bool | None = None

    @field_validator("formats", mode="after")
    @classmethod
    def _normalize_formats(cls, v: list[str | FormatSpec]) -> list[FormatSpec]:
        return _normalize_format_list(v)


class BatchMintResult(BaseModel):
    """Per-job outcome within a batch-mint response."""

    job_id: str
    status: Literal["ok", "failed"]
    reports: list[ReportInfo] | None = None
    error: str | None = None


class BatchMintResponse(BaseModel):
    """Envelope for POST /api/v1/reports:batchMint results."""

    results: list[BatchMintResult]
    summary: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of {'ok': int, 'failed': int} for quick client-side filtering.",
    )


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
    request: Request,
    body: GenerateReportsRequest | None = None,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> GenerateReportsResponse:
    """Generate hosted reports for a completed job."""
    from lintpdf.api.config import get_settings

    settings = get_settings()

    if body is None:
        body = GenerateReportsRequest()

    # Read optional Idempotency-Key header. When present, tokens become
    # deterministic (hash of tenant + key + format) so retries converge
    # on the same artifact and the stored bytes are reused instead of
    # regenerated. A header-sized DoS guard mirrors Stripe's 255-char
    # limit.
    idempotency_key: str | None = None
    if getattr(settings, "reports_idempotency_enabled", True):
        raw_idem = request.headers.get("Idempotency-Key")
        if raw_idem is not None:
            raw_idem = raw_idem.strip()
            if len(raw_idem) > 255:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Idempotency-Key must be 255 characters or fewer.",
                )
            if raw_idem:
                idempotency_key = raw_idem

    # Inline kill-switch: reject any inline/both spec when disabled.
    if not getattr(settings, "reports_inline_enabled", True):
        for spec in body.formats:
            if spec.return_ in ("inline", "both"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Inline returns are disabled on this instance.",
                )

    # Fold nested ``body.overrides`` onto the flat fields. The flat API
    # was here first and legacy clients still use it; the nested
    # envelope is the forward-looking shape. When both are set, the
    # nested (more explicit) values win for each field — caller opts in
    # by including the field in ``overrides``.
    if body.overrides is not None:
        if body.overrides.report is not None:
            r = body.overrides.report
            if r.formats is not None:
                # ``r.formats`` is a list of strings from the envelope
                # schema; re-run through the shared normalizer so bare
                # strings normalize to ``FormatSpec`` and inline-for-
                # binary is still rejected via the envelope surface.
                try:
                    body.formats = _normalize_format_list(list(r.formats))
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=str(exc),
                    ) from exc
            if r.detail_level is not None:
                body.detail_level = r.detail_level
            if r.summary_page is not None:
                body.summary_page = r.summary_page
            if r.expiry_days is not None:
                body.expiry_days = r.expiry_days
            if r.email_to is not None:
                body.email_to = r.email_to
        if body.overrides.share is not None:
            s = body.overrides.share
            if s.require_visitor_email is not None:
                body.require_visitor_email = s.require_visitor_email
            if s.allow_annotations is not None:
                body.allow_annotations = s.allow_annotations
        if body.overrides.branding is not None and body.branding is None:
            # Map the envelope's branding fields onto the flat
            # BrandingOverride only when the caller didn't already
            # supply one — the flat surface remains authoritative if it
            # was explicitly set.
            b = body.overrides.branding
            if any(
                v is not None
                for v in (
                    b.name,
                    b.logo_url,
                    b.primary_color,
                    b.accent_color,
                    b.hide_footer,
                )
            ):
                body.branding = BrandingOverride(
                    name=b.name,
                    logo_url=b.logo_url,
                    primary_color=b.primary_color,
                    accent_color=b.accent_color,
                    hide_footer=b.hide_footer,
                )

    # Enforce tier-based restrictions
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    # Report format entitlements — resolver owns the message formatting so
    # there's only one place to update when plan gates change. The
    # entitlements resolver works with bare format strings, so project
    # the FormatSpec list down before checking.
    from lintpdf.overrides.envelope import ReportOverrides

    try:
        enforce_report_entitlements(
            ReportOverrides(formats=[spec.format for spec in body.formats]),
            entitlements,
        )
    except EntitlementDenied as exc:
        from lintpdf.api.gates import plan_upgrade_required
        from lintpdf.tenants.models import PLAN_LIMITS, TenantPlan

        requested = [spec.format for spec in body.formats]
        # Find the cheapest plan whose allowed_report_formats covers every
        # requested format. Iterate in ascending tier order so we return
        # the real minimum upgrade target — the previous hard-coded
        # "starter" was wrong for annotated_pdf / annotated_pdf_markup
        # (which require scale+), misleading customers into a cheaper
        # plan that still doesn't include the format.
        plan_order = [
            TenantPlan.FREE,
            TenantPlan.VIEWER,
            TenantPlan.STARTER,
            TenantPlan.GROWTH,
            TenantPlan.SCALE,
            TenantPlan.ENTERPRISE,
        ]
        required = "enterprise"
        for plan in plan_order:
            allowed = set(PLAN_LIMITS[plan].get("allowed_report_formats") or [])
            if all(fmt in allowed for fmt in requested):
                required = str(plan)
                break

        raise plan_upgrade_required(
            gate="report_format",
            current_plan=str(tenant.plan),
            required_plan=required,
            message=str(exc),
        ) from exc

    # Check white-label branding restriction
    if body.branding and not entitlements.whitelabel_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="White-label branding (Livery) requires Scale or Enterprise plan.",
        )

    # Viewer tier: force allow_annotations=False on every minted share
    # link, regardless of what the caller requested. The token carries the
    # constraint immutably so the public viewer never sees an annotate
    # affordance.
    if not entitlements.annotations_enabled:
        body.allow_annotations = False

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

    from lintpdf.api.storage import get_storage
    from lintpdf.reports.service import (
        ReportService,
        resolve_report_base_url,
        resolve_viewer_base_url,
    )
    from lintpdf.tenants.models import PLAN_LIMITS, TenantPlan

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
            # Pass the tenant-resolved viewer base so white-labeled tenants
            # see their custom app domain in the share/viewer URLs that the
            # mint response + desktop app + dashboard surface.
            viewer_base_url=resolve_viewer_base_url(tenant, active_profile, entitlements, settings),
            detail_level=detail_level,
            summary_page=body.summary_page
            or getattr(tenant, "report_summary_page", None)
            or "prepend",
            allow_annotations=body.allow_annotations,
            require_visitor_email=body.require_visitor_email,
            overrides_dict=(
                body.overrides.model_dump(exclude_unset=True, exclude_none=True)
                if body.overrides is not None
                else None
            ),
            idempotency_key=idempotency_key,
        ),
    )

    # Notify subscribers. Only the formats that actually produced a URL
    # are interesting for a "report.minted" event -- a skipped format
    # (e.g. annotated_pdf_markup with no viewer annotations) returns
    # url=None and skipped_reason set; those don't constitute a mint.
    minted = [r for r in result.reports if r.get("url")]
    if minted:
        from lintpdf.webhooks.events import fire_job_state_changed, fire_report_minted

        fire_report_minted(
            db,
            tenant.id,
            job_id=uid,
            reports=[
                {
                    "format": r["format"],
                    "url": r["url"],
                    "token": r.get("token"),
                    "expires_at": r.get("expires_at"),
                }
                for r in minted
            ],
        )
        job_row = db.query(Job).filter(Job.id == uid, Job.tenant_id == tenant.id).first()
        if job_row is not None:
            fire_job_state_changed(db, job_row, tenant.id, reason="report.minted")
        db.commit()

    return GenerateReportsResponse(
        reports=[ReportInfo(**r) for r in result.reports],
    )


@router.post(
    "/api/v1/reports:batchMint",
    response_model=BatchMintResponse,
    status_code=status.HTTP_200_OK,
)
async def batch_mint_reports(
    body: BatchMintRequest,
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BatchMintResponse:
    """Mint report tokens for N completed jobs in a single round trip.

    See ``BatchMintRequest`` for the supported knobs. Each job is
    dispatched through the same per-job handler the single-endpoint
    uses, so minted tokens are byte-identical to
    ``POST /api/v1/jobs/{id}/reports``. Per-job failures (job not
    found, wrong tenant, job not complete, entitlement denial, etc.)
    are captured as ``{"status":"failed","error":"..."}`` on the
    matching result entry — a single bad id in the batch does not
    drop the rest.

    Serial inside the handler: client saves N HTTP round trips, engine
    reuses one DB session. Per-job wall clock is unchanged; the
    throughput gain is the eliminated round-trip overhead and the
    shared auth/parse cost. True per-job concurrency is a follow-up
    — SQLAlchemy sessions aren't thread-safe so it requires a session
    per concurrent task.
    """
    # Build a minimal per-job request body from the batch knobs.
    per_job_body = GenerateReportsRequest(
        formats=list(body.formats),
        expiry_days=body.expiry_days,
        allow_annotations=body.allow_annotations,
        require_visitor_email=body.require_visitor_email,
    )

    results: list[BatchMintResult] = []
    ok_count = 0
    failed_count = 0
    for job_id in body.job_ids:
        try:
            resp = await generate_reports(
                job_id=job_id,
                request=request,
                body=per_job_body,
                db=db,
                tenant=tenant,
            )
            results.append(
                BatchMintResult(
                    job_id=job_id,
                    status="ok",
                    reports=list(resp.reports),
                )
            )
            ok_count += 1
        except HTTPException as exc:
            results.append(
                BatchMintResult(
                    job_id=job_id,
                    status="failed",
                    error=f"{exc.status_code}: {exc.detail}"[:400],
                )
            )
            failed_count += 1
        except Exception as exc:  # noqa: BLE001 — we *want* to report any downstream blow-up per-job
            results.append(
                BatchMintResult(
                    job_id=job_id,
                    status="failed",
                    error=f"unexpected error: {type(exc).__name__}: {exc}"[:400],
                )
            )
            failed_count += 1

    return BatchMintResponse(
        results=results,
        summary={"ok": ok_count, "failed": failed_count},
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

    pdf_formats = {"pdf", "annotated_pdf", "annotated_pdf_markup"}
    if record.format not in pdf_formats:
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

    # Resolve the email gate in three layers, most specific first:
    #   1. Per-token override (``ReportToken.require_visitor_email``):
    #      the mint call asked for gate on / off for *this* link.
    #   2. Tenant-wide default (``Tenant.share_email_required``):
    #      what the tenant usually wants.
    #   3. ``True`` fallback:
    #      rows predating either column keep the pre-existing
    #      behaviour — never accidentally de-gate an old share link.
    per_token = getattr(record, "require_visitor_email", None)
    if per_token is not None:
        email_required = bool(per_token)
    else:
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
