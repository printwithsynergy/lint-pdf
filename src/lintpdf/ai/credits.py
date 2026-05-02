"""AI credit metering — deduction, balance, and spending limit enforcement."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lintpdf.services.ai_credit_balance import (
    CreditBalance,
    get_ai_credit_balance_service,
)
from lintpdf.services.ai_credit_check import get_ai_credit_check_service
from lintpdf.services.ai_credit_deduction import get_ai_credit_deduction_service

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

    Dispatches to the registered :class:`AICreditDeductionService`. The
    OSS engine ships a pure no-op default (no AI billing concept on
    OSS-only deploys); ``lintpdf_saas`` installs an implementation
    that drains ``TenantAICreditPackage`` rows, computes overage at
    the configured rate, writes the ``AIUsageLog`` row, and fires
    billing-threshold webhooks ("low" / "exhausted").
    """
    get_ai_credit_deduction_service().deduct_credits(
        tenant_id,
        job_id,
        category,
        feature,
        credit_amount,
        processing_time_ms,
        result_summary,
        db,
    )
