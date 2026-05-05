"""``WhitelabelService`` — entitlement-gated custom-domain resolution (W6c-6).

Used by ``lintpdf.reports.service.resolve_report_base_url`` and
``resolve_viewer_base_url`` to pick the customer-facing URL host.

The OSS engine ships ``BrandProfile`` + ``Tenant`` as core models —
every deploy needs per-tenant logos, colors, palettes. What's
SaaS-only is the **whitelabel tier**: gating ``custom_domain`` /
``app_custom_domain`` resolution behind a billing-plan entitlement.

OSS default always returns ``settings.report_base_url`` /
``settings.app_base_url`` (no whitelabeling — every tenant sees the
global default). SaaS impl reads ``entitlements.whitelabel_enabled``
and the verified custom-domain fields on ``BrandProfile`` / ``Tenant``.

Hosted SaaS overrides via ``set_whitelabel_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from lintpdf.api.config import Settings
    from lintpdf.api.models import BrandProfile
    from lintpdf.services.tenant_context import TenantContext
    from lintpdf.tenants.entitlements import TenantEntitlements

logger = logging.getLogger(__name__)


class WhitelabelService(Protocol):
    """Resolve customer-facing base URLs honoring the whitelabel tier."""

    def resolve_report_base_url(
        self,
        tenant: TenantContext,
        brand_profile: BrandProfile | None,
        entitlements: TenantEntitlements,
        settings: Settings,
    ) -> str:
        """Pick the report base URL. Returns ``settings.report_base_url`` on OSS."""
        ...

    def resolve_viewer_base_url(
        self,
        tenant: TenantContext,
        brand_profile: BrandProfile | None,
        entitlements: TenantEntitlements,
        settings: Settings,
    ) -> str:
        """Pick the viewer handoff base URL on OSS."""
        ...

    def probe_pending_domains(self, db) -> dict[str, int]:  # type: ignore[no-untyped-def]
        """Beat-driven sweep: flip ``verified=True`` on unverified custom domains.

        Returns a counter dict (``{"checked": N, "activated": M, "cname_mismatch": K}``)
        for the Celery task's structured log output.
        """
        ...


class DefaultWhitelabelService:
    """OSS default: always returns the global settings URLs.

    OSS deploys have no whitelabel tier — every tenant uses the same
    ``report_base_url`` / ``app_base_url`` regardless of any
    ``custom_domain`` field set on their BrandProfile / Tenant row.
    """

    def resolve_report_base_url(
        self,
        tenant: TenantContext,
        brand_profile: BrandProfile | None,
        entitlements: TenantEntitlements,
        settings: Settings,
    ) -> str:
        return settings.report_base_url

    def resolve_viewer_base_url(
        self,
        tenant: TenantContext,
        brand_profile: BrandProfile | None,
        entitlements: TenantEntitlements,
        settings: Settings,
    ) -> str:
        return settings.viewer_handoff_base_url

    def probe_pending_domains(self, db) -> dict[str, int]:  # type: ignore[no-untyped-def]
        # OSS-only deploys have no custom-domain concept — beat tick is a no-op.
        return {"checked": 0, "activated": 0, "cname_mismatch": 0}


_service: WhitelabelService | None = None


def get_whitelabel_service() -> WhitelabelService:
    global _service
    if _service is None:
        _service = DefaultWhitelabelService()
    return _service


def set_whitelabel_service(service: WhitelabelService | None) -> None:
    global _service
    _service = service
