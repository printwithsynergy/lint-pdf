"""Admin API endpoints for internal services (Stripe plugin, Pixie Dust)."""

from __future__ import annotations

import uuid as uuid_mod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import generate_api_key, hash_api_key, verify_admin_key
from lintpdf.api.database import get_db
from lintpdf.api.models import ApiKey, Job, Tenant
from lintpdf.api.schemas import (
    AdminCustomDomainListResponse,
    AdminUpdateCustomDomainRequest,
)

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


class AdminJobListResponse(BaseModel):
    jobs: list[AdminJobSummary]
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
    from lintpdf.api.models import BrandProfile
    from lintpdf.api.schemas import AdminCustomDomainRow

    tenant_rows = (
        db.query(Tenant)
        .filter(Tenant.brand_custom_domain.isnot(None))
        .all()
    )
    profile_rows = (
        db.query(BrandProfile, Tenant)
        .join(Tenant, BrandProfile.tenant_id == Tenant.id)
        .filter(BrandProfile.custom_domain.isnot(None))
        .all()
    )

    pending: list[AdminCustomDomainRow] = []
    active: list[AdminCustomDomainRow] = []

    for t in tenant_rows:
        row = AdminCustomDomainRow(
            scope="tenant",
            tenant_id=t.id,
            tenant_name=t.name,
            brand_profile_id=None,
            brand_profile_name=None,
            domain=t.brand_custom_domain or "",
            verified=t.brand_custom_domain_verified,
            requested_at=t.brand_custom_domain_requested_at,
        )
        (active if t.brand_custom_domain_verified else pending).append(row)

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

    return AdminTenantResponse(
        id=str(tenant.id), name=tenant.name, plan=tenant.plan, updated=True
    )


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
                status=j.status,
                profile_id=j.profile_id,
                file_name=j.file_name,
                created_at=j.created_at.isoformat(),
            )
            for j in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


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
    updates: dict[str, str] = {}
    if body.app_name is not None:
        updates['"appName"'] = body.app_name
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

