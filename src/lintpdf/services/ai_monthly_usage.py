"""``AIMonthlyUsageService`` — current-month AI spend lookup (W6c-2a).

Used by ``lintpdf.ai.cost_cap.monthly_usage_cents`` to gate the
per-tenant LLM cost cap. SaaS-only ``AIUsageLog`` table; OSS default
is a pure no-op returning ``0`` (cap never trips on OSS-only deploys
because there's no AI billing concept).

Hosted SaaS overrides via ``set_ai_monthly_usage_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AIMonthlyUsageService(Protocol):
    """Sum the tenant's AI spend for the current calendar month."""

    def monthly_usage_cents(
        self,
        tenant_id: uuid.UUID,
        db: Session,
        *,
        now: datetime | None = None,
    ) -> int:
        """Return integer cents spent this month. Soft-fails to ``0``."""
        ...


class DefaultAIMonthlyUsageService:
    """Pure no-op default. OSS engine has no AI billing."""

    def monthly_usage_cents(
        self,
        tenant_id: uuid.UUID,  # noqa: ARG002
        db: Session,  # noqa: ARG002
        *,
        now: datetime | None = None,  # noqa: ARG002
    ) -> int:
        return 0


_service: AIMonthlyUsageService | None = None


def get_ai_monthly_usage_service() -> AIMonthlyUsageService:
    global _service
    if _service is None:
        _service = DefaultAIMonthlyUsageService()
    return _service


def set_ai_monthly_usage_service(service: AIMonthlyUsageService | None) -> None:
    global _service
    _service = service
