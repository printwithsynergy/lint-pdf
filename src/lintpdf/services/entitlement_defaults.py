"""``EntitlementDefaultsService`` — plan-tier baselines for the entitlement resolver.

The OSS engine has no concept of subscription plans / billing tiers
— every deploy uses the same permissive defaults. The SaaS shell
installs an implementation that returns per-tier baselines (the
``PLAN_LIMITS`` dict that used to live in ``lintpdf.tenants.models``).

Used by ``lintpdf.tenants.entitlements.resolve_entitlements`` to
seed the layer-0 defaults dict that subsequent layers
(``plan_limit_overrides``, per-tenant ``entitlement_overrides``
JSON, dedicated columns) merge on top of.

Hosted SaaS overrides via ``set_entitlement_defaults_service`` at
boot.
"""

from __future__ import annotations

from typing import Any, Protocol

# OSS-default permissive baseline.
#
# OSS deploys have no SaaS billing-tier mapping. The engine resolver
# still needs SOMETHING to seed the layer-0 defaults dict, so we
# return an everything-enabled, generous-limits bag. Real values
# come from the SaaS-side impl (see ``lintpdf_saas.tenants.entitlements_defaults``).
#
# Numbers chosen so an OSS-only deploy doesn't accidentally clamp
# itself to a free-tier ceiling: rate limits high enough that abuse
# is the only realistic blocker, every report format allowed, every
# capability enabled, AI feature gate fully open. The OSS host can
# always tighten via per-tenant overrides if it wants.
_OSS_PERMISSIVE_DEFAULTS: dict[str, Any] = {
    "rate_limit_daily": 1_000_000,
    "max_file_size_mb": 4096,
    "max_custom_profiles": 10_000,
    "overage_rate_cents": 0,
    "report_storage_mb": 1_048_576,
    "report_default_expiry_days": 365,
    "allowed_report_formats": [
        "json",
        "html",
        "pdf",
        "xml",
        "annotated_pdf",
        "annotated_pdf_markup",
    ],
    "allowed_preflight_sources": ["engine", "external", "minimal"],
    "capability_fillin_enabled": True,
    "annotations_enabled": True,
    "webhooks_enabled": True,
    "whitelabel_enabled": True,
    "priority_processing": True,
    "custom_integrations": True,
    "custom_profiles": True,
    "max_webhooks": 1_000,
    "approval_chains_enabled": True,
    "max_approval_templates": None,
    "desktop_app_enabled": True,
    "monthly_ai_credits": 1_000_000,
    "monthly_files_included": 1_000_000,
    "ai_features": [
        "audit",
        "ocr",
        "dieline",
        "art_size",
        "legend",
        "similarity",
        "internal_opus",
        "sonnet_fallback",
    ],
}


class EntitlementDefaultsService(Protocol):
    """Resolve the baseline entitlements dict for a tenant's plan."""

    def defaults_for(self, plan: str) -> dict[str, Any]:
        """Return the layer-0 defaults dict for ``plan``.

        SaaS impl returns ``PLAN_LIMITS[TenantPlan(plan)]`` (or the
        FREE-tier fallback for unknown plan strings); OSS default
        returns a permissive everything-enabled bag regardless of
        ``plan``.
        """
        ...

    def overage_rate_cents_for(self, plan: str) -> int:
        """Return the overage rate (cents per file) for ``plan``.

        SaaS impl reads ``PLAN_LIMITS[TenantPlan(plan)]["overage_rate_cents"]``;
        OSS default returns 0 (no overage on OSS-only deploys).
        """
        ...


class DefaultEntitlementDefaultsService:
    """OSS default: returns a permissive everything-enabled bag.

    Ignores the ``plan`` argument because OSS deploys have no plan
    tier concept — every tenant gets the same generous defaults.
    """

    def defaults_for(self, plan: str) -> dict[str, Any]:
        return dict(_OSS_PERMISSIVE_DEFAULTS)

    def overage_rate_cents_for(self, plan: str) -> int:
        return 0


_service: EntitlementDefaultsService | None = None


def get_entitlement_defaults_service() -> EntitlementDefaultsService:
    global _service
    if _service is None:
        _service = DefaultEntitlementDefaultsService()
    return _service


def set_entitlement_defaults_service(
    service: EntitlementDefaultsService | None,
) -> None:
    global _service
    _service = service
