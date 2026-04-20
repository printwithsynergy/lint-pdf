"""Brand profile CRUD endpoints."""

from __future__ import annotations

import re
import uuid as uuid_mod
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel as _BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import BrandProfile, BrandProfileType, Tenant
from lintpdf.api.schemas import (
    BrandProfileCreateRequest,
    BrandProfileListResponse,
    BrandProfileResponse,
    BrandProfileUpdateRequest,
    SetCustomDomainRequest,
    SetDefaultBrandProfileRequest,
    TenantCustomDomainResponse,
)

router = APIRouter(tags=["branding"])


# --- Custom report domain validation ---
#
# The validator is intentionally strict because the value ends up in a
# URL we hand out to the customer's end users. An invalid hostname here
# would break every report link the customer generates.

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
_BLOCKED_EXACT: frozenset[str] = frozenset({"lintpdf.com", "localhost", "example.com", "invalid"})
_BLOCKED_SUFFIXES: tuple[str, ...] = (
    ".lintpdf.com",
    ".railway.app",
    ".railway.internal",
    ".localhost",
    ".local",
    ".internal",
    ".example.com",
    ".invalid",
    ".test",
)


def validate_custom_domain(raw: str) -> str:
    """Normalize + validate a customer-submitted custom report domain.

    Returns the canonical lowercase hostname on success. Raises HTTP
    422 on any format issue or if the domain is on the blocklist
    (LintPDF-owned hosts, localhost, Railway internals).
    """
    d = (raw or "").strip().lower().rstrip(".")
    # Reject scheme or path
    if "://" in d or "/" in d or " " in d or ":" in d:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Custom domain must be a bare hostname — no scheme, path, or port. "
                "Example: reports.acmeprint.com"
            ),
        )
    if not _HOSTNAME_RE.match(d):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That doesn't look like a valid hostname.",
        )
    if d in _BLOCKED_EXACT or any(d.endswith(s) for s in _BLOCKED_SUFFIXES):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That domain is reserved and can't be used as a custom report domain.",
        )
    return d


def _resolve_dns_target(alias: str | None, fallback: str | None = None) -> str:
    """Return the CNAME target for a customer's BYO custom domain.

    Always ``edge.lintpdf.com`` — our Fly.io Caddy edge that
    terminates TLS (on-demand Let's Encrypt) and path-routes to the
    Railway backends. Every BYO customer CNAMEs here regardless of
    whether they also have an auto-provisioned branded subdomain
    (``{slug}-custom.lintpdf.com``).

    The ``alias`` parameter is ACCEPTED for signature back-compat but
    no longer used as the CNAME target: the alias represents a
    separate UX surface (a LintPDF-branded URL the tenant can use
    directly without any DNS work), NOT a CNAME target for BYO. An
    alias-bearing tenant who also wants BYO still CNAMEs to
    ``edge.lintpdf.com`` and adds their branded URL as an additional
    share option in-product.

    Legacy callers passed ``reports.lintpdf.com`` / ``app.lintpdf.com``
    as the fallback -- those were the old "shared service hostname"
    values that predate the Caddy edge and don't work for cert
    issuance anymore (Railway's per-domain validator doesn't chase
    CNAME chains). ``edge.lintpdf.com`` is the single correct answer.
    """
    # Alias intentionally unused; see docstring. Kept in signature so
    # existing call sites don't need to change.
    del alias
    return fallback or "edge.lintpdf.com"


def _cleanup_alias_best_effort(alias_fqdn: str | None) -> None:
    """Delete the Cloudflare CNAME record for a cleared custom domain.

    Graceful: never raises. If Cloudflare is unreachable or the token
    is missing the orphan record stays in the zone, which is harmless
    (it points at a Railway target that'll 404 for any request that
    isn't the now-deleted custom domain). Ops can clean up manually
    later.
    """
    if not alias_fqdn:
        return
    try:
        from lintpdf.integrations.cloudflare import CloudflareClient

        cf = CloudflareClient()
        result = cf.delete_cname(alias_fqdn)
        if result.status not in ("deleted", "not_found", "disabled"):
            import logging

            logging.getLogger(__name__).warning(
                "Cloudflare alias cleanup for %s returned %s: %s",
                alias_fqdn,
                result.status,
                result.message,
            )
    except Exception:  # noqa: BLE001 -- never block a customer API call
        import logging

        logging.getLogger(__name__).exception(
            "Cloudflare alias cleanup crashed for %s", alias_fqdn
        )


def _provision_alias_sync(tenant_id: Any, purpose: str = "") -> str | None:
    """Create the Cloudflare DNS record for a customer's branded subdomain NOW.

    Historically this happened asynchronously in the Celery probe task
    (up to 5-min delay before the customer's dashboard showed the
    final ``dns_target``). Calling it inline on the admin / tenant
    PATCH endpoint means customers see the branded target the moment
    they submit their hostname -- no probe-beat wait.

    Uses the same slug logic as the probe task so repeated calls are
    idempotent (second call hits the ``already_correct`` branch and
    returns without a DB or CF write).

    Returns the FQDN on success, or None if CF is unreachable /
    disabled. Never raises -- a CF outage must not block a tenant's
    domain submission; the probe task still runs periodically and
    will fill the column on the next cycle.
    """
    try:
        from lintpdf.integrations.cloudflare import CloudflareClient
        from lintpdf.queue.tasks import _alias_slug, _provision_alias

        slug = _alias_slug(tenant_id, purpose)
        cf = CloudflareClient()
        # We don't have a required_cname here because Railway hasn't
        # registered the domain yet (that happens async in the probe
        # task). Pass a sentinel: _provision_alias only uses the arg
        # as a "did Railway give us anything?" gate, and the CNAME
        # record target is hardcoded to ``lintpdf.com`` anyway (the
        # edge Worker intercepts before DNS resolves to any IP).
        fqdn, _ = _provision_alias(cf, slug, "lintpdf.com")
        return fqdn
    except Exception:  # noqa: BLE001 -- never block a customer API call
        import logging

        logging.getLogger(__name__).exception(
            "Synchronous alias provision crashed for tenant=%s purpose=%s",
            tenant_id,
            purpose,
        )
        return None


def _profile_to_response(profile: BrandProfile, tenant: Tenant) -> BrandProfileResponse:
    """Convert a BrandProfile model to a response schema."""
    return BrandProfileResponse(
        id=profile.id,
        name=profile.name,
        profile_type=profile.profile_type.value,
        brand_name=profile.brand_name,
        logo_url=profile.logo_url,
        primary_color=profile.primary_color,
        accent_color=profile.accent_color,
        footer_text=profile.footer_text,
        hide_footer=profile.hide_footer,
        is_default=tenant.default_brand_profile_id == profile.id,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        custom_domain=profile.custom_domain,
        custom_domain_verified=profile.custom_domain_verified,
        custom_domain_dns_target=_resolve_dns_target(profile.custom_domain_alias)
        if profile.custom_domain
        else None,
        app_custom_domain=profile.app_custom_domain,
        app_custom_domain_verified=profile.app_custom_domain_verified,
        app_custom_domain_dns_target=_resolve_dns_target(profile.app_custom_domain_alias)
        if profile.app_custom_domain
        else None,
    )


@router.get(
    "/api/v1/tenants/{tenant_id}/brand-profiles",
    response_model=BrandProfileListResponse,
)
async def list_brand_profiles(
    tenant_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileListResponse:
    """List all brand profiles for the tenant."""
    profiles = (
        db.query(BrandProfile)
        .filter(BrandProfile.tenant_id == tenant.id)
        .order_by(BrandProfile.created_at)
        .all()
    )
    return BrandProfileListResponse(profiles=[_profile_to_response(p, tenant) for p in profiles])


@router.post(
    "/api/v1/tenants/{tenant_id}/brand-profiles",
    response_model=BrandProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand_profile(
    tenant_id: str,
    request: BrandProfileCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Create a new brand profile."""
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if not entitlements.whitelabel_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brand profiles require Scale or Enterprise plan.",
        )

    # Validate profile type
    try:
        profile_type = BrandProfileType(request.profile_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid profile type: {request.profile_type}. Must be custom, lintpdf, or none.",
        ) from exc

    profile = BrandProfile(
        id=uuid_mod.uuid4(),
        tenant_id=tenant.id,
        name=request.name,
        profile_type=profile_type,
        brand_name=request.brand_name,
        logo_url=request.logo_url,
        primary_color=request.primary_color,
        accent_color=request.accent_color,
        footer_text=request.footer_text,
        hide_footer=request.hide_footer,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)


@router.get(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}",
    response_model=BrandProfileResponse,
)
async def get_brand_profile(
    tenant_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Get a brand profile by ID."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    return _profile_to_response(profile, tenant)


@router.put(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}",
    response_model=BrandProfileResponse,
)
async def update_brand_profile(
    tenant_id: str,
    profile_id: str,
    request: BrandProfileUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Update a brand profile."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    if request.name is not None:
        profile.name = request.name
    if request.profile_type is not None:
        try:
            profile.profile_type = BrandProfileType(request.profile_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid profile type: {request.profile_type}.",
            ) from exc
    if request.brand_name is not None:
        profile.brand_name = request.brand_name
    if request.logo_url is not None:
        profile.logo_url = request.logo_url
    if request.primary_color is not None:
        profile.primary_color = request.primary_color
    if request.accent_color is not None:
        profile.accent_color = request.accent_color
    if request.footer_text is not None:
        profile.footer_text = request.footer_text
    if request.hide_footer is not None:
        profile.hide_footer = request.hide_footer

    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)


@router.delete(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_brand_profile(
    tenant_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Delete a brand profile."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    # Clear default if this was the default profile
    if tenant.default_brand_profile_id == uid:
        tenant.default_brand_profile_id = None

    db.delete(profile)
    db.commit()


@router.post(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}/logo",
    response_model=BrandProfileResponse,
)
async def upload_brand_logo(
    tenant_id: str,
    profile_id: str,
    file: UploadFile = File(
        ...,
        description=(
            "Logo image (PNG, JPEG, SVG, or WebP). Maximum 2 MB. Stored in "
            "the tenant's custom-domain bucket when verified, otherwise in "
            "the global reports host."
        ),
    ),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Upload a logo for a brand profile."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    # Validate file type
    if file.content_type not in ("image/png", "image/jpeg", "image/svg+xml", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Logo must be PNG, JPEG, SVG, or WebP.",
        )

    # Read file content
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Logo file must be under 2 MB.",
        )

    # Upload to storage
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    file_key = f"brand-logos/{tenant.id}/{profile.id}.{ext}"
    # ``StorageBackend`` exposes ``upload_raw(key, data, content_type, ...)``;
    # the earlier ``upload_file`` name never existed. This line has been
    # broken since the brand-logo upload endpoint shipped — any logo-upload
    # attempt 500s with AttributeError. Caught while setting up the
    # "Print With Synergy" demo tenant.
    storage.upload_raw(
        file_key,
        content,
        content_type=file.content_type or "image/png",
        cache_control="public, max-age=31536000, immutable",
    )

    # Update profile logo URL using the per-tenant resolver — if the tenant
    # has a verified custom domain, logos come from that host too so the
    # whole report (HTML + <img>) is served under one hostname. Otherwise
    # logos use the global report_base_url (defaults to reports.lintpdf.com).
    from lintpdf.api.config import get_settings
    from lintpdf.reports.service import resolve_report_base_url
    from lintpdf.tenants.entitlements import resolve_entitlements

    settings = get_settings()
    entitlements = resolve_entitlements(tenant)
    base_url = resolve_report_base_url(tenant, profile, entitlements, settings)
    logo_url = f"{base_url}/assets/{file_key}"
    profile.logo_url = logo_url

    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)


@router.patch(
    "/api/v1/tenants/{tenant_id}/default-brand-profile",
    response_model=BrandProfileResponse | None,
)
async def set_default_brand_profile(
    tenant_id: str,
    request: SetDefaultBrandProfileRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse | None:
    """Set or clear the tenant's default brand profile."""
    if request.brand_profile_id is None:
        tenant.default_brand_profile_id = None
        db.commit()
        return None

    profile = (
        db.query(BrandProfile)
        .filter(
            BrandProfile.id == request.brand_profile_id,
            BrandProfile.tenant_id == tenant.id,
        )
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    tenant.default_brand_profile_id = profile.id
    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)


# --- White-label custom report domain (customer self-service) ---


def _tenant_custom_domain_response(tenant: Tenant) -> TenantCustomDomainResponse:
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    return TenantCustomDomainResponse(
        tenant_id=tenant.id,
        domain=tenant.brand_custom_domain,
        verified=tenant.brand_custom_domain_verified,
        requested_at=tenant.brand_custom_domain_requested_at,
        plan_allows_whitelabel=entitlements.whitelabel_enabled,
        dns_target=_resolve_dns_target(tenant.custom_domain_alias),
    )


@router.get(
    "/api/v1/tenants/{tenant_id}/custom-domain",
    response_model=TenantCustomDomainResponse,
)
async def get_tenant_custom_domain(
    tenant_id: str,
    tenant: Tenant = Depends(get_current_tenant),
) -> TenantCustomDomainResponse:
    """Return the current state of the tenant's white-label custom report domain."""
    if str(tenant.id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    return _tenant_custom_domain_response(tenant)


@router.patch(
    "/api/v1/tenants/{tenant_id}/custom-domain",
    response_model=TenantCustomDomainResponse,
)
async def set_tenant_custom_domain(
    tenant_id: str,
    request: SetCustomDomainRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> TenantCustomDomainResponse:
    """Customer self-service: set (or clear) the tenant's white-label custom domain.

    Setting always resets ``brand_custom_domain_verified`` to False —
    only the admin flow (or the DNS probe task) can flip it back to True.

    Returns 403 if the tenant's plan doesn't include the whitelabel
    entitlement (SCALE/ENTERPRISE only), 409 if another tenant already
    claims this domain, 422 if the domain is on the blocklist or
    otherwise invalid.
    """
    if str(tenant.id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if not entitlements.whitelabel_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("White-label custom report domains require the Scale or Enterprise plan."),
        )

    if request.domain is None or request.domain.strip() == "":
        # Clearing -- remove the CF alias too to avoid orphan records
        _cleanup_alias_best_effort(tenant.custom_domain_alias)
        tenant.brand_custom_domain = None
        tenant.brand_custom_domain_verified = False
        tenant.brand_custom_domain_requested_at = None
        tenant.custom_domain_alias = None
    else:
        canonical = validate_custom_domain(request.domain)
        # If the customer is changing domains, tear down the alias for
        # the old one so we provision a fresh alias in the new slug shape.
        if tenant.brand_custom_domain != canonical:
            _cleanup_alias_best_effort(tenant.custom_domain_alias)
            tenant.custom_domain_alias = None
        tenant.brand_custom_domain = canonical
        tenant.brand_custom_domain_verified = False
        tenant.brand_custom_domain_requested_at = datetime.now(timezone.utc)
        # Provision the branded alias NOW so the dashboard shows the
        # final dns_target immediately. The probe task still runs on
        # its 5-min beat to reconcile, but the customer doesn't have
        # to wait for it -- they get their CNAME target right here.
        alias = _provision_alias_sync(tenant.id, "reports")
        if alias:
            tenant.custom_domain_alias = alias

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That domain is already claimed by another tenant.",
        ) from exc

    db.refresh(tenant)
    return _tenant_custom_domain_response(tenant)


@router.patch(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}/custom-domain",
    response_model=BrandProfileResponse,
)
async def set_brand_profile_custom_domain(
    tenant_id: str,
    profile_id: str,
    request: SetCustomDomainRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Customer self-service: set a per-brand-profile custom report domain.

    Useful for agencies serving multiple clients — each brand profile
    can point reports at the owning client's own subdomain.
    """
    if str(tenant.id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if not entitlements.whitelabel_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("White-label custom report domains require the Scale or Enterprise plan."),
        )

    try:
        pid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == pid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    if request.domain is None or request.domain.strip() == "":
        _cleanup_alias_best_effort(profile.custom_domain_alias)
        profile.custom_domain = None
        profile.custom_domain_verified = False
        profile.custom_domain_requested_at = None
        profile.custom_domain_alias = None
    else:
        canonical = validate_custom_domain(request.domain)
        if profile.custom_domain != canonical:
            _cleanup_alias_best_effort(profile.custom_domain_alias)
            profile.custom_domain_alias = None
        profile.custom_domain = canonical
        profile.custom_domain_verified = False
        profile.custom_domain_requested_at = datetime.now(timezone.utc)
        alias = _provision_alias_sync(
            tenant.id, f"profile-{profile.id.hex[:8]}-reports"
        )
        if alias:
            profile.custom_domain_alias = alias

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That domain is already claimed by another brand profile.",
        ) from exc

    db.refresh(profile)
    return _profile_to_response(profile, tenant)


# --- White-label app/viewer custom domain (customer self-service) ---


class AppCustomDomainResponse(_BaseModel):
    tenant_id: str | None = None
    domain: str | None = None
    verified: bool = False
    requested_at: str | None = None
    plan_allows_whitelabel: bool = False
    dns_target: str = "edge.lintpdf.com"
    """The CNAME target customers point their app subdomain at.

    Same semantics as the reports-domain ``dns_target``: either the
    auto-provisioned ``{slug}-custom.lintpdf.com`` alias, or the Fly.io
    Caddy edge (``edge.lintpdf.com``) for BYO. Both reports + app paths
    resolve on the same subdomain via the edge Worker / Caddy's path
    routing -- separate ``dns_target`` fields are preserved for
    historical reasons but return the same value per tenant."""


@router.get(
    "/api/v1/tenants/{tenant_id}/app-custom-domain",
    response_model=AppCustomDomainResponse,
)
async def get_tenant_app_custom_domain(
    tenant_id: str,
    tenant: Tenant = Depends(get_current_tenant),
) -> AppCustomDomainResponse:
    """Return the current state of the tenant's white-label app/viewer domain."""
    if str(tenant.id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    from lintpdf.tenants.entitlements import resolve_entitlements

    ent = resolve_entitlements(tenant)
    return AppCustomDomainResponse(
        tenant_id=str(tenant.id),
        domain=tenant.app_custom_domain,
        verified=tenant.app_custom_domain_verified,
        requested_at=tenant.app_custom_domain_requested_at.isoformat()
        if tenant.app_custom_domain_requested_at
        else None,
        plan_allows_whitelabel=ent.whitelabel_enabled,
        dns_target=_resolve_dns_target(tenant.app_custom_domain_alias),
    )


@router.patch(
    "/api/v1/tenants/{tenant_id}/app-custom-domain",
    response_model=AppCustomDomainResponse,
)
async def set_tenant_app_custom_domain(
    tenant_id: str,
    request: SetCustomDomainRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AppCustomDomainResponse:
    """Customer self-service: set (or clear) the tenant's app/viewer custom domain."""
    if str(tenant.id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    from lintpdf.tenants.entitlements import resolve_entitlements

    ent = resolve_entitlements(tenant)
    if not ent.whitelabel_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="White-label custom domains require the Scale or Enterprise plan.",
        )

    if request.domain is None or request.domain.strip() == "":
        _cleanup_alias_best_effort(tenant.app_custom_domain_alias)
        tenant.app_custom_domain = None
        tenant.app_custom_domain_verified = False
        tenant.app_custom_domain_requested_at = None
        tenant.app_custom_domain_alias = None
    else:
        canonical = validate_custom_domain(request.domain)
        if tenant.app_custom_domain != canonical:
            _cleanup_alias_best_effort(tenant.app_custom_domain_alias)
            tenant.app_custom_domain_alias = None
        tenant.app_custom_domain = canonical
        tenant.app_custom_domain_verified = False
        tenant.app_custom_domain_requested_at = datetime.now(timezone.utc)
        alias = _provision_alias_sync(tenant.id, "app")
        if alias:
            tenant.app_custom_domain_alias = alias

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That domain is already claimed by another tenant.",
        ) from exc

    db.refresh(tenant)
    return AppCustomDomainResponse(
        tenant_id=str(tenant.id),
        domain=tenant.app_custom_domain,
        verified=tenant.app_custom_domain_verified,
        requested_at=tenant.app_custom_domain_requested_at.isoformat()
        if tenant.app_custom_domain_requested_at
        else None,
        plan_allows_whitelabel=ent.whitelabel_enabled,
        dns_target=_resolve_dns_target(tenant.app_custom_domain_alias),
    )


# --- Default output branding (anonymous / profile / LintPDF) -------------


class BrandingDefaultsRequest(_BaseModel):
    """Payload for PATCH /api/v1/tenant/branding-defaults.

    Exactly one of ``mode`` values controls the default: when ``mode`` is
    ``anonymous`` the tenant's ``unbranded_by_default`` flag flips on and
    ``default_brand_profile_id`` is cleared. When ``mode`` is ``profile``
    a ``brand_profile_id`` must be provided. ``lintpdf`` clears both.
    """

    mode: str  # "anonymous" | "profile" | "lintpdf"
    brand_profile_id: str | None = None


class BrandingDefaultsResponse(_BaseModel):
    mode: str
    unbranded_by_default: bool
    default_brand_profile_id: str | None = None


@router.get(
    "/api/v1/tenant/branding-defaults",
    response_model=BrandingDefaultsResponse,
)
async def get_tenant_branding_defaults(
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandingDefaultsResponse:
    """Return the tenant's default-output-branding mode."""
    if tenant.unbranded_by_default:
        mode = "anonymous"
    elif tenant.default_brand_profile_id is not None:
        mode = "profile"
    else:
        mode = "lintpdf"
    return BrandingDefaultsResponse(
        mode=mode,
        unbranded_by_default=tenant.unbranded_by_default,
        default_brand_profile_id=(
            str(tenant.default_brand_profile_id) if tenant.default_brand_profile_id else None
        ),
    )


@router.patch(
    "/api/v1/tenant/branding-defaults",
    response_model=BrandingDefaultsResponse,
)
async def set_tenant_branding_defaults(
    request: BrandingDefaultsRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandingDefaultsResponse:
    """Update the tenant's default output branding.

    Modes:
    * ``anonymous`` — strip all branding + sanitise PDF metadata by default
      (broker → distributor use case). Sets ``unbranded_by_default = True``
      and clears ``default_brand_profile_id``.
    * ``profile`` — use a specific BrandProfile by default. Requires a
      valid ``brand_profile_id`` owned by the tenant.
    * ``lintpdf`` — fall back to LintPDF's built-in branding (clears both).
    """
    mode = (request.mode or "").strip().lower()
    if mode not in {"anonymous", "profile", "lintpdf"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="mode must be one of: anonymous, profile, lintpdf.",
        )

    if mode == "anonymous":
        tenant.unbranded_by_default = True
        tenant.default_brand_profile_id = None
    elif mode == "lintpdf":
        tenant.unbranded_by_default = False
        tenant.default_brand_profile_id = None
    else:  # profile
        if not request.brand_profile_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="brand_profile_id is required when mode='profile'.",
            )
        try:
            profile_uuid = uuid_mod.UUID(request.brand_profile_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="brand_profile_id must be a valid UUID.",
            ) from exc
        profile = (
            db.query(BrandProfile)
            .filter(
                BrandProfile.id == profile_uuid,
                BrandProfile.tenant_id == tenant.id,
            )
            .first()
        )
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand profile not found.",
            )
        tenant.unbranded_by_default = False
        tenant.default_brand_profile_id = profile_uuid

    db.commit()
    db.refresh(tenant)

    if tenant.unbranded_by_default:
        resolved_mode = "anonymous"
    elif tenant.default_brand_profile_id is not None:
        resolved_mode = "profile"
    else:
        resolved_mode = "lintpdf"

    return BrandingDefaultsResponse(
        mode=resolved_mode,
        unbranded_by_default=tenant.unbranded_by_default,
        default_brand_profile_id=(
            str(tenant.default_brand_profile_id) if tenant.default_brand_profile_id else None
        ),
    )
