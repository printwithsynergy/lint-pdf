"""Metered-resource allocation: monthly grants + Stripe top-up fulfillment.

One allocator handles both kinds ("credits" and "files") by reading
the right entitlement field and writing a ``TenantAICreditPackage``
row with the kind discriminator. Called from:

* ``invoice.paid`` Stripe webhook → ``allocate_monthly(...)``
  (fresh plan-monthly grant per billing cycle, idempotent via
  ``(tenant_id, kind, billing_period_start)``).
* ``checkout.session.completed`` Stripe webhook → ``fulfill_purchase(...)``
  (idempotent via ``stripe_session_id`` unique constraint).
* Admin ``POST /admin/tenants/{id}/ai/credits`` → direct grant bypass
  (source='admin_grant' — the existing endpoint, unchanged).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from lintpdf.billing.metered_packs import PackKind, pack_for_size

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import Tenant

logger = logging.getLogger(__name__)

# Plan-monthly allotments expire at the end of the next billing period.
# Top-ups rolled over for a full year so purchased credits don't vanish
# on the customer mid-project.
_PLAN_MONTHLY_LIFETIME = timedelta(days=32)
_PURCHASE_LIFETIME = timedelta(days=365)


@dataclass
class AllocationResult:
    """What allocate_monthly / fulfill_purchase returns to callers."""

    package_id: uuid.UUID
    kind: PackKind
    amount: int
    source: str
    created: bool  # False when the call hit an idempotency dedupe


def allocate_monthly(
    tenant: Tenant,
    kind: Literal["credits", "files"],
    db: Session,
    *,
    billing_period_start: datetime,
    source_event: str = "invoice.paid",
) -> AllocationResult | None:
    """Grant a tenant their plan-monthly allotment of ``kind`` resources.

    Idempotent on ``(tenant_id, kind, billing_period_start)`` so a
    replayed Stripe webhook never double-grants. If the resolved
    allotment is 0 (e.g. FREE plan, no override), returns None.

    The allotment is read from the tenant's resolved entitlements,
    which already layers:
        plan default → entitlement_overrides JSON → per-tenant override column
    """
    from lintpdf.api.models import TenantAICreditPackage
    from lintpdf.tenants.entitlements import resolve_entitlements

    ents = resolve_entitlements(tenant)
    amount = ents.monthly_ai_credits if kind == "credits" else ents.monthly_files_included
    if amount <= 0:
        logger.info(
            "allocate_monthly skip: tenant=%s kind=%s amount=0 (plan=%s source=%s)",
            tenant.id,
            kind,
            tenant.plan,
            source_event,
        )
        return None

    # Dedupe: has this (tenant, kind, period) already been granted?
    existing = (
        db.query(TenantAICreditPackage)
        .filter(
            TenantAICreditPackage.tenant_id == tenant.id,
            TenantAICreditPackage.kind == kind,
            TenantAICreditPackage.source == "plan_monthly",
            TenantAICreditPackage.billing_period_start == billing_period_start,
        )
        .first()
    )
    if existing is not None:
        logger.info(
            "allocate_monthly dedupe: tenant=%s kind=%s period=%s package=%s",
            tenant.id,
            kind,
            billing_period_start.isoformat(),
            existing.id,
        )
        return AllocationResult(
            package_id=existing.id,
            kind=kind,
            amount=existing.credits_purchased,
            source="plan_monthly",
            created=False,
        )

    pkg = TenantAICreditPackage(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        kind=kind,
        source="plan_monthly",
        credits_purchased=amount,
        credits_remaining=amount,
        price_paid=Decimal("0"),
        billing_period_start=billing_period_start,
        expires_at=billing_period_start + _PLAN_MONTHLY_LIFETIME,
    )
    db.add(pkg)
    db.flush()  # surface constraint violations before the caller commits
    logger.info(
        "allocate_monthly grant: tenant=%s kind=%s amount=%s period=%s package=%s",
        tenant.id,
        kind,
        amount,
        billing_period_start.isoformat(),
        pkg.id,
    )
    return AllocationResult(
        package_id=pkg.id,
        kind=kind,
        amount=amount,
        source="plan_monthly",
        created=True,
    )


def fulfill_purchase(
    tenant_id: uuid.UUID,
    kind: Literal["credits", "files"],
    pack_size: int,
    price_cents: int,
    stripe_session_id: str,
    db: Session,
) -> AllocationResult:
    """Insert a purchased pack into the metered-resource table.

    Called by the engine's internal fulfilment endpoint (hit by the
    Stripe webhook worker). Idempotent via the unique index on
    ``stripe_session_id`` — a replayed webhook returns the existing
    package row instead of creating a duplicate.
    """
    from sqlalchemy.exc import IntegrityError

    from lintpdf.api.models import TenantAICreditPackage

    # Sanity: the pack size must be a known SKU.
    defn = pack_for_size(kind, pack_size)
    if defn is None:
        raise ValueError(f"Unknown {kind} pack size: {pack_size}")

    existing = (
        db.query(TenantAICreditPackage)
        .filter(TenantAICreditPackage.stripe_session_id == stripe_session_id)
        .first()
    )
    if existing is not None:
        return AllocationResult(
            package_id=existing.id,
            kind=kind,
            amount=existing.credits_purchased,
            source="purchase",
            created=False,
        )

    pkg = TenantAICreditPackage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        kind=kind,
        source="purchase",
        credits_purchased=pack_size,
        credits_remaining=pack_size,
        price_paid=Decimal(price_cents) / Decimal(100),
        stripe_session_id=stripe_session_id,
        expires_at=datetime.now(timezone.utc) + _PURCHASE_LIFETIME,
    )
    db.add(pkg)
    try:
        db.flush()
    except IntegrityError:
        # Concurrent webhook fulfilment raced us — return the winner.
        db.rollback()
        winner = (
            db.query(TenantAICreditPackage)
            .filter(TenantAICreditPackage.stripe_session_id == stripe_session_id)
            .first()
        )
        if winner is None:
            raise
        return AllocationResult(
            package_id=winner.id,
            kind=kind,
            amount=winner.credits_purchased,
            source="purchase",
            created=False,
        )
    logger.info(
        "fulfill_purchase: tenant=%s kind=%s size=%s session=%s package=%s",
        tenant_id,
        kind,
        pack_size,
        stripe_session_id,
        pkg.id,
    )
    return AllocationResult(
        package_id=pkg.id,
        kind=kind,
        amount=pack_size,
        source="purchase",
        created=True,
    )
