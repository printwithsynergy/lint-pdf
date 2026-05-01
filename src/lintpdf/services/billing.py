"""``BillingService`` — route-layer metered-resource enforcement (Phase 5 W4).

Engine route handlers gate file-quota consumption on tenant billing
state: when a tenant submits a preflight job, the engine checks
their metered file pool and either deducts a unit or 402s with
"upgrade required". Today this lives in
``lintpdf.billing.file_quota.check_and_consume_file_quota``, which
is Stripe-coupled (it reads the tenant's metered package balance
from the SaaS-side billing table).

The Protocol declared here lets routes accept the billing service
via ``Depends(get_billing_service)`` instead. The default factory
returns ``DefaultBillingService`` which forwards to the existing
helper — bit-for-bit identical for the SaaS deploy. SaaS hosts that
want custom billing logic (e.g. an on-prem deploy with no Stripe)
flip the dep via ``app.dependency_overrides``:

    from lintpdf.services.billing import get_billing_service
    from lintpdf_saas.billing.file_quota import SaaSBillingService

    app.dependency_overrides[get_billing_service] = lambda: SaaSBillingService()

OSS hosts that boot the engine standalone get a permissive default:
the no-op stub never raises, every quota check passes. Until the
SaaS shell wires its real Stripe-backed implementation, the
behaviour is "unmetered" — fine for OSS deploys with no billing
concept at all.

Pattern matches Phase 5 W2 (``EmailService``) + W3
(``EntitlementsService``) — Protocol + factory + ``Depends`` +
override-friendly. Each route migration is a literal swap of the
import + handler-signature parameter.
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

        Raises an HTTPException (typically 402 Payment Required) if
        the tenant has no allotment + no overage allowed. SaaS impl
        forwards to ``lintpdf.billing.file_quota.check_and_consume_file_quota``;
        OSS no-op stub returns ``None`` and never raises.
        """
        ...


class DefaultBillingService:
    """Default implementation: forwards to the existing
    ``lintpdf.billing.file_quota.check_and_consume_file_quota`` helper.

    Bit-for-bit identical to pre-DI behaviour. Stays in OSS until the
    wider ``lintpdf.billing`` module physically extracts to
    ``lintpdf_saas``; at that point, this default flips to a permissive
    no-op stub and the SaaS shell wires its real impl via
    ``app.dependency_overrides``.
    """

    def check_and_consume_file_quota(
        self,
        tenant: Any,
        files_requested: int,
        db: Any,
    ) -> Any:
        from lintpdf.billing.file_quota import check_and_consume_file_quota

        return check_and_consume_file_quota(tenant, files_requested=files_requested, db=db)


_default_factory = DefaultBillingService


def get_billing_service() -> BillingService:
    """FastAPI dependency factory.

    The default returns a ``DefaultBillingService`` that forwards to
    the existing ``check_and_consume_file_quota`` helper. SaaS hosts
    and tests override via ``app.dependency_overrides``:

        app.dependency_overrides[get_billing_service] = lambda: MyBillingService()
    """

    return _default_factory()
