"""AI credit metering — deduction, balance, and spending limit enforcement."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from lintpdf.services.ai_credit_balance import (
    CreditBalance,
    get_ai_credit_balance_service,
)
from lintpdf.services.ai_credit_check import get_ai_credit_check_service

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_credit_balance(tenant_id: uuid.UUID, db: Session) -> CreditBalance:
    """Get current AI credit balance and usage summary.

    Dispatches to the registered :class:`AICreditBalanceService`. The
    OSS engine ships a no-op default that returns a zeroed
    ``pay_per_use`` balance (no AI billing concept on OSS-only
    deploys); ``lintpdf_saas`` installs an implementation backed by
    ``TenantAIConfig`` / ``TenantAICreditPackage`` / ``AIUsageLog`` at
    boot via ``set_ai_credit_balance_service``.
    """
    return get_ai_credit_balance_service().get_credit_balance(tenant_id, db)


def check_ai_credits(
    tenant_id: uuid.UUID,
    credits_needed: int,
    db: Session,
) -> None:
    """Verify tenant has sufficient credits. Raises 402 if not.

    Dispatches to the registered :class:`AICreditCheckService`. The
    OSS engine ships a no-op default (no AI billing concept on
    OSS-only deploys); ``lintpdf_saas`` installs an implementation
    backed by ``TenantAIConfig`` + the credit balance for full
    pay-per-use vs credit-package gate logic.
    """
    get_ai_credit_check_service().check_credits(tenant_id, credits_needed, db)


def deduct_credits(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    category: str,
    feature: str,
    credit_amount: int,
    processing_time_ms: int,
    result_summary: dict[str, Any] | None,
    db: Session,
) -> None:
    """Deduct AI credits after successful analysis and log usage.

    For credit_package billing: deducts from oldest non-expired package first.
    For pay_per_use billing: logs cost at overage rate.
    """
    from lintpdf.api.models import (
        AIBillingMode,
        AIUsageLog,
        TenantAIConfig,
        TenantAICreditPackage,
    )

    config = db.query(TenantAIConfig).filter(TenantAIConfig.tenant_id == tenant_id).first()

    if config is None:
        logger.warning("No AI config for tenant %s during credit deduction", tenant_id)
        return

    cost = Decimal("0")

    if config.billing_mode == AIBillingMode.CREDIT_PACKAGE:
        # Deduct from oldest non-expired package first
        now = datetime.now(timezone.utc)
        packages = (
            db.query(TenantAICreditPackage)
            .filter(
                TenantAICreditPackage.tenant_id == tenant_id,
                TenantAICreditPackage.kind == "credits",
                TenantAICreditPackage.credits_remaining > 0,
            )
            .order_by(TenantAICreditPackage.purchased_at.asc())
            .all()
        )

        remaining = credit_amount
        for pkg in packages:
            if pkg.expires_at and pkg.expires_at <= now:
                continue
            if remaining <= 0:
                break
            deduct = min(remaining, pkg.credits_remaining)
            pkg.credits_remaining -= deduct
            remaining -= deduct

        if remaining > 0:
            # Overage — charge at overage rate
            cost = Decimal(str(remaining)) * Decimal(str(config.overage_rate))
    else:
        # Pay-per-use: charge at overage rate
        cost = Decimal(str(credit_amount)) * Decimal(str(config.overage_rate))

    # Log usage
    db.add(
        AIUsageLog(
            tenant_id=tenant_id,
            job_id=job_id,
            category=category,
            feature=feature,
            credits_consumed=credit_amount,
            cost=cost,
            processing_time_ms=processing_time_ms,
            result_summary=result_summary,
        )
    )

    db.flush()

    # Webhook threshold checks. Only meaningful in credit_package mode
    # (pay_per_use has no pool to exhaust). Compares balance before vs
    # after the deduct so a single crossing of the 10% line fires once,
    # not every subsequent deduction while already-low.
    if config.billing_mode == AIBillingMode.CREDIT_PACKAGE:
        try:
            post_balance = get_credit_balance(tenant_id, db)
            current_total = float(post_balance.package_credits_remaining)
            before_total = current_total + float(credit_amount)
            if current_total <= 0 < before_total:
                from lintpdf.webhooks.events import fire_billing_threshold

                fire_billing_threshold(
                    db,
                    tenant_id,
                    resource="ai_credits",
                    severity="exhausted",
                    remaining=0,
                )
                db.flush()
            elif before_total > 0:
                # Low threshold: 10% of pre-deduction balance.
                if before_total > 0 and current_total / before_total <= 0.10 < 1.0:
                    # Only fire "low" when we actually crossed the line
                    # on this deduction, not when we're already below.
                    prev_pct = 1.0  # before_total / before_total
                    curr_pct = current_total / before_total
                    if prev_pct > 0.10 >= curr_pct:
                        from lintpdf.webhooks.events import fire_billing_threshold

                        fire_billing_threshold(
                            db,
                            tenant_id,
                            resource="ai_credits",
                            severity="low",
                            remaining=current_total,
                            allotment=before_total,
                        )
                        db.flush()
        except Exception:
            logger.exception("ai_credits threshold webhook check failed")
