"""``ApprovalsService`` — approval-chain lookup for ``/jobs/{id}/state`` (W6c-5).

Used by ``lintpdf.api.routes.jobs.get_job_state`` to populate the
optional ``approval_chain`` section of the job-state aggregate
response. SaaS-only feature backed by ``ApprovalChain`` /
``ApprovalStep`` tables; OSS default returns ``None`` so the
``approval_chain`` field stays ``null`` on OSS-only deploys.

Hosted SaaS overrides via ``set_approvals_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.orm import Session

    from lintpdf.api.schemas import JobStateApprovalChain

logger = logging.getLogger(__name__)


class ApprovalsService(Protocol):
    """Look up the approval chain state for a job."""

    def get_approval_chain_state(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: Session,
    ) -> JobStateApprovalChain | None:
        """Return the assembled response shape, or ``None`` when no chain exists."""
        ...


class DefaultApprovalsService:
    """Pure no-op default. OSS engine has no approval workflow concept."""

    def get_approval_chain_state(
        self,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        db: Session,
    ) -> JobStateApprovalChain | None:
        return None


_service: ApprovalsService | None = None


def get_approvals_service() -> ApprovalsService:
    global _service
    if _service is None:
        _service = DefaultApprovalsService()
    return _service


def set_approvals_service(service: ApprovalsService | None) -> None:
    global _service
    _service = service
