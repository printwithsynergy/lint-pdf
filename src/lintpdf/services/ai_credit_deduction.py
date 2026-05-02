"""``AICreditDeductionService`` — post-call credit deduction + ledger write (W6c-2e).

Used by ``lintpdf.ai.credits.deduct_credits`` to drain the tenant's
credit-package allotment, charge overage at the configured rate, and
write the per-call ``AIUsageLog`` row. Also fires billing-threshold
webhooks ("low" / "exhausted") when a deduction crosses the line.

OSS engine ships a pure no-op default (no AI billing concept on
OSS-only deploys). Hosted SaaS overrides via
``set_ai_credit_deduction_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AICreditDeductionService(Protocol):
    """Drain credits + write ``AIUsageLog`` after a successful AI call."""

    def deduct_credits(
        self,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        category: str,
        feature: str,
        credit_amount: int,
        processing_time_ms: int,
        result_summary: dict[str, Any] | None,
        db: Session,
    ) -> None:
        """Apply the deduction. Best-effort — never raises."""
        ...


class DefaultAICreditDeductionService:
    """Pure no-op default. OSS engine has no AI billing concept."""

    def deduct_credits(
        self,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        category: str,
        feature: str,
        credit_amount: int,
        processing_time_ms: int,
        result_summary: dict[str, Any] | None,
        db: Session,
    ) -> None:
        return None


_service: AICreditDeductionService | None = None


def get_ai_credit_deduction_service() -> AICreditDeductionService:
    global _service
    if _service is None:
        _service = DefaultAICreditDeductionService()
    return _service


def set_ai_credit_deduction_service(service: AICreditDeductionService | None) -> None:
    global _service
    _service = service
