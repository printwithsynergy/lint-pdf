"""File-quota balance + consumption.

Mirrors ``lintpdf.ai.credits`` for the AI side, but instead of a
separate AIUsageLog we count ``Job`` rows within the current billing
period. Balance = (active file-pack packages with credits_remaining > 0).

FIFO deduction on submit: subtract from the oldest active package
first. When the active pool is exhausted, the request either falls
back to the existing rate_limit_daily guard or is rejected with 402
depending on ``Tenant.overage_enabled`` — same shape as the AI overage
story.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

    from lintpdf.api.models import Tenant

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileQuotaBalance:
    """Snapshot of the tenant's metered-file-quota position right now."""

    tenant_id: uuid.UUID
    total_remaining: int
    monthly_allotment_remaining: int  # from source='plan_monthly' packages
    purchased_remaining: int  # from source='purchase' packages
    active_packages: int


def get_file_quota_balance(tenant_id: uuid.UUID, db: Session) -> FileQuotaBalance:
    """Return the caller's file-quota balance broken down by source."""
    from lintpdf.api.models import TenantAICreditPackage

    now = datetime.now(timezone.utc)
    packages = (
        db.query(TenantAICreditPackage)
        .filter(
            TenantAICreditPackage.tenant_id == tenant_id,
            TenantAICreditPackage.kind == "files",
            TenantAICreditPackage.credits_remaining > 0,
        )
        .all()
    )
    active = [p for p in packages if p.expires_at is None or p.expires_at > now]
    monthly = sum(p.credits_remaining for p in active if p.source == "plan_monthly")
    purchased = sum(p.credits_remaining for p in active if p.source != "plan_monthly")
    return FileQuotaBalance(
        tenant_id=tenant_id,
        total_remaining=monthly + purchased,
        monthly_allotment_remaining=monthly,
        purchased_remaining=purchased,
        active_packages=len(active),
    )


def check_and_consume_file_quota(
    tenant: Tenant,
    files_requested: int,
    db: Session,
) -> FileQuotaBalance:
    """Deduct ``files_requested`` from the tenant's metered file pool.

    Raises 402 Payment Required if the tenant has a plan allotment of 0
    and hasn't bought any packs (and overage is off). Rolling out:

    * If ``monthly_files_included == 0`` AND no active file packs →
      behave exactly like before (rely on ``rate_limit_daily``).
    * Else deduct from oldest package first; if the pool drains and
      ``overage_enabled`` is True, allow the request and let the
      existing Pixie Dust usage tracker bill overage per-job.
    """
    from lintpdf.api.models import TenantAICreditPackage
    from lintpdf.tenants.entitlements import resolve_entitlements

    # Materialise entitlements for its side-effects (plan resolution
    # errors surface here) even though we don't need the current
    # monthly_files_included value on the fall-through path.
    resolve_entitlements(tenant)
    tenant_id: uuid.UUID = tenant.id

    # No metered-resource packs for this tenant yet — either their plan
    # allots 0 files, or invoice.paid hasn't fired since the feature
    # rolled out. Fall through to the legacy rate_limit_daily-only path
    # without decrementing anything. Once the allocator runs (on the
    # next billing cycle or via the admin grant endpoint) subsequent
    # submits will correctly decrement the monthly pool.
    if not _has_active_file_packs(tenant_id, db):
        return get_file_quota_balance(tenant_id, db)

    now = datetime.now(timezone.utc)
    packages = (
        db.query(TenantAICreditPackage)
        .filter(
            TenantAICreditPackage.tenant_id == tenant_id,
            TenantAICreditPackage.kind == "files",
            TenantAICreditPackage.credits_remaining > 0,
        )
        .order_by(TenantAICreditPackage.purchased_at.asc())
        .all()
    )

    remaining = files_requested
    for pkg in packages:
        if pkg.expires_at and pkg.expires_at <= now:
            continue
        if remaining <= 0:
            break
        deduct = min(remaining, pkg.credits_remaining)
        pkg.credits_remaining -= deduct
        remaining -= deduct

    if remaining > 0:
        # Pool exhausted — decide: overage or reject.
        if not getattr(tenant, "overage_enabled", False):
            # Fire the exhausted webhook BEFORE raising so subscribers
            # see the signal even on the 402 path.
            try:
                from lintpdf.webhooks.events import fire_billing_threshold

                fire_billing_threshold(
                    db,
                    tenant_id,
                    resource="file_quota",
                    severity="exhausted",
                    remaining=0,
                )
                db.flush()
            except Exception:
                logger.exception("file_quota.exhausted webhook emit failed")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Monthly file quota exceeded (need {files_requested}, "
                    f"have 0 remaining). Purchase a file pack or enable "
                    f"overage billing to continue."
                ),
            )
        logger.info(
            "file_quota overage: tenant=%s requested=%s overspend=%s",
            tenant_id,
            files_requested,
            remaining,
        )

    db.flush()
    post_balance = get_file_quota_balance(tenant_id, db)

    # Low-water-mark alert: fire when we cross the 10% threshold on
    # decrement (i.e. previous balance was above 10% and current is at
    # or below). Threshold compares the monthly allotment share so
    # tenants with large pools get a useful warning window.
    try:
        total = post_balance.total_remaining
        monthly = post_balance.monthly_allotment_remaining + post_balance.purchased_remaining
        # Use monthly+purchased as the denominator fallback when there's
        # no plan allotment (tenant bought purely ad-hoc packs).
        if total > 0 and monthly > 0:
            before = total + files_requested
            pct_before = before / max(monthly + files_requested, 1)
            pct_after = total / max(monthly + files_requested, 1)
            if pct_before > 0.10 >= pct_after:
                from lintpdf.webhooks.events import fire_billing_threshold

                fire_billing_threshold(
                    db,
                    tenant_id,
                    resource="file_quota",
                    severity="low",
                    remaining=total,
                    allotment=monthly + files_requested,
                )
                db.flush()
    except Exception:
        logger.exception("file_quota.low threshold check failed")

    return post_balance


def _has_active_file_packs(tenant_id: uuid.UUID, db: Session) -> bool:
    from lintpdf.api.models import TenantAICreditPackage

    now = datetime.now(timezone.utc)
    q = db.query(TenantAICreditPackage).filter(
        TenantAICreditPackage.tenant_id == tenant_id,
        TenantAICreditPackage.kind == "files",
        TenantAICreditPackage.credits_remaining > 0,
    )
    return any((p.expires_at is None or p.expires_at > now) for p in q)
