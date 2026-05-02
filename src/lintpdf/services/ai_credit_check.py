"""``AICreditCheckService`` — pre-call credit balance gate (W6c-2d).

Used by ``lintpdf.ai.credits.check_ai_credits`` to verify the tenant
has sufficient credits / monthly spend headroom before dispatching an
AI call. SaaS-only ``TenantAIConfig`` + balance read; OSS default is
a pure no-op (no AI billing concept on OSS-only deploys, so the gate
trivially passes).

Hosted SaaS overrides via ``set_ai_credit_check_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AICreditCheckService(Protocol):
    """Verify a tenant can spend ``credits_needed`` more AI credits."""

    def check_credits(
        self,
        tenant_id: uuid.UUID,
        credits_needed: int,
        db: Session,
    ) -> None:
        """Raise ``HTTPException(402)`` when the tenant lacks headroom."""
        ...


class DefaultAICreditCheckService:
    """Pure no-op default. OSS engine has no AI billing concept."""

    def check_credits(
        self,
        tenant_id: uuid.UUID,
        credits_needed: int,
        db: Session,
    ) -> None:
        return None


_service: AICreditCheckService | None = None


def get_ai_credit_check_service() -> AICreditCheckService:
    global _service
    if _service is None:
        _service = DefaultAICreditCheckService()
    return _service


def set_ai_credit_check_service(service: AICreditCheckService | None) -> None:
    global _service
    _service = service
