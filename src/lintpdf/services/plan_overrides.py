"""``PlanOverridesService`` — plan-tier limit override resolver (W6c).

The OSS engine's entitlement resolver
(``lintpdf.tenants.entitlements.resolve_plan_overrides``) needs to
read ops-editable per-plan-tier overrides — e.g. raising the daily
rate limit on the Growth plan from 600 to 1000 without bumping
everyone to Scale. Today that lookup imports the
``PlanLimitOverride`` model from ``lintpdf.api.models`` and queries
it directly. After W6 the model moves to ``lintpdf_saas.api.models``
and the OSS package no longer ships it.

This Protocol gives the engine a typed seam to call without knowing
where the model lives. The default implementation does what today's
code does: query ``lintpdf.api.models.PlanLimitOverride`` if
importable, else return ``{}``. The SaaS shell overrides the factory
at boot via ``set_plan_overrides_service`` to install a
``SaaSPlanOverridesService`` that reads from
``lintpdf_saas.api.models.PlanLimitOverride``.

Pure factory pattern (no FastAPI ``Depends``) because the consumer
(``entitlements.resolve_plan_overrides``) is a library helper called
from non-route contexts (Celery boot, plan-tier lookups in scoring,
CLI tooling) where ``Depends`` injection isn't available.
"""

from __future__ import annotations

import contextlib
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
    """Reads ``lintpdf.api.models.PlanLimitOverride`` directly.

    This is the implementation the OSS engine ships pre-W6
    extraction. After ``PlanLimitOverride`` moves to
    ``lintpdf_saas.api.models``, the import here fails and every
    call returns ``{}`` — i.e. OSS-only deploys without
    ``lintpdf_saas`` installed never see plan-tier overrides. The
    SaaS shell overrides this with its own implementation that
    knows about the moved model.
    """

    def resolve_for_plan(self, plan_value: str) -> dict[str, Any]:
        from lintpdf.api.database import get_db_session

        try:
            from lintpdf.api.models import PlanLimitOverride  # type: ignore[attr-defined]
        except ImportError:
            return {}

        try:
            session = get_db_session()
        except Exception:  # pragma: no cover — DB not initialised
            return {}

        try:
            with contextlib.closing(session):
                row = (
                    session.query(PlanLimitOverride)
                    .filter(PlanLimitOverride.plan == plan_value)
                    .first()
                )
                if row is None or not row.overrides:
                    return {}
                return dict(row.overrides)
        except Exception:
            # Missing table (pre-035) or transient DB flap — fall
            # through to plan defaults rather than raising.
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
