"""``PlanOverridesService`` — plan-tier limit override resolver (W6c).

The OSS engine's entitlement resolver
(``lintpdf.tenants.entitlements.resolve_plan_overrides``) needs a
plan-tier override lookup hook. The OSS package itself has no notion
of plan tiers (that's a SaaS / multi-tenant concept), so the default
implementation here is a pure no-op that returns ``{}`` for every
call. ``resolve_entitlements`` falls back to the
``EntitlementDefaultsService`` baseline (a permissive everything-
enabled bag on OSS-only deploys; the real SaaS plan-tier baselines
on hosted SaaS) when overrides are empty.

The SaaS shell installs its own implementation at boot via
``set_plan_overrides_service`` that queries the SaaS-only
``plan_limit_overrides`` table.

Pure factory pattern (no FastAPI ``Depends``) because the consumer
is a library helper called from non-route contexts (Celery boot,
plan-tier lookups in scoring, CLI tooling) where ``Depends``
injection isn't available.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class PlanOverridesService(Protocol):
    """Resolve a plan tier's ops-editable override block."""

    def resolve_for_plan(self, plan_value: str) -> dict[str, Any]:
        """Return the override dict for ``plan_value`` (e.g. ``"growth"``).

        Returns an empty dict when no override row exists, when the
        DB session can't be opened, when the backing table is absent,
        or when the model class itself isn't importable. The
        resolver always falls open (no override) rather than raising
        — the entitlement system has hardcoded defaults to fall back
        on.
        """
        ...


class DefaultPlanOverridesService:
    """Pure no-op default — OSS engine ships zero plan-tier overrides.

    Plan-tier overrides are a SaaS concept (operator-edited rows in
    a multi-tenant database). The OSS preflight engine has no notion
    of plan tiers at all; ``resolve_entitlements`` falls back to the
    ``EntitlementDefaultsService`` baseline when this returns ``{}``.

    Hosted SaaS deployments override the factory at boot via
    ``set_plan_overrides_service(SaaSPlanOverridesService())``
    (in ``lintpdf_saas.api.app:create_app``). That implementation
    queries the ``plan_limit_overrides`` table.

    No SaaS-only model imports here — that's the W6c-1 invariant.
    """

    def resolve_for_plan(self, plan_value: str) -> dict[str, Any]:
        return {}


_service: PlanOverridesService | None = None


def get_plan_overrides_service() -> PlanOverridesService:
    """Return the configured ``PlanOverridesService`` (singleton)."""
    global _service
    if _service is None:
        _service = DefaultPlanOverridesService()
    return _service


def set_plan_overrides_service(service: PlanOverridesService | None) -> None:
    """Install a custom ``PlanOverridesService``.

    The SaaS shell calls this at boot in ``lintpdf_saas.api.app:create_app``
    to inject a service that reads from ``lintpdf_saas.api.models``.
    Pass ``None`` to reset to the default for tests.
    """
    global _service
    _service = service
