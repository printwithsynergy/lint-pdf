"""``EntitlementsService`` — route-layer entitlement resolution (Phase 5 W3).

Engine route handlers gate features on tenant entitlements: viewer
annotations, AI categories, custom profiles, batch submission,
white-label branding, etc. Today they import
``lintpdf.tenants.entitlements.resolve_entitlements`` directly, which
couples the OSS engine to the SaaS-side ``Tenant`` SQLAlchemy model
+ ``PLAN_LIMITS`` table.

The Protocol declared here lets routes accept the resolver via
``Depends(get_entitlements_service)`` instead. The default factory
returns ``DefaultEntitlementsService`` which forwards to the existing
``resolve_entitlements`` helper — bit-for-bit identical behaviour
for the SaaS deploy. SaaS hosts that want custom plan logic
(e.g. an enterprise override that grants every feature) can flip
the dep via ``app.dependency_overrides``:

    from lintpdf.services.entitlements import get_entitlements_service
    from lintpdf_saas.tenants.entitlements import SaaSEntitlementsService

    app.dependency_overrides[get_entitlements_service] = lambda: SaaSEntitlementsService()

OSS hosts that boot the engine standalone get the default permissive
behaviour: every feature enabled, no caps, until the host wires
something more restrictive.

Pattern matches Phase 5 W2 (``EmailService``) — Protocol + factory +
``Depends`` + override-friendly. Each route migration is a literal
swap of the import + handler-signature parameter.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class EntitlementsService(Protocol):
    """Route-layer entitlement resolver.

    Implementations take a tenant identifier (the ORM row in the
    SaaS impl, or any opaque tenant handle in OSS) and return the
    effective ``TenantEntitlements`` snapshot for the request.
    Returning a frozen dataclass means callers can pass the snapshot
    around without worrying about background mutation.
    """

    def resolve(self, tenant: Any) -> Any:
        """Resolve entitlements for a tenant.

        The return type is intentionally ``Any`` at the Protocol
        level so the Protocol stays decoupled from the
        ``TenantEntitlements`` dataclass that lives inside
        ``lintpdf.tenants.entitlements`` (a SaaS-side module that
        moves to ``lintpdf_saas`` in a later PR). Concrete
        implementations return a ``TenantEntitlements`` instance.
        """
        ...


class DefaultEntitlementsService:
    """Default implementation: forwards to the existing
    ``lintpdf.tenants.entitlements.resolve_entitlements`` helper.

    Bit-for-bit identical to pre-DI behaviour. Stays in OSS until
    the wider ``lintpdf.tenants`` module physically extracts to
    ``lintpdf_saas``; at that point, this default flips to a
    permissive "everything-enabled" stub and the SaaS shell wires
    its real impl via ``app.dependency_overrides``.
    """

    def resolve(self, tenant: Any) -> Any:
        # Local import keeps this module loadable when the wider
        # `tenants` package isn't installed (future OSS-only host).
        from lintpdf.tenants.entitlements import resolve_entitlements

        return resolve_entitlements(tenant)


_default_factory = DefaultEntitlementsService


def get_entitlements_service() -> EntitlementsService:
    """FastAPI dependency factory.

    The default returns a ``DefaultEntitlementsService`` that forwards
    to the existing ``resolve_entitlements`` helper. SaaS hosts and
    tests override via ``app.dependency_overrides``:

        app.dependency_overrides[get_entitlements_service] = lambda: MyEntitlementsService()
    """

    return _default_factory()
