"""Q-C4 / Q-C5 — AI-Explain HTTP endpoint.

Returns a 2-3 sentence plain-language explanation for one preflight
finding. Backed by ``lintpdf.ai.explain.explain_finding``: the first
call dispatches Claude Haiku and caches the result on the finding
row; subsequent calls return the cached value so cost stays bounded.

URL: ``POST /api/v1/jobs/{job_id}/findings/{finding_id}/explain``

Response codes:

* ``200 OK`` — explanation rendered (cached or fresh).
* ``402 Payment Required`` — tenant has the cost cap enabled and
  this dispatch would push past the monthly cap.
* ``404 Not Found`` — job or finding doesn't belong to the
  authenticated tenant.
* ``503 Service Unavailable`` — Claude client misconfigured or the
  call failed (transient).
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from lintpdf.ai.cost_cap import CostCapExceededError, remaining_cents
from lintpdf.ai.explain import explain_finding
from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import Job, JobFinding, Tenant

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["ai-explain"])


class ExplanationResponse(BaseModel):
    """Returned by the explain endpoint."""

    finding_id: str
    explanation: str
    model: str
    cached: bool


def _parse_uuid(raw: str, *, kind: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found.",
        ) from exc


def _load_owned_finding(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    job_id: uuid_mod.UUID,
    finding_id: uuid_mod.UUID,
) -> JobFinding:
    """Look up a finding scoped to the tenant's job; 404 otherwise."""
    row = db.execute(
        select(JobFinding)
        .join(Job, Job.id == JobFinding.job_id)
        .where(
            JobFinding.id == finding_id,
            JobFinding.job_id == job_id,
            Job.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found.",
        )
    return row


@router.post(
    "/{job_id}/findings/{finding_id}/explain",
    response_model=ExplanationResponse,
)
async def explain_job_finding(
    job_id: str,
    finding_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ExplanationResponse:
    """Return a cached or freshly-rendered explanation for a finding."""
    job_uid = _parse_uuid(job_id, kind="Job")
    finding_uid = _parse_uuid(finding_id, kind="Finding")
    finding = _load_owned_finding(db, tenant_id=tenant.id, job_id=job_uid, finding_id=finding_uid)

    cached = bool(finding.ai_explanation)
    try:
        text = explain_finding(db, tenant_id=tenant.id, finding=finding)
    except CostCapExceededError as exc:
        # 402 Payment Required is the natural fit for a budget gate.
        # Surface remaining_cents so the dashboard can render a hint.
        remaining = remaining_cents(db, tenant.id)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "cost_cap_exceeded",
                "message": ("Tenant LLM cost cap reached for the current month."),
                "cap_cents": exc.cap_cents,
                "used_cents": exc.used_cents,
                "remaining_cents": max(0, remaining or 0),
            },
        ) from exc

    if not text:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Explanation service is unavailable. The Claude client may"
                " be unconfigured or the call failed transiently — retry"
                " in a few seconds."
            ),
        )

    return ExplanationResponse(
        finding_id=str(finding.id),
        explanation=text,
        model=finding.ai_explanation_model or "",
        cached=cached,
    )
