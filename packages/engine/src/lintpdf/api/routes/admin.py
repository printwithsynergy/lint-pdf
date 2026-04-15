"""Admin API endpoints for internal services (Stripe plugin, Pixie Dust)."""

from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import generate_api_key, hash_api_key, verify_admin_key
from lintpdf.api.database import get_db
from lintpdf.api.models import ApiKey, Job, Tenant
from lintpdf.api.schemas import (
    AdminCustomDomainListResponse,
    AdminUpdateCustomDomainRequest,
)
from lintpdf.api.storage import get_storage

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# Backward-compatible alias — existing Depends(_verify_admin_key) calls still work
_verify_admin_key = verify_admin_key


# ── Request/Response models ──────────────────────────────────


class CreateTenantRequest(BaseModel):
    name: str
    contact_email: str | None = None
    plan: str = "free"


class UpdatePlanRequest(BaseModel):
    plan: str
    overage_enabled: bool | None = None
    overage_cap_cents: int | None = None


class UpdateStripeRequest(BaseModel):
    stripe_customer_id: str | None = None
    stripe_subscription_item_id: str | None = None


class UpdateStatusRequest(BaseModel):
    is_active: bool


class AdminTenantResponse(BaseModel):
    id: str
    name: str
    plan: str
    updated: bool


class AdminTenantDetail(BaseModel):
    id: str
    name: str
    plan: str
    rate_limit_daily: int
    max_file_size_mb: int
    contact_email: str | None
    overage_enabled: bool
    overage_cap_cents: int | None
    stripe_customer_id: str | None
    entitlement_overrides: dict[str, Any] | None
    is_active: bool
    created_at: str


class AdminTenantListResponse(BaseModel):
    tenants: list[AdminTenantDetail]
    total: int
    page: int
    page_size: int


class ApiKeyResponse(BaseModel):
    id: str
    label: str
    key_prefix: str
    is_active: bool
    last_used_at: str | None
    created_at: str


class ApiKeyCreatedResponse(BaseModel):
    id: str
    label: str
    key_prefix: str
    raw_key: str


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyResponse]


class UpdateEntitlementsRequest(BaseModel):
    """Per-tenant entitlement overrides. Only include keys to override."""

    allowed_report_formats: list[str] | None = None
    webhooks_enabled: bool | None = None
    whitelabel_enabled: bool | None = None
    priority_processing: bool | None = None
    custom_integrations: bool | None = None
    custom_profiles: bool | None = None
    max_custom_profiles: int | None = None
    max_webhooks: int | None = None
    rate_limit_daily: int | None = None
    max_file_size_mb: int | None = None
    report_storage_mb: int | None = None
    report_default_expiry_days: int | None = None
    overage_rate_cents: int | None = None


class EntitlementOverridesResponse(BaseModel):
    id: str
    entitlement_overrides: dict[str, Any] | None
    updated: bool


class EffectiveEntitlementsResponse(BaseModel):
    plan: str
    plan_defaults: dict[str, Any]
    overrides: dict[str, Any]
    effective: dict[str, Any]


class AdminJobSummary(BaseModel):
    id: str
    tenant_id: str
    tenant_name: str | None
    status: str
    profile_id: str
    file_name: str
    created_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    page_count: int | None = None
    error_message: str | None = None


class AdminJobListResponse(BaseModel):
    jobs: list[AdminJobSummary]
    total: int
    page: int
    page_size: int


class AdminJobDetail(AdminJobSummary):
    file_size: int
    result_summary: dict[str, Any] | None = None
    report_token: str | None = None
    report_format: str | None = None
    verdict: str | None = None
    verdict_by: str | None = None
    verdict_at: str | None = None
    verdict_notes: str | None = None
    preflight_source: str | None = None
    external_format: str | None = None


class AdminProfileSummary(BaseModel):
    profile_id: str
    name: str
    description: str = ""
    conformance: str | None = None
    workflow: str = "CMYK"
    is_builtin: bool = True


class AdminTenantProfiles(BaseModel):
    tenant_id: str
    tenant_name: str | None
    profiles: list[AdminProfileSummary]


class AdminProfileListResponse(BaseModel):
    system: list[AdminProfileSummary]
    tenants: list[AdminTenantProfiles]


class AdminProfileDetailResponse(BaseModel):
    profile_id: str
    tenant_id: str | None
    tenant_name: str | None
    name: str
    description: str = ""
    version: str = "1.0"
    conformance: str | None = None
    workflow: str = "CMYK"
    checks: dict[str, Any]
    thresholds: dict[str, Any]
    is_builtin: bool = True


class AdminProfileUpsertRequest(BaseModel):
    tenant_id: str
    profile_id: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
    )
    preflight_profile: dict[str, Any]


# ── Preflight Audit (cross-tenant end-to-end visibility) ─────


class AdminAuditJobRow(BaseModel):
    """Row in the audit list — header-only fields for accordion display."""

    id: str
    tenant_id: str
    tenant_name: str | None = None
    file_name: str
    status: str
    profile_id: str
    preflight_source: str | None = None
    external_format: str | None = None
    created_at: str
    completed_at: str | None = None
    page_count: int | None = None
    duration_ms: int | None = None
    verdict: str | None = None
    has_imported_report: bool = False
    report_token_count: int = 0
    findings_count: int = 0


class AdminAuditGroup(BaseModel):
    """A single group bucket (e.g. one tenant, one source, one date)."""

    key: str = Field(description="Machine key, e.g. tenant UUID or 'engine'.")
    label: str = Field(description="Human-readable label for the group header.")
    count: int
    jobs: list[AdminAuditJobRow]


class AdminAuditListResponse(BaseModel):
    groups: list[AdminAuditGroup]
    total: int
    page: int
    page_size: int
    group_by: str
    filters_applied: dict[str, Any]


class AdminPresignedBlob(BaseModel):
    """Presigned GET URL plus metadata for a single S3 object."""

    presigned_url: str
    expires_at: str
    size_bytes: int | None = None


class AdminImportedReportDetail(BaseModel):
    id: str
    format: str
    parser_version: str
    raw_size_bytes: int
    source_metadata: dict[str, Any] | None = None
    parsed_at: str
    raw_blob_presigned_url: str
    expires_at: str
    inline_text: str | None = Field(
        default=None,
        description=(
            "Raw blob text for quick copy-paste. Populated only when the blob is "
            "under 2 MB and the format is a text type (XML/JSON)."
        ),
    )


class AdminReportTokenDetail(BaseModel):
    id: str
    token: str
    format: str
    public_url: str
    expires_at: str | None = None
    created_at: str
    accessed_count: int
    last_accessed_at: str | None = None
    brand_mode: str | None = None
    brand_profile_id: str | None = None
    allow_annotations: bool = False


class AdminApprovalStepSummary(BaseModel):
    index: int
    status: str
    approver_email: str | None = None
    decided_at: str | None = None
    notes: str | None = None


class AdminApprovalSummary(BaseModel):
    chain_id: str
    template_id: str | None = None
    status: str
    current_step: int
    steps: list[AdminApprovalStepSummary]
    created_at: str
    completed_at: str | None = None


class AdminSubmissionContext(BaseModel):
    source: str = Field(
        description=(
            "Origin of the submission: 'trial', 'endpoint', 'batch', 'api', or 'unknown'."
        ),
    )
    trial_submission_id: str | None = None
    trial_submitter_email: str | None = None
    endpoint_slug: str | None = None
    request_metadata: dict[str, Any] | None = None


class AdminJobAuditDetail(BaseModel):
    # Core identity
    id: str
    tenant_id: str
    tenant_name: str | None = None
    status: str
    profile_id: str
    file_name: str
    file_key: str
    file_size: int
    page_count: int | None = None
    duration_ms: int | None = None
    created_at: str
    completed_at: str | None = None
    error_message: str | None = None

    # Preflight mode / overrides
    preflight_source: str | None = None
    external_format: str | None = None
    data_capabilities: dict[str, Any] | None = None
    brand_profile_id_override: str | None = None
    unbranded_override: bool = False
    jdf_overrides: dict[str, Any] | None = None
    color_quality_score: float | None = None

    # Verdict
    verdict: str | None = None
    verdict_by: str | None = None
    verdict_at: str | None = None
    verdict_notes: str | None = None

    # Full result payload (not the trimmed summary returned by AdminJobDetail)
    result_json: dict[str, Any] | None = None

    # Artifacts
    input_pdf: AdminPresignedBlob | None = None
    imported_reports: list[AdminImportedReportDetail] = Field(default_factory=list)
    report_tokens: list[AdminReportTokenDetail] = Field(default_factory=list)

    # Counts / joins
    findings_count: int = 0
    annotations_count: int = 0

    # Context
    submission_context: AdminSubmissionContext
    approvals: AdminApprovalSummary | None = None


class AdminAuditFindingRow(BaseModel):
    id: str
    inspection_id: str
    severity: str
    message: str
    page_num: int | None = None
    category: str | None = None
    source: str
    object_id: str | None = None
    object_type: str | None = None
    bbox_x0: float | None = None
    bbox_y0: float | None = None
    bbox_x1: float | None = None
    bbox_y1: float | None = None
    details: dict[str, Any] | None = None


class AdminAuditFindingsResponse(BaseModel):
    findings: list[AdminAuditFindingRow]
    total: int
    page: int
    page_size: int


# ── Tenant plan management ───────────────────────────────────


@router.patch("/tenants/{tenant_id}/plan", response_model=AdminTenantResponse)
async def update_tenant_plan(
    tenant_id: str,
    body: UpdatePlanRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantResponse:
    """Update a tenant's plan (used by Stripe plugin on subscription changes)."""
    tenant = _get_tenant(db, tenant_id)

    from lintpdf.tenants.models import PLAN_LIMITS, TenantPlan

    try:
        new_plan = TenantPlan(body.plan)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan: {body.plan}",
        ) from exc

    limits = PLAN_LIMITS[new_plan]
    tenant.plan = new_plan
    tenant.rate_limit_daily = limits["rate_limit_daily"]
    tenant.max_file_size_mb = limits["max_file_size_mb"]

    if body.overage_enabled is not None:
        tenant.overage_enabled = body.overage_enabled
    if body.overage_cap_cents is not None:
        tenant.overage_cap_cents = body.overage_cap_cents

    db.commit()

    return AdminTenantResponse(id=str(tenant.id), name=tenant.name, plan=tenant.plan, updated=True)


@router.patch("/tenants/{tenant_id}/stripe", response_model=AdminTenantResponse)
async def update_tenant_stripe(
    tenant_id: str,
    body: UpdateStripeRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantResponse:
    """Set Stripe customer/subscription IDs for a tenant."""
    tenant = _get_tenant(db, tenant_id)

    if body.stripe_customer_id is not None:
        tenant.stripe_customer_id = body.stripe_customer_id
    if body.stripe_subscription_item_id is not None:
        tenant.stripe_subscription_item_id = body.stripe_subscription_item_id

    db.commit()

    return AdminTenantResponse(id=str(tenant.id), name=tenant.name, plan=tenant.plan, updated=True)


# ── Tenant creation ──────────────────────────────────────────


class CreateTenantResponse(BaseModel):
    id: str
    name: str
    plan: str
    api_key: str


@router.post("/tenants", response_model=CreateTenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: CreateTenantRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> CreateTenantResponse:
    """Create a new tenant with an API key.

    Used by super-admin provisioning and account onboarding flows.
    The raw API key is returned only in this response.
    """
    from lintpdf.tenants.models import PLAN_LIMITS, TenantPlan

    try:
        plan_enum = TenantPlan(body.plan.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan: {body.plan}",
        ) from exc

    limits = PLAN_LIMITS[plan_enum]
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    tenant_id = uuid_mod.uuid4()

    # Default to LintPDF branding for all new tenants
    from lintpdf.reports.service import _LINTPDF_DEFAULT_LOGO

    tenant = Tenant(
        id=tenant_id,
        name=body.name,
        api_key_hash=key_hash,
        plan=plan_enum,
        rate_limit_daily=limits["rate_limit_daily"],
        max_file_size_mb=limits["max_file_size_mb"],
        contact_email=body.contact_email,
        is_active=True,
        brand_name="LintPDF",
        brand_logo_url=_LINTPDF_DEFAULT_LOGO,
        brand_primary_color="#1e3a8a",
        brand_accent_color="#2563eb",
    )
    db.add(tenant)
    db.flush()

    api_key_record = ApiKey(
        tenant_id=tenant_id,
        key_hash=key_hash,
        label="Default",
        key_prefix=raw_key[:12],
    )
    db.add(api_key_record)
    db.commit()

    return CreateTenantResponse(
        id=str(tenant_id),
        name=body.name,
        plan=body.plan,
        api_key=raw_key,
    )


# ── Tenant list/detail/status (for site admin) ──────────────


@router.get("/tenants", response_model=AdminTenantListResponse)
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantListResponse:
    """List all tenants (paginated)."""
    total = db.query(Tenant).count()
    tenants = (
        db.query(Tenant)
        .order_by(desc(Tenant.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AdminTenantListResponse(
        tenants=[_tenant_to_detail(t) for t in tenants],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tenants/{tenant_id}", response_model=AdminTenantDetail)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantDetail:
    """Get tenant detail."""
    tenant = _get_tenant(db, tenant_id)
    return _tenant_to_detail(tenant)


@router.patch("/tenants/{tenant_id}/status", response_model=AdminTenantResponse)
async def update_tenant_status(
    tenant_id: str,
    body: UpdateStatusRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantResponse:
    """Activate or suspend a tenant."""
    tenant = _get_tenant(db, tenant_id)
    tenant.is_active = body.is_active
    db.commit()
    return AdminTenantResponse(id=str(tenant.id), name=tenant.name, plan=tenant.plan, updated=True)


# ── Tenant branding (admin) ────────────────────────────────


class UpdateBrandingRequest(BaseModel):
    brand_name: str | None = None
    brand_logo_url: str | None = None
    brand_primary_color: str | None = None
    brand_accent_color: str | None = None
    brand_hide_footer: bool | None = None


@router.patch("/tenants/{tenant_id}/branding", response_model=AdminTenantResponse)
async def update_tenant_branding(
    tenant_id: str,
    body: UpdateBrandingRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantResponse:
    """Set branding fields on a tenant (admin only)."""
    tenant = _get_tenant(db, tenant_id)
    if body.brand_name is not None:
        tenant.brand_name = body.brand_name
    if body.brand_logo_url is not None:
        tenant.brand_logo_url = body.brand_logo_url
    if body.brand_primary_color is not None:
        tenant.brand_primary_color = body.brand_primary_color
    if body.brand_accent_color is not None:
        tenant.brand_accent_color = body.brand_accent_color
    if body.brand_hide_footer is not None:
        tenant.brand_hide_footer = body.brand_hide_footer
    db.commit()
    return AdminTenantResponse(id=str(tenant.id), name=tenant.name, plan=tenant.plan, updated=True)


# ── White-label custom report domain (admin override) ───────


@router.get(
    "/custom-domains",
    response_model=AdminCustomDomainListResponse,
)
async def admin_list_custom_domains(
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminCustomDomainListResponse:
    """List all tenant + brand-profile custom domains, split by verified status."""
    from sqlalchemy import or_

    from lintpdf.api.models import BrandProfile
    from lintpdf.api.schemas import AdminCustomDomainRow

    tenant_rows = (
        db.query(Tenant)
        .filter(
            or_(
                Tenant.brand_custom_domain.isnot(None),
                Tenant.app_custom_domain.isnot(None),
            )
        )
        .all()
    )
    profile_rows = (
        db.query(BrandProfile, Tenant)
        .join(Tenant, BrandProfile.tenant_id == Tenant.id)
        .filter(
            or_(
                BrandProfile.custom_domain.isnot(None),
                BrandProfile.app_custom_domain.isnot(None),
            )
        )
        .all()
    )

    pending: list[AdminCustomDomainRow] = []
    active: list[AdminCustomDomainRow] = []

    for t in tenant_rows:
        if t.brand_custom_domain:
            row = AdminCustomDomainRow(
                scope="tenant",
                tenant_id=t.id,
                tenant_name=t.name,
                brand_profile_id=None,
                brand_profile_name=None,
                domain=t.brand_custom_domain,
                verified=t.brand_custom_domain_verified,
                requested_at=t.brand_custom_domain_requested_at,
            )
            (active if t.brand_custom_domain_verified else pending).append(row)
        # App/viewer domain
        if t.app_custom_domain:
            app_row = AdminCustomDomainRow(
                scope="tenant_app",
                tenant_id=t.id,
                tenant_name=t.name,
                brand_profile_id=None,
                brand_profile_name=None,
                domain=t.app_custom_domain,
                verified=t.app_custom_domain_verified,
                requested_at=t.app_custom_domain_requested_at,
            )
            (active if t.app_custom_domain_verified else pending).append(app_row)

    for profile, tenant in profile_rows:
        row = AdminCustomDomainRow(
            scope="brand_profile",
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            brand_profile_id=profile.id,
            brand_profile_name=profile.name,
            domain=profile.custom_domain or "",
            verified=profile.custom_domain_verified,
            requested_at=profile.custom_domain_requested_at,
        )
        (active if profile.custom_domain_verified else pending).append(row)
        if profile.app_custom_domain:
            app_row = AdminCustomDomainRow(
                scope="brand_profile_app",
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                brand_profile_id=profile.id,
                brand_profile_name=profile.name,
                domain=profile.app_custom_domain,
                verified=profile.app_custom_domain_verified,
                requested_at=profile.app_custom_domain_requested_at,
            )
            (active if profile.app_custom_domain_verified else pending).append(app_row)

    return AdminCustomDomainListResponse(pending=pending, active=active)


@router.patch(
    "/tenants/{tenant_id}/custom-domain",
    response_model=AdminTenantResponse,
)
async def admin_update_tenant_custom_domain(
    tenant_id: str,
    body: AdminUpdateCustomDomainRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantResponse:
    """Admin override: set/clear a tenant's custom domain and/or flip verified."""
    from sqlalchemy.exc import IntegrityError

    from lintpdf.api.routes.branding import validate_custom_domain

    tenant = _get_tenant(db, tenant_id)

    if body.domain is not None:
        if body.domain.strip() == "":
            tenant.brand_custom_domain = None
            tenant.brand_custom_domain_verified = False
            tenant.brand_custom_domain_requested_at = None
        else:
            tenant.brand_custom_domain = validate_custom_domain(body.domain)

    if body.verified is not None:
        tenant.brand_custom_domain_verified = body.verified

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That domain is already claimed by another tenant.",
        ) from exc

    return AdminTenantResponse(id=str(tenant.id), name=tenant.name, plan=tenant.plan, updated=True)


@router.patch(
    "/brand-profiles/{profile_id}/custom-domain",
    response_model=AdminTenantResponse,
)
async def admin_update_brand_profile_custom_domain(
    profile_id: str,
    body: AdminUpdateCustomDomainRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantResponse:
    """Admin override for a per-profile custom domain."""
    from sqlalchemy.exc import IntegrityError

    from lintpdf.api.models import BrandProfile
    from lintpdf.api.routes.branding import validate_custom_domain

    pid = _parse_uuid(profile_id)
    profile = db.query(BrandProfile).filter(BrandProfile.id == pid).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found."
        )

    if body.domain is not None:
        if body.domain.strip() == "":
            profile.custom_domain = None
            profile.custom_domain_verified = False
            profile.custom_domain_requested_at = None
        else:
            profile.custom_domain = validate_custom_domain(body.domain)

    if body.verified is not None:
        profile.custom_domain_verified = body.verified

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That domain is already claimed by another brand profile.",
        ) from exc

    tenant = db.query(Tenant).filter(Tenant.id == profile.tenant_id).first()
    return AdminTenantResponse(
        id=str(profile.tenant_id),
        name=tenant.name if tenant else "",
        plan=tenant.plan if tenant else None,
        updated=True,
    )


@router.patch(
    "/tenants/{tenant_id}/app-custom-domain",
    response_model=AdminTenantResponse,
)
async def admin_update_tenant_app_custom_domain(
    tenant_id: str,
    body: AdminUpdateCustomDomainRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminTenantResponse:
    """Admin override: set/clear a tenant's app/viewer custom domain."""
    from sqlalchemy.exc import IntegrityError

    from lintpdf.api.routes.branding import validate_custom_domain

    tid = _parse_uuid(tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    if body.domain is not None:
        if body.domain.strip() == "":
            tenant.app_custom_domain = None
            tenant.app_custom_domain_verified = False
            tenant.app_custom_domain_requested_at = None
        else:
            tenant.app_custom_domain = validate_custom_domain(body.domain)

    if body.verified is not None:
        tenant.app_custom_domain_verified = body.verified

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That domain is already claimed by another tenant.",
        ) from exc

    return AdminTenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        plan=tenant.plan,
        updated=True,
    )


# ── API key management ───────────────────────────────────────


@router.get("/tenants/{tenant_id}/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    tenant_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> ApiKeyListResponse:
    """List API keys for a tenant (masked)."""
    uid = _parse_uuid(tenant_id)
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.tenant_id == uid, ApiKey.is_active.is_(True))
        .order_by(desc(ApiKey.created_at))
        .all()
    )
    return ApiKeyListResponse(
        keys=[
            ApiKeyResponse(
                id=str(k.id),
                label=k.label,
                key_prefix=k.key_prefix,
                is_active=k.is_active,
                last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
                created_at=k.created_at.isoformat(),
            )
            for k in keys
        ]
    )


class CreateApiKeyRequest(BaseModel):
    label: str = "Default"


@router.post(
    "/tenants/{tenant_id}/keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    tenant_id: str,
    body: CreateApiKeyRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> ApiKeyCreatedResponse:
    """Generate a new API key for a tenant. The raw key is returned only once."""
    uid = _parse_uuid(tenant_id)

    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == uid).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    api_key = ApiKey(
        tenant_id=uid,
        key_hash=key_hash,
        label=body.label,
        key_prefix=raw_key[:12],
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreatedResponse(
        id=str(api_key.id),
        label=api_key.label,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
    )


@router.delete("/tenants/{tenant_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    tenant_id: str,
    key_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> None:
    """Revoke an API key (soft delete)."""
    t_uid = _parse_uuid(tenant_id)
    k_uid = _parse_uuid(key_id)

    api_key = db.query(ApiKey).filter(ApiKey.id == k_uid, ApiKey.tenant_id == t_uid).first()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")

    api_key.is_active = False
    db.commit()


# ── Cross-tenant job list (for site admin) ───────────────────


@router.get("/jobs", response_model=AdminJobListResponse)
async def list_all_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminJobListResponse:
    """List jobs across all tenants (paginated)."""
    total = db.query(Job).count()
    jobs = (
        db.query(Job)
        .order_by(desc(Job.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Batch-fetch tenant names
    tenant_ids = {j.tenant_id for j in jobs}
    tenants = db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()
    tenant_names = {t.id: t.name for t in tenants}

    return AdminJobListResponse(
        jobs=[
            AdminJobSummary(
                id=str(j.id),
                tenant_id=str(j.tenant_id),
                tenant_name=tenant_names.get(j.tenant_id),
                status=j.status.value if hasattr(j.status, "value") else str(j.status),
                profile_id=j.profile_id,
                file_name=j.file_name,
                created_at=j.created_at.isoformat(),
                completed_at=j.completed_at.isoformat() if j.completed_at else None,
                duration_ms=j.duration_ms,
                page_count=j.page_count,
                error_message=j.error_message,
            )
            for j in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=AdminJobDetail)
async def get_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminJobDetail:
    """Get full job detail (cross-tenant) for the site-admin Jobs drawer."""
    from lintpdf.api.models import ReportToken

    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job id: {job_id}",
        ) from exc

    job: Job | None = db.query(Job).filter(Job.id == uid).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    tenant = db.query(Tenant).filter(Tenant.id == job.tenant_id).first()

    # Pick the most recent report token (any format) for the Links tab.
    report: ReportToken | None = (
        db.query(ReportToken)
        .filter(ReportToken.job_id == uid)
        .order_by(desc(ReportToken.created_at))
        .first()
    )

    result_summary: dict[str, Any] | None = None
    if isinstance(job.result_json, dict):
        # Surface only the top-level summary block when present; otherwise
        # pass through a trimmed view to keep the response small.
        raw_summary = job.result_json.get("summary")
        if isinstance(raw_summary, dict):
            result_summary = raw_summary
        else:
            result_summary = {
                k: v
                for k, v in job.result_json.items()
                if k in ("total_checks", "passed", "failed", "warnings", "errors")
            } or None

    status_str = job.status.value if hasattr(job.status, "value") else str(job.status)
    source_str = (
        job.preflight_source.value
        if hasattr(job.preflight_source, "value")
        else str(job.preflight_source)
        if job.preflight_source
        else None
    )

    return AdminJobDetail(
        id=str(job.id),
        tenant_id=str(job.tenant_id),
        tenant_name=tenant.name if tenant else None,
        status=status_str,
        profile_id=job.profile_id,
        file_name=job.file_name,
        file_size=job.file_size,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        duration_ms=job.duration_ms,
        page_count=job.page_count,
        error_message=job.error_message,
        result_summary=result_summary,
        report_token=report.token if report else None,
        report_format=report.format if report else None,
        verdict=job.verdict,
        verdict_by=job.verdict_by,
        verdict_at=job.verdict_at.isoformat() if job.verdict_at else None,
        verdict_notes=job.verdict_notes,
        preflight_source=source_str,
        external_format=job.external_format,
    )


# ── Cross-tenant profile (ruleset) management ────────────────


def _profile_summary_from_builtin(profile_id: str, fp: Any) -> AdminProfileSummary:
    return AdminProfileSummary(
        profile_id=profile_id,
        name=fp.name,
        description=fp.description,
        conformance=fp.conformance,
        workflow=fp.workflow,
        is_builtin=True,
    )


def _profile_summary_from_custom(row: Any, fp: Any) -> AdminProfileSummary:
    return AdminProfileSummary(
        profile_id=row.profile_id,
        name=fp.name,
        description=fp.description,
        conformance=fp.conformance,
        workflow=fp.workflow,
        is_builtin=False,
    )


@router.get("/profiles", response_model=AdminProfileListResponse)
async def list_all_profiles(
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminProfileListResponse:
    """List all preflight profiles (system + per-tenant custom) for the
    site-admin Rulesets page."""
    from lintpdf.api.models import CustomProfile
    from lintpdf.profiles.registry import ProfileRegistry
    from lintpdf.profiles.schema import PreflightProfile

    registry = ProfileRegistry()
    system: list[AdminProfileSummary] = [
        _profile_summary_from_builtin(pid, registry.get(pid)) for pid in registry.list_profiles()
    ]

    custom_rows = db.query(CustomProfile).all()
    tenants = {
        t.id: t
        for t in db.query(Tenant).filter(Tenant.id.in_({r.tenant_id for r in custom_rows})).all()
    }

    by_tenant: dict[Any, list[AdminProfileSummary]] = {}
    for row in custom_rows:
        try:
            fp = PreflightProfile.model_validate(row.preflight_profile_json)
            by_tenant.setdefault(row.tenant_id, []).append(_profile_summary_from_custom(row, fp))
        except Exception:
            continue

    tenant_blocks: list[AdminTenantProfiles] = [
        AdminTenantProfiles(
            tenant_id=str(tid),
            tenant_name=tenants[tid].name if tid in tenants else None,
            profiles=sorted(profs, key=lambda p: p.profile_id),
        )
        for tid, profs in sorted(
            by_tenant.items(),
            key=lambda kv: (tenants.get(kv[0]).name if kv[0] in tenants else "").lower(),
        )
    ]

    return AdminProfileListResponse(system=system, tenants=tenant_blocks)


@router.get(
    "/tenants/{tenant_id}/profiles/{profile_id}",
    response_model=AdminProfileDetailResponse,
)
async def get_tenant_profile(
    tenant_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminProfileDetailResponse:
    """Get a tenant's custom profile detail (admin, any tenant)."""
    from lintpdf.api.models import CustomProfile
    from lintpdf.profiles.registry import ProfileRegistry
    from lintpdf.profiles.schema import PreflightProfile

    registry = ProfileRegistry()
    if tenant_id == "system":
        if not registry.has(profile_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"System profile '{profile_id}' not found.",
            )
        fp = registry.get(profile_id)
        return AdminProfileDetailResponse(
            profile_id=profile_id,
            tenant_id=None,
            tenant_name=None,
            name=fp.name,
            description=fp.description,
            version=fp.version,
            conformance=fp.conformance,
            workflow=fp.workflow,
            checks=fp.checks.model_dump(),
            thresholds=fp.thresholds.model_dump(),
            is_builtin=True,
        )

    tid = _parse_uuid(tenant_id)
    row: CustomProfile | None = (
        db.query(CustomProfile)
        .filter(CustomProfile.tenant_id == tid, CustomProfile.profile_id == profile_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found for tenant {tenant_id}.",
        )
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    fp = PreflightProfile.model_validate(row.preflight_profile_json)
    return AdminProfileDetailResponse(
        profile_id=profile_id,
        tenant_id=str(tid),
        tenant_name=tenant.name if tenant else None,
        name=fp.name,
        description=fp.description,
        version=fp.version,
        conformance=fp.conformance,
        workflow=fp.workflow,
        checks=fp.checks.model_dump(),
        thresholds=fp.thresholds.model_dump(),
        is_builtin=False,
    )


@router.put(
    "/tenants/{tenant_id}/profiles/{profile_id}",
    response_model=AdminProfileDetailResponse,
)
async def upsert_tenant_profile(
    tenant_id: str,
    profile_id: str,
    body: AdminProfileUpsertRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminProfileDetailResponse:
    """Create or update a tenant's custom profile (admin, any tenant)."""
    from lintpdf.api.models import CustomProfile
    from lintpdf.profiles.registry import ProfileRegistry
    from lintpdf.profiles.schema import PreflightProfile

    registry = ProfileRegistry()
    if registry.has(profile_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile '{profile_id}' is a built-in profile and cannot be overwritten.",
        )

    try:
        fp = PreflightProfile.model_validate(body.preflight_profile)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid Preflight Profile: {exc}",
        ) from exc

    tid = _parse_uuid(tenant_id)
    tenant = db.query(Tenant).filter(Tenant.id == tid).first()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found.",
        )

    existing: CustomProfile | None = (
        db.query(CustomProfile)
        .filter(CustomProfile.tenant_id == tid, CustomProfile.profile_id == profile_id)
        .first()
    )
    if existing:
        existing.preflight_profile_json = fp.model_dump(mode="json")
    else:
        db.add(
            CustomProfile(
                id=uuid_mod.uuid4(),
                tenant_id=tid,
                profile_id=profile_id,
                preflight_profile_json=fp.model_dump(mode="json"),
            )
        )
    db.commit()

    return AdminProfileDetailResponse(
        profile_id=profile_id,
        tenant_id=str(tid),
        tenant_name=tenant.name,
        name=fp.name,
        description=fp.description,
        version=fp.version,
        conformance=fp.conformance,
        workflow=fp.workflow,
        checks=fp.checks.model_dump(),
        thresholds=fp.thresholds.model_dump(),
        is_builtin=False,
    )


@router.delete(
    "/tenants/{tenant_id}/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tenant_profile(
    tenant_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> None:
    """Delete a tenant's custom profile (admin, any tenant)."""
    from lintpdf.api.models import CustomProfile

    tid = _parse_uuid(tenant_id)
    row: CustomProfile | None = (
        db.query(CustomProfile)
        .filter(CustomProfile.tenant_id == tid, CustomProfile.profile_id == profile_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found for tenant {tenant_id}.",
        )
    db.delete(row)
    db.commit()


# ── Tenant entitlement overrides ──────────────────────────────


@router.get("/tenants/{tenant_id}/entitlements", response_model=EffectiveEntitlementsResponse)
async def get_tenant_entitlements(
    tenant_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> EffectiveEntitlementsResponse:
    """Get effective entitlements for a tenant (plan defaults + overrides)."""
    from dataclasses import asdict

    from lintpdf.tenants.entitlements import resolve_entitlements
    from lintpdf.tenants.models import PLAN_LIMITS, TenantPlan

    tenant = _get_tenant(db, tenant_id)
    entitlements = resolve_entitlements(tenant)

    return EffectiveEntitlementsResponse(
        plan=tenant.plan,
        plan_defaults=dict(PLAN_LIMITS[TenantPlan(tenant.plan)]),
        overrides=tenant.entitlement_overrides or {},
        effective=asdict(entitlements),
    )


@router.patch("/tenants/{tenant_id}/entitlements", response_model=EntitlementOverridesResponse)
async def update_tenant_entitlements(
    tenant_id: str,
    body: UpdateEntitlementsRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> EntitlementOverridesResponse:
    """Set per-tenant entitlement overrides. Only provided fields are merged."""
    tenant = _get_tenant(db, tenant_id)
    current = dict(tenant.entitlement_overrides or {})

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No overrides provided.",
        )

    current.update(updates)
    tenant.entitlement_overrides = current
    db.commit()

    return EntitlementOverridesResponse(
        id=str(tenant.id),
        entitlement_overrides=current,
        updated=True,
    )


@router.delete(
    "/tenants/{tenant_id}/entitlements",
    response_model=EntitlementOverridesResponse,
)
async def reset_tenant_entitlements(
    tenant_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> EntitlementOverridesResponse:
    """Reset all per-tenant overrides (tenant falls back to plan defaults)."""
    tenant = _get_tenant(db, tenant_id)
    tenant.entitlement_overrides = None
    db.commit()

    return EntitlementOverridesResponse(
        id=str(tenant.id),
        entitlement_overrides=None,
        updated=True,
    )


# ── Helpers ──────────────────────────────────────────────────


def _parse_uuid(value: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid UUID.",
        ) from exc


def _get_tenant(db: Session, tenant_id: str) -> Tenant:
    uid = _parse_uuid(tenant_id)
    tenant: Tenant | None = db.query(Tenant).filter(Tenant.id == uid).first()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return tenant


def _tenant_to_detail(t: Tenant) -> AdminTenantDetail:
    return AdminTenantDetail(
        id=str(t.id),
        name=t.name,
        plan=t.plan,
        rate_limit_daily=t.rate_limit_daily,
        max_file_size_mb=t.max_file_size_mb,
        contact_email=t.contact_email,
        overage_enabled=t.overage_enabled,
        overage_cap_cents=t.overage_cap_cents,
        stripe_customer_id=t.stripe_customer_id,
        entitlement_overrides=t.entitlement_overrides,
        is_active=t.is_active,
        created_at=t.created_at.isoformat(),
    )


# --- Admin AI Endpoints ---


@router.get("/tenants/{tenant_id}/ai")
async def get_tenant_ai_status(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(_verify_admin_key),
) -> dict[str, Any]:
    """View a tenant's AI status and configuration."""
    tenant = _get_tenant(db, tenant_id)

    from lintpdf.ai.config import get_or_create_ai_config

    config = get_or_create_ai_config(tenant.id, db)
    db.commit()

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "ai_enabled": config.ai_enabled,
        "billing_mode": str(config.billing_mode),
        "credit_balance": float(config.credit_balance),
        "trial_enabled": config.trial_enabled,
        "trial_expires_at": config.trial_expires_at.isoformat()
        if config.trial_expires_at
        else None,
        "enabled_categories": config.enabled_categories or [],
    }


@router.put("/tenants/{tenant_id}/ai")
async def update_tenant_ai(
    tenant_id: str,
    db: Session = Depends(get_db),
    _admin: str = Depends(_verify_admin_key),
    ai_enabled: bool | None = None,
    billing_mode: str | None = None,
    overage_rate: float | None = None,
    enabled_categories: str | None = None,
    monthly_spending_limit: float | None = None,
) -> dict[str, Any]:
    """Enable/disable AI features for a tenant (admin only)."""
    tenant = _get_tenant(db, tenant_id)

    from lintpdf.ai.config import admin_update_ai_config

    updates: dict[str, Any] = {}
    if ai_enabled is not None:
        updates["ai_enabled"] = ai_enabled
    if billing_mode is not None:
        updates["billing_mode"] = billing_mode
    if overage_rate is not None:
        updates["overage_rate"] = overage_rate
    if enabled_categories is not None:
        updates["enabled_categories"] = [
            c.strip() for c in enabled_categories.split(",") if c.strip()
        ]
    if monthly_spending_limit is not None:
        updates["monthly_spending_limit"] = monthly_spending_limit

    config = admin_update_ai_config(tenant.id, updates, db)
    db.commit()

    return {
        "tenant_id": str(tenant.id),
        "ai_enabled": config.ai_enabled,
        "billing_mode": str(config.billing_mode),
        "message": "AI configuration updated",
    }


@router.post("/tenants/{tenant_id}/ai/credits")
async def grant_tenant_ai_credits(
    tenant_id: str,
    credit_amount: int = 1000,
    price_paid: float = 0.0,
    db: Session = Depends(get_db),
    _admin: str = Depends(_verify_admin_key),
) -> dict[str, Any]:
    """Grant AI credits to a tenant (admin only)."""
    from decimal import Decimal

    tenant = _get_tenant(db, tenant_id)

    from lintpdf.api.models import TenantAICreditPackage

    package = TenantAICreditPackage(
        tenant_id=tenant.id,
        credits_purchased=credit_amount,
        credits_remaining=credit_amount,
        price_paid=Decimal(str(price_paid)),
    )
    db.add(package)
    db.commit()

    return {
        "tenant_id": str(tenant.id),
        "package_id": str(package.id),
        "credits_granted": credit_amount,
        "message": "AI credits granted",
    }


@router.put("/tenants/{tenant_id}/ai/trial")
async def set_tenant_ai_trial(
    tenant_id: str,
    trial_enabled: bool = True,
    trial_days: int = 14,
    db: Session = Depends(get_db),
    _admin: str = Depends(_verify_admin_key),
) -> dict[str, Any]:
    """Set AI trial period for a tenant (admin only)."""
    from datetime import datetime, timedelta, timezone

    tenant = _get_tenant(db, tenant_id)

    from lintpdf.ai.config import admin_update_ai_config

    expires_at = datetime.now(timezone.utc) + timedelta(days=trial_days) if trial_enabled else None

    admin_update_ai_config(
        tenant.id,
        {
            "ai_enabled": True,
            "trial_enabled": trial_enabled,
            "trial_expires_at": expires_at,
        },
        db,
    )
    db.commit()

    return {
        "tenant_id": str(tenant.id),
        "trial_enabled": trial_enabled,
        "trial_expires_at": expires_at.isoformat() if expires_at else None,
        "message": "AI trial configured",
    }


@router.get("/ai/usage")
async def get_all_ai_usage(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _admin: str = Depends(_verify_admin_key),
) -> dict[str, Any]:
    """View AI usage across all tenants (admin only)."""
    from sqlalchemy import func

    from lintpdf.api.models import AIUsageLog

    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    total = db.query(AIUsageLog).count()
    logs = (
        db.query(AIUsageLog)
        .order_by(desc(AIUsageLog.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    agg = db.query(
        func.coalesce(func.sum(AIUsageLog.credits_consumed), 0),
        func.coalesce(func.sum(AIUsageLog.cost), 0),
    ).first()

    return {
        "entries": [
            {
                "id": str(log.id),
                "tenant_id": str(log.tenant_id),
                "job_id": str(log.job_id) if log.job_id else None,
                "category": log.category,
                "feature": log.feature,
                "credits_consumed": log.credits_consumed,
                "cost": float(log.cost),
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "total_credits": int(agg[0]) if agg else 0,
        "total_cost": float(agg[1]) if agg else 0.0,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ── Site-level branding (Prisma AppSettings — shared DB) ──────────


class SiteBrandingRequest(BaseModel):
    """Update Pixie Dust AppSettings branding columns.

    The engine and the Next.js app share the same PostgreSQL database.
    This endpoint updates the Prisma-managed AppSettings table directly
    via raw SQL so the login page, dashboard, and emails reflect the
    configured brand identity.
    """

    app_name: str | None = None
    brand_logo_url: str | None = None
    brand_logo_url_dark: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    favicon_url: str | None = None
    login_bg_color: str | None = None
    login_heading: str | None = None
    login_subheading: str | None = None


@router.patch("/site-branding")
async def update_site_branding(
    body: SiteBrandingRequest,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> dict[str, Any]:
    """Update the Pixie Dust AppSettings branding (admin only).

    Writes directly to the shared PostgreSQL database's AppSettings table
    that the Next.js app reads for login page, dashboard, and email branding.
    """
    from sqlalchemy import text

    # Build SET clause from non-null fields
    # Column names must match the Prisma schema exactly (camelCase, quoted)
    updates: dict[str, str] = {}
    if body.app_name is not None:
        updates['"brandName"'] = body.app_name
    if body.brand_logo_url is not None:
        updates['"brandLogoUrl"'] = body.brand_logo_url
    if body.brand_logo_url_dark is not None:
        updates['"brandLogoUrlDark"'] = body.brand_logo_url_dark
    if body.primary_color is not None:
        updates['"primaryColor"'] = body.primary_color
    if body.accent_color is not None:
        updates['"accentColor"'] = body.accent_color
    if body.favicon_url is not None:
        updates['"faviconUrl"'] = body.favicon_url
    if body.login_bg_color is not None:
        updates['"loginBgColor"'] = body.login_bg_color
    if body.login_heading is not None:
        updates['"loginHeading"'] = body.login_heading
    if body.login_subheading is not None:
        updates['"loginSubheading"'] = body.login_subheading

    if not updates:
        return {"updated": False, "message": "No fields to update"}

    # Build parameterized UPDATE
    set_clauses = []
    params: dict[str, str] = {}
    for i, (col, val) in enumerate(updates.items()):
        param_name = f"v{i}"
        set_clauses.append(f"{col} = :{param_name}")
        params[param_name] = val

    sql = f'UPDATE "AppSettings" SET {", ".join(set_clauses)}'
    db.execute(text(sql), params)
    db.commit()

    return {"updated": True, "fields": list(updates.keys())}


# ── Preflight Audit (cross-tenant end-to-end visibility) ─────
#
# Read-only surface for super-admins. Returns the **full** picture for each
# job — raw result JSON, all imported report blobs, every report token, the
# input PDF via presigned URL, findings with pagination, and submission
# context — without modifying the existing ``AdminJobDetail`` contract used
# by the Jobs page.


_TEXT_FORMATS = {
    "pitstop_xml",
    "callas_xml",
    "acrobat_xml",
    "callas_json",
    "lintpdf_json",
}
_INLINE_TEXT_MAX_BYTES = 2_000_000
_PRESIGN_EXPIRES_SECONDS = 900


def _iso(dt: Any) -> str | None:
    """Render a datetime column as ISO-8601 or None."""
    return dt.isoformat() if dt else None


def _presign_with_expiry(file_key: str) -> tuple[str, str]:
    """Generate a presigned GET URL plus an ISO-8601 expiry timestamp."""
    from datetime import datetime, timedelta, timezone

    storage = get_storage()
    url = storage.generate_presigned_url(file_key, expires_in=_PRESIGN_EXPIRES_SECONDS)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=_PRESIGN_EXPIRES_SECONDS)
    ).isoformat()
    return url, expires_at


def _public_report_url(token: str, fmt: str) -> str:
    """Build the public ``/r/{token}[.{ext}]`` URL for a given report token."""
    from lintpdf.api.config import get_settings

    base = get_settings().report_base_url.rstrip("/")
    # HTML is served at bare ``/r/{token}``; other formats use the file-suffix route.
    if fmt == "html":
        return f"{base}/r/{token}"
    return f"{base}/r/{token}.{fmt}"


def _group_label(group_by: str, key: str, tenant_names: dict[Any, str]) -> str:
    """Render a human-readable label for a group bucket."""
    if group_by == "tenant":
        try:
            return tenant_names.get(uuid_mod.UUID(key), key)
        except ValueError:
            return key
    if group_by == "source":
        return {"engine": "Engine", "external": "External import", "minimal": "Minimal"}.get(
            key, key or "Unknown"
        )
    if group_by == "format":
        return key or "—"
    if group_by == "date":
        return key
    return key


@router.get("/audit/jobs", response_model=AdminAuditListResponse)
async def list_audit_jobs(
    tenant_id: str | None = Query(None, description="Filter by tenant UUID."),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by job status (pending/processing/complete/failed).",
    ),
    preflight_source: str | None = Query(None, description="Filter by preflight_source enum."),
    external_format: str | None = Query(None, description="Filter by external_format string."),
    date_from: str | None = Query(None, description="ISO-8601 lower bound on created_at."),
    date_to: str | None = Query(None, description="ISO-8601 upper bound on created_at."),
    q: str | None = Query(
        None,
        description="Substring match against file_name (case-insensitive).",
    ),
    group_by: str = Query(
        "tenant",
        description="Group key: tenant | source | format | date.",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminAuditListResponse:
    """Cross-tenant preflight audit list with grouping + filters."""
    from lintpdf.api.models import JobFinding, JobImportedReport, ReportToken

    if group_by not in {"tenant", "source", "format", "date"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="group_by must be one of: tenant, source, format, date.",
        )

    query = db.query(Job)
    if tenant_id:
        try:
            query = query.filter(Job.tenant_id == uuid_mod.UUID(tenant_id))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid tenant_id: {tenant_id}",
            ) from exc
    if status_filter:
        query = query.filter(Job.status == status_filter)
    if preflight_source:
        query = query.filter(Job.preflight_source == preflight_source)
    if external_format:
        query = query.filter(Job.external_format == external_format)
    if date_from:
        query = query.filter(Job.created_at >= date_from)
    if date_to:
        query = query.filter(Job.created_at <= date_to)
    if q:
        query = query.filter(Job.file_name.ilike(f"%{q}%"))

    total = query.count()
    jobs: list[Job] = (
        query.order_by(desc(Job.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    )

    # Batch fetches to avoid N+1.
    job_ids = [j.id for j in jobs]
    tenant_ids = {j.tenant_id for j in jobs}
    tenant_names = {t.id: t.name for t in db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).all()}

    imported_counts: dict[Any, int] = {}
    if job_ids:
        for job_id_val, cnt in (
            db.query(JobImportedReport.job_id, func.count(JobImportedReport.id))  # type: ignore[attr-defined]
            .filter(JobImportedReport.job_id.in_(job_ids))
            .group_by(JobImportedReport.job_id)
            .all()
        ):
            imported_counts[job_id_val] = int(cnt)

    token_counts: dict[Any, int] = {}
    if job_ids:
        for job_id_val, cnt in (
            db.query(ReportToken.job_id, func.count(ReportToken.id))  # type: ignore[attr-defined]
            .filter(ReportToken.job_id.in_(job_ids))
            .group_by(ReportToken.job_id)
            .all()
        ):
            token_counts[job_id_val] = int(cnt)

    finding_counts: dict[Any, int] = {}
    if job_ids:
        for job_id_val, cnt in (
            db.query(JobFinding.job_id, func.count(JobFinding.id))  # type: ignore[attr-defined]
            .filter(JobFinding.job_id.in_(job_ids))
            .group_by(JobFinding.job_id)
            .all()
        ):
            finding_counts[job_id_val] = int(cnt)

    # Assemble rows, then group.
    rows: list[AdminAuditJobRow] = []
    group_keys: list[tuple[str, AdminAuditJobRow]] = []
    for j in jobs:
        source_val = (
            j.preflight_source.value
            if hasattr(j.preflight_source, "value")
            else (str(j.preflight_source) if j.preflight_source else None)
        )
        status_val = j.status.value if hasattr(j.status, "value") else str(j.status)
        row = AdminAuditJobRow(
            id=str(j.id),
            tenant_id=str(j.tenant_id),
            tenant_name=tenant_names.get(j.tenant_id),
            file_name=j.file_name,
            status=status_val,
            profile_id=j.profile_id,
            preflight_source=source_val,
            external_format=j.external_format,
            created_at=j.created_at.isoformat(),
            completed_at=_iso(j.completed_at),
            page_count=j.page_count,
            duration_ms=j.duration_ms,
            verdict=j.verdict,
            has_imported_report=imported_counts.get(j.id, 0) > 0,
            report_token_count=token_counts.get(j.id, 0),
            findings_count=finding_counts.get(j.id, 0),
        )
        rows.append(row)

        if group_by == "tenant":
            gkey = str(j.tenant_id)
        elif group_by == "source":
            gkey = source_val or "unknown"
        elif group_by == "format":
            gkey = j.external_format or "—"
        else:  # date
            gkey = j.created_at.date().isoformat()
        group_keys.append((gkey, row))

    # Bucket into ordered groups (preserves descending-created order within buckets).
    buckets: dict[str, list[AdminAuditJobRow]] = {}
    order: list[str] = []
    for gkey, row in group_keys:
        if gkey not in buckets:
            buckets[gkey] = []
            order.append(gkey)
        buckets[gkey].append(row)

    groups = [
        AdminAuditGroup(
            key=gkey,
            label=_group_label(group_by, gkey, tenant_names),
            count=len(buckets[gkey]),
            jobs=buckets[gkey],
        )
        for gkey in order
    ]

    return AdminAuditListResponse(
        groups=groups,
        total=total,
        page=page,
        page_size=page_size,
        group_by=group_by,
        filters_applied={
            "tenant_id": tenant_id,
            "status": status_filter,
            "preflight_source": preflight_source,
            "external_format": external_format,
            "date_from": date_from,
            "date_to": date_to,
            "q": q,
        },
    )


@router.get("/audit/jobs/{job_id}", response_model=AdminJobAuditDetail)
async def get_audit_job_detail(
    job_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminJobAuditDetail:
    """Full audit detail: every column, every artifact, every share link."""
    from lintpdf.api.models import (
        ApprovalChain,
        JobFinding,
        JobImportedReport,
        ReportToken,
        TrialFile,
        TrialSubmission,
        ViewerAnnotation,
    )

    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job id: {job_id}",
        ) from exc

    job: Job | None = db.query(Job).filter(Job.id == uid).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    tenant = db.query(Tenant).filter(Tenant.id == job.tenant_id).first()

    # Presigned GET for the input PDF. If the bucket round-trip fails (e.g.
    # object deleted), surface None rather than raising — the rest of the
    # audit page is still useful.
    input_pdf: AdminPresignedBlob | None = None
    try:
        url, expires_at = _presign_with_expiry(job.file_key)
        input_pdf = AdminPresignedBlob(
            presigned_url=url, expires_at=expires_at, size_bytes=job.file_size
        )
    except Exception:  # pragma: no cover — best-effort, surface absence as None
        input_pdf = None

    # Imported reports (raw third-party preflight blobs).
    imported_rows = (
        db.query(JobImportedReport)
        .filter(JobImportedReport.job_id == uid)
        .order_by(JobImportedReport.parsed_at)
        .all()
    )
    imported_reports: list[AdminImportedReportDetail] = []
    storage = get_storage()
    for ir in imported_rows:
        try:
            url, expires_at = _presign_with_expiry(ir.raw_blob_key)
        except Exception:  # pragma: no cover
            url, expires_at = "", ""
        inline_text: str | None = None
        if ir.format in _TEXT_FORMATS and ir.raw_size_bytes <= _INLINE_TEXT_MAX_BYTES:
            try:
                blob = storage.download_raw(ir.raw_blob_key)
                if blob is not None:
                    inline_text = blob.decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover
                inline_text = None
        imported_reports.append(
            AdminImportedReportDetail(
                id=str(ir.id),
                format=ir.format,
                parser_version=ir.parser_version,
                raw_size_bytes=ir.raw_size_bytes,
                source_metadata=ir.source_metadata,
                parsed_at=ir.parsed_at.isoformat(),
                raw_blob_presigned_url=url,
                expires_at=expires_at,
                inline_text=inline_text,
            )
        )

    # All report tokens for this job (HTML / JSON / XML / PDF).
    token_rows = (
        db.query(ReportToken)
        .filter(ReportToken.job_id == uid)
        .order_by(desc(ReportToken.created_at))
        .all()
    )
    report_tokens = [
        AdminReportTokenDetail(
            id=str(tok.id),
            token=tok.token,
            format=tok.format,
            public_url=_public_report_url(tok.token, tok.format),
            expires_at=_iso(tok.expires_at),
            created_at=tok.created_at.isoformat(),
            accessed_count=tok.accessed_count,
            last_accessed_at=_iso(tok.last_accessed_at),
            brand_mode=tok.brand_mode,
            brand_profile_id=str(tok.brand_profile_id) if tok.brand_profile_id else None,
            allow_annotations=tok.allow_annotations,
        )
        for tok in token_rows
    ]

    # Counts.
    findings_count = (
        db.query(func.count(JobFinding.id)).filter(JobFinding.job_id == uid).scalar() or 0
    )
    annotations_count = (
        db.query(func.count(ViewerAnnotation.id)).filter(ViewerAnnotation.job_id == uid).scalar()
        or 0
    )

    # Submission context: figure out where this job originated.
    submission_source = "api"
    trial_submission_id: str | None = None
    trial_submitter_email: str | None = None
    trial_file = db.query(TrialFile).filter(TrialFile.job_id == uid).first()
    if trial_file is not None:
        submission_source = "trial"
        trial_submission_id = str(trial_file.submission_id)
        sub = (
            db.query(TrialSubmission).filter(TrialSubmission.id == trial_file.submission_id).first()
        )
        if sub is not None:
            trial_submitter_email = sub.email
    submission_context = AdminSubmissionContext(
        source=submission_source,
        trial_submission_id=trial_submission_id,
        trial_submitter_email=trial_submitter_email,
        endpoint_slug=None,
        request_metadata=None,
    )

    # Approval chain (at most one per job, by unique index).
    approvals: AdminApprovalSummary | None = None
    chain = db.query(ApprovalChain).filter(ApprovalChain.job_id == uid).first()
    if chain is not None:
        step_rows: list[AdminApprovalStepSummary] = []
        raw_steps = chain.steps if isinstance(chain.steps, list) else []
        for i, step in enumerate(raw_steps):
            if not isinstance(step, dict):
                continue
            step_rows.append(
                AdminApprovalStepSummary(
                    index=i,
                    status=str(step.get("status", "pending")),
                    approver_email=step.get("approver_email"),
                    decided_at=step.get("decided_at"),
                    notes=step.get("notes"),
                )
            )
        approvals = AdminApprovalSummary(
            chain_id=str(chain.id),
            template_id=str(chain.template_id) if chain.template_id else None,
            status=chain.status,
            current_step=chain.current_step,
            steps=step_rows,
            created_at=chain.created_at.isoformat(),
            completed_at=_iso(chain.completed_at),
        )

    source_val = (
        job.preflight_source.value
        if hasattr(job.preflight_source, "value")
        else (str(job.preflight_source) if job.preflight_source else None)
    )
    status_val = job.status.value if hasattr(job.status, "value") else str(job.status)

    return AdminJobAuditDetail(
        id=str(job.id),
        tenant_id=str(job.tenant_id),
        tenant_name=tenant.name if tenant else None,
        status=status_val,
        profile_id=job.profile_id,
        file_name=job.file_name,
        file_key=job.file_key,
        file_size=job.file_size,
        page_count=job.page_count,
        duration_ms=job.duration_ms,
        created_at=job.created_at.isoformat(),
        completed_at=_iso(job.completed_at),
        error_message=job.error_message,
        preflight_source=source_val,
        external_format=job.external_format,
        data_capabilities=job.data_capabilities,
        brand_profile_id_override=(
            str(job.brand_profile_id_override) if job.brand_profile_id_override else None
        ),
        unbranded_override=job.unbranded_override,
        jdf_overrides=job.jdf_overrides,
        color_quality_score=(
            float(job.color_quality_score) if job.color_quality_score is not None else None
        ),
        verdict=job.verdict,
        verdict_by=job.verdict_by,
        verdict_at=_iso(job.verdict_at),
        verdict_notes=job.verdict_notes,
        result_json=job.result_json if isinstance(job.result_json, dict) else None,
        input_pdf=input_pdf,
        imported_reports=imported_reports,
        report_tokens=report_tokens,
        findings_count=int(findings_count),
        annotations_count=int(annotations_count),
        submission_context=submission_context,
        approvals=approvals,
    )


@router.get(
    "/audit/jobs/{job_id}/findings",
    response_model=AdminAuditFindingsResponse,
)
async def list_audit_findings(
    job_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminAuditFindingsResponse:
    """Paginated list of individual findings for a job."""
    from lintpdf.api.models import JobFinding

    try:
        uid = uuid_mod.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid job id: {job_id}",
        ) from exc

    total = db.query(func.count(JobFinding.id)).filter(JobFinding.job_id == uid).scalar() or 0
    rows = (
        db.query(JobFinding)
        .filter(JobFinding.job_id == uid)
        .order_by(JobFinding.page_num, JobFinding.severity)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AdminAuditFindingsResponse(
        findings=[
            AdminAuditFindingRow(
                id=str(r.id),
                inspection_id=r.inspection_id,
                severity=r.severity,
                message=r.message,
                page_num=r.page_num,
                category=r.category,
                source=r.source,
                object_id=r.object_id,
                object_type=r.object_type,
                bbox_x0=r.bbox_x0,
                bbox_y0=r.bbox_y0,
                bbox_x1=r.bbox_x1,
                bbox_y1=r.bbox_y1,
                details=r.details,
            )
            for r in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.get(
    "/audit/imported-reports/{imported_report_id}",
    response_model=AdminPresignedBlob,
)
async def refresh_imported_report_presigned_url(
    imported_report_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(_verify_admin_key),
) -> AdminPresignedBlob:
    """Mint a fresh presigned GET URL for an imported-report raw blob."""
    from lintpdf.api.models import JobImportedReport

    try:
        uid = uuid_mod.UUID(imported_report_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid imported report id: {imported_report_id}",
        ) from exc

    row: JobImportedReport | None = (
        db.query(JobImportedReport).filter(JobImportedReport.id == uid).first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Imported report not found."
        )

    url, expires_at = _presign_with_expiry(row.raw_blob_key)
    return AdminPresignedBlob(
        presigned_url=url, expires_at=expires_at, size_bytes=row.raw_size_bytes
    )
