"""Tenant domain models and plan definitions.

``PLAN_LIMITS`` and the per-plan ``_AI_FEATURES_*`` baselines used to
live here. They were extracted to ``lintpdf_saas.tenants.entitlement_defaults``
in audit-fix #3 (catalog item #3 in audit/saas-residual-modules.md).
The OSS engine no longer carries SaaS plan-tier knowledge -- the
resolver dispatches through ``EntitlementDefaultsService``. OSS-only
deploys get a permissive everything-enabled bag from the default
service; SaaS deploys get the real tier baselines via
``SaaSEntitlementDefaultsService``.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class TenantPlan(enum.StrEnum):
    """Subscription plans -- string-typed identifier read by the engine.

    The engine reads the value as an opaque string; SaaS billing-tier
    semantics (limits, AI feature grants) live in
    ``lintpdf_saas.tenants.entitlement_defaults``.
    """

    FREE = "free"
    VIEWER = "viewer"
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"
    ENTERPRISE = "enterprise"


ALL_PREFLIGHT_SOURCES: list[str] = ["engine", "external", "minimal"]


# Warning thresholds (percentage of limit)
RATE_LIMIT_WARN_THRESHOLD = 80
RATE_LIMIT_OVERAGE_THRESHOLD = 100


@dataclass
class TenantInfo:
    """Domain representation of a tenant (decoupled from DB model)."""

    id: str
    name: str
    plan: TenantPlan
    api_key_hash: str
    rate_limit_daily: int
    max_file_size_mb: int
    is_active: bool = True
    contact_email: str | None = None
    custom_profile_ids: list[str] = field(default_factory=list)
    overage_enabled: bool = False
    overage_cap_cents: int | None = None
    overage_rate_override_cents: int | None = None

    @property
    def overage_rate_cents(self) -> int:
        """Per-job overage charge in cents."""
        if self.overage_rate_override_cents is not None:
            return self.overage_rate_override_cents
        from lintpdf.services.entitlement_defaults import get_entitlement_defaults_service

        return get_entitlement_defaults_service().overage_rate_cents_for(self.plan.value)

    @property
    def overage_allowed(self) -> bool:
        """Whether this tenant can incur billable overages."""
        return self.overage_enabled and self.overage_rate_cents > 0
