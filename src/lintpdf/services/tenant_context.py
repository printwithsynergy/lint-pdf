"""``TenantContextService`` — opaque tenant-data lookup (W6c-7).

The OSS preflight engine does not own the multi-tenant concept —
``Tenant`` is a SaaS-only model. Engine code that needs to know
"the caller's plan" / "their contact email" / "their default brand
profile" reaches for those values through this service rather than
querying or reading attributes off a SaaS-only ORM class.

The engine never imports ``lintpdf.api.models.Tenant``. Instead it
asks ``get_tenant_context_service().load(tenant_id, db)`` and
operates on the returned :class:`TenantContext` frozen dataclass.

OSS default returns a minimal stub populated from the passed
``tenant_id`` only — every other field is ``None`` or a sensible
zero. SaaS impl reads the actual ``Tenant`` row from
``lintpdf_saas.api.models`` and populates the union of fields the
engine reads today.

Hosted SaaS overrides via ``set_tenant_context_service`` at boot.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TenantContext:
    """Snapshot of the fields the engine reads off a Tenant row.

    Frozen dataclass so the engine treats this as immutable
    request-scoped data — never writes back. SaaS impls should
    populate the relevant subset; OSS default leaves nearly all
    fields ``None``.

    Field categories:
    * Identity — ``id``, ``name``, ``is_active``
    * Auth — ``api_key_hash`` (SaaS-only)
    * Plan / quota — ``plan``, ``rate_limit_daily``, ``max_file_size_mb``,
      ``overage_enabled``, ``overage_cap_cents``, ``overage_rate_override_cents``,
      ``monthly_ai_credits_override``, ``monthly_files_override``,
      ``entitlement_overrides``, ``ai_features`` (all SaaS billing)
    * Communication — ``contact_email`` (SaaS lead-gen)
    * Branding — ``brand_*``, ``app_custom_domain*``,
      ``default_brand_profile_id``, ``default_profile_id``,
      ``unbranded_by_default``, ``share_email_required``,
      ``brand_hide_footer``, ``report_default_expiry_days``,
      ``report_email_enabled``, ``report_summary_page``
    """

    id: uuid.UUID
    name: str = ""
    is_active: bool = True

    # Auth (SaaS-only)
    api_key_hash: str | None = None

    # Plan / quota (SaaS billing)
    plan: str = "free"
    rate_limit_daily: int = 0
    max_file_size_mb: int = 0
    overage_enabled: bool = False
    overage_cap_cents: int | None = None
    overage_rate_override_cents: int | None = None
    monthly_ai_credits_override: int | None = None
    monthly_files_override: int | None = None
    entitlement_overrides: dict[str, Any] | None = None
    ai_features: list[str] = field(default_factory=list)

    # Communication
    contact_email: str | None = None

    # Branding (defaults — concrete BrandProfile resolution happens via
    # the BrandingService chain; these are the tenant-level fallbacks)
    brand_name: str | None = None
    brand_logo_url: str | None = None
    brand_primary_color: str | None = None
    brand_accent_color: str | None = None
    brand_custom_domain: str | None = None
    brand_custom_domain_verified: bool = False
    app_custom_domain: str | None = None
    app_custom_domain_verified: bool = False
    brand_hide_footer: bool = False
    default_brand_profile_id: uuid.UUID | None = None
    default_profile_id: str | None = None
    unbranded_by_default: bool = False

    # Reports
    share_email_required: bool = True
    report_default_expiry_days: int | None = None
    report_email_enabled: bool = True
    report_summary_page: str = "prepend"

    # Webhooks
    webhook_signing_secret: str | None = None


class TenantContextService(Protocol):
    """Look up the engine-visible context for a tenant."""

    def load(self, tenant_id: uuid.UUID, db: Session) -> TenantContext | None:
        """Return the tenant's context snapshot, or ``None`` when not found."""
        ...

    def load_by_api_key_hash(
        self,
        api_key_hash: str,
        db: Session,
    ) -> TenantContext | None:
        """Auth lookup: return the tenant matching this API key, or ``None``."""
        ...


class DefaultTenantContextService:
    """Pure no-op default. Returns a minimal context from the tenant_id only.

    OSS-only deploys that don't ship a SaaS-side ``Tenant`` ORM use
    this default — every tenant looks like a plain ``free``-plan
    record with all SaaS billing / branding fields blank.
    """

    def load(self, tenant_id: uuid.UUID, db: Session) -> TenantContext | None:
        return TenantContext(id=tenant_id)

    def load_by_api_key_hash(
        self,
        api_key_hash: str,
        db: Session,
    ) -> TenantContext | None:
        # No auth concept on OSS-only deploys — caller (likely a SaaS
        # auth middleware) is expected to install a real service.
        return None


_service: TenantContextService | None = None


def get_tenant_context_service() -> TenantContextService:
    global _service
    if _service is None:
        _service = DefaultTenantContextService()
    return _service


def set_tenant_context_service(service: TenantContextService | None) -> None:
    global _service
    _service = service
