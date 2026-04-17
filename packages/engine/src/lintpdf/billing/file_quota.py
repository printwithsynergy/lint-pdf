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
    tenant: object,
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

    ents = resolve_entitlements(tenant)
    tenant_id = tenant.id if hasattr(tenant, "id") else tenant  # type: ignore[union-attr]

    # Plan doesn't use metered files — no-op (legacy daily-only path).
    if ents.monthly_files_included <= 0 and not _has_active_file_packs(tenant_id, db):
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
    return get_file_quota_balance(tenant_id, db)


def _has_active_file_packs(tenant_id: uuid.UUID, db: Session) -> bool:
    from lintpdf.api.models import TenantAICreditPackage

    now = datetime.now(timezone.utc)
    q = (
        db.query(TenantAICreditPackage)
        .filter(
            TenantAICreditPackage.tenant_id == tenant_id,
            TenantAICreditPackage.kind == "files",
            TenantAICreditPackage.credits_remaining > 0,
        )
    )
    return any((p.expires_at is None or p.expires_at > now) for p in q)
