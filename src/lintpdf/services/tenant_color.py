"""``TenantColorService`` — per-tenant custom Pantone override resolver (W6c-3).

The engine pre-flight worker (``lintpdf.queue.tasks``) reads the
tenant's custom Pantone override JSON to extend the bundled Pantone
library at runtime. That data is a SaaS-only concern (multi-tenant
configuration); the OSS preflight engine has no notion of per-tenant
customization, so the default implementation here returns ``None``
(no overrides) for every call.

Hosted SaaS deployments override the factory at boot via
``set_tenant_color_service(SaaSTenantColorService())`` (in
``lintpdf_saas.api.app:create_app``). That implementation queries
the SaaS-only ``tenant_color_configs`` table.

Pure factory pattern (no FastAPI ``Depends``) because the consumer
is a Celery worker function, not a route handler. Same shape as
``lintpdf.services.plan_overrides``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TenantColorService(Protocol):
    """Resolve a tenant's custom Pantone override JSON."""

    def get_custom_pantone(self, tenant_id: uuid.UUID, db: Session) -> dict[str, Any] | None:
        """Return the tenant's ``custom_pantone_overrides`` JSON, or ``None``.

        ``None`` means no overrides — the engine falls back to the
        bundled Pantone library. Implementations must never raise;
        the preflight pipeline keeps running on a soft fail.
        """
        ...


class DefaultTenantColorService:
    """Pure no-op default — OSS engine ships zero custom Pantone overrides.

    The OSS preflight engine has no per-tenant concept, so there are
    no custom Pantone overrides to resolve. Every call returns
    ``None`` and the worker falls back to the bundled Pantone
    library.

    Hosted SaaS deployments install ``SaaSTenantColorService`` at
    boot which queries the ``tenant_color_configs`` table. No
    SaaS-only model imports here — that's the W6c invariant.
    """

    def get_custom_pantone(
        self,
        tenant_id: uuid.UUID,
        db: Session,
    ) -> dict[str, Any] | None:
        return None


_service: TenantColorService | None = None


def get_tenant_color_service() -> TenantColorService:
    """Return the configured ``TenantColorService`` (singleton)."""
    global _service
    if _service is None:
        _service = DefaultTenantColorService()
    return _service


def set_tenant_color_service(service: TenantColorService | None) -> None:
    """Install a custom ``TenantColorService``.

    The SaaS shell calls this at boot in
    ``lintpdf_saas.api.app:create_app`` to inject a service that
    reads from ``lintpdf_saas.api.models``. Pass ``None`` to reset
    to the default for tests.
    """
    global _service
    _service = service
