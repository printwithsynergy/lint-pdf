"""``AIUsageRecorderService`` — best-effort AI cost-cents bookkeeping (W6c-2b).

Used by ``lintpdf.ai.explain._record_usage_inline`` to write a row
into the metering ledger after every Claude dispatch. SaaS-only
``AIUsageLog`` table; OSS default is a pure no-op (no AI billing
concept on OSS-only deploys, so nothing to record).

Hosted SaaS overrides via ``set_ai_usage_recorder_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AIUsageRecorderService(Protocol):
    """Persist a per-call AI usage row into the metering ledger."""

    def record_usage(
        self,
        db: Session,
        *,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID | None,
        model: str,
        usage: object,
        category: str = "explain",
        feature: str = "explain",
    ) -> None:
        """Best-effort write. Must never raise — errors are logged."""
        ...


class DefaultAIUsageRecorderService:
    """Pure no-op default. OSS engine has no AI billing ledger."""

    def record_usage(
        self,
        db: Session,
        *,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID | None,
        model: str,
        usage: object,
        category: str = "explain",
        feature: str = "explain",
    ) -> None:
        return None


_service: AIUsageRecorderService | None = None


def get_ai_usage_recorder_service() -> AIUsageRecorderService:
    global _service
    if _service is None:
        _service = DefaultAIUsageRecorderService()
    return _service


def set_ai_usage_recorder_service(service: AIUsageRecorderService | None) -> None:
    global _service
    _service = service
