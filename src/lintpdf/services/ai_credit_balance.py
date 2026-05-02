"""``AICreditBalanceService`` — current AI credit + spend snapshot (W6c-2c).

Used by ``lintpdf.ai.credits.get_credit_balance`` to render the
billing dashboard (credit packages, monthly spend, spending limit).
SaaS-only ``TenantAIConfig`` / ``TenantAICreditPackage`` /
``AIUsageLog`` tables; OSS default returns a zeroed ``pay_per_use``
balance so OSS-only deploys render the dashboard as "no AI billing
configured" rather than crashing on a missing model.

Hosted SaaS overrides via ``set_ai_credit_balance_service`` at boot.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreditBalance:
    """Snapshot of a tenant's AI credit + spend state."""

    credit_balance: Decimal
    billing_mode: str
    packages_active: int
    package_credits_remaining: int
    monthly_spent: Decimal
    monthly_spending_limit: Decimal | None


class AICreditBalanceService(Protocol):
    """Look up the current AI credit balance for a tenant."""

    def get_credit_balance(self, tenant_id: uuid.UUID, db: Session) -> CreditBalance:
        """Return the tenant's current credit balance + monthly spend."""
        ...


class DefaultAICreditBalanceService:
    """Pure no-op default. OSS engine has no AI billing concept."""

    def get_credit_balance(self, tenant_id: uuid.UUID, db: Session) -> CreditBalance:
        return CreditBalance(
            credit_balance=Decimal("0"),
            billing_mode="pay_per_use",
            packages_active=0,
            package_credits_remaining=0,
            monthly_spent=Decimal("0"),
            monthly_spending_limit=None,
        )


_service: AICreditBalanceService | None = None


def get_ai_credit_balance_service() -> AICreditBalanceService:
    global _service
    if _service is None:
        _service = DefaultAICreditBalanceService()
    return _service


def set_ai_credit_balance_service(service: AICreditBalanceService | None) -> None:
    global _service
    _service = service
