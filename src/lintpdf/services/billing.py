"""``BillingService`` — route-layer metered-resource enforcement (Phase 5 W4).

Engine route handlers gate file-quota consumption on tenant billing
state: when a tenant submits a preflight job, the engine checks
their metered file pool and either deducts a unit or 402s with
"upgrade required".

The Protocol declared here lets routes accept the billing service
via ``Depends(get_billing_service)``. The OSS default is a
permissive no-op (no metered-resource concept on OSS-only deploys).
The SaaS shell installs ``SaaSBillingService`` via
``app.dependency_overrides`` at boot, which forwards to
``lintpdf_saas.billing.file_quota.check_and_consume_file_quota``.

Pattern matches Phase 5 W2 (``EmailService``) + W3
(``EntitlementsService``) — Protocol + factory + ``Depends`` +
override-friendly.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class BillingService(Protocol):
    """Route-layer billing/quota service.

    Implementations gate metered resource usage and either deduct
    a unit or raise a 402-equivalent HTTPException. The return type
    is intentionally ``Any`` at the Protocol level so the Protocol
    stays decoupled from the ``FileQuotaBalance`` dataclass that
    lives inside ``lintpdf.billing.file_quota`` (a SaaS-side module
    that moves to ``lintpdf_saas`` in a later PR). Concrete
    implementations return the SaaS-flavoured balance object.
    """

    def check_and_consume_file_quota(
        self,
        tenant: Any,
        files_requested: int,
        db: Any,
    ) -> Any:
        """Reserve ``files_requested`` from the tenant's metered file pool.

        SaaS impl raises HTTPException(402) when the pool is dry and
        overage is off; OSS no-op stub returns ``None`` and never raises.
        """
        ...


class DefaultBillingService:
    """Permissive no-op default. OSS engine has no metered-resource concept.

    The SaaS shell installs ``SaaSBillingService`` (which forwards to
    ``lintpdf_saas.billing.file_quota.check_and_consume_file_quota``)
    via ``app.dependency_overrides`` at boot. OSS-only deploys get
    "no quota enforcement, no errors" — appropriate since OSS has no
    Stripe / metered packs concept.
    """

    def check_and_consume_file_quota(
        self,
        tenant: Any,
        files_requested: int,
        db: Any,
    ) -> Any:
        return None


_default_factory = DefaultBillingService


def get_billing_service() -> BillingService:
    """FastAPI dependency factory.

    The default returns a ``DefaultBillingService`` that forwards to
    the existing ``check_and_consume_file_quota`` helper. SaaS hosts
    and tests override via ``app.dependency_overrides``:

        app.dependency_overrides[get_billing_service] = lambda: MyBillingService()
    """

    return _default_factory()
