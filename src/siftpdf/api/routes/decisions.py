"""Decisions HTTP routes — Wave V V-05 surface.

Wraps :mod:`siftpdf.decisions.service` so dashboard/SDK/plugin clients
can list, record, and soft-revoke decisions without touching the ORM
directly.

URLs (all tenant-scoped via ``get_current_tenant``):

* ``GET    /api/v1/jobs/{job_id}/decisions`` — list decisions on a job.
* ``POST   /api/v1/jobs/{job_id}/findings/{finding_id}/decisions`` —
  record a finding-level decision.
* ``POST   /api/v1/jobs/{job_id}/decisions`` — record a job-level
  decision (no finding).
* ``POST   /api/v1/jobs/{job_id}/decisions/{decision_id}/revoke`` —
  soft-revoke a previously-recorded decision (Q-2).

Decisions are append-only; the revoke endpoint stamps
``revoked_at`` / ``revoked_by_user_id`` / ``revoked_reason`` rather
than deleting the row, so audit replays stay correct.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import datetime  # noqa: TC003 — pydantic needs it at runtime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from siftpdf.api.auth import get_current_tenant
from siftpdf.api.database import get_db
from siftpdf.api.models import Job, JobFinding, Tenant
from siftpdf.decisions import service as decisions_service

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from siftpdf.decisions.models import Decision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["decisions"])


# ---- response / request schemas -----------------------------------------


class DecisionResponse(BaseModel):
    """Public-facing rendition of a Decision row."""

    id: str
    job_id: str
    finding_id: str | None
    decision_type: str
    decision_value: str | None = None
    decision_metadata: dict[str, Any] | None = None
    notes: str | None = None
    decided_by_user_id: str
    decided_by_email: str | None = None
    decided_at: datetime
    source: str
    request_id: str | None = None
    revoked_at: datetime | None = None
    revoked_by_user_id: str | None = None
    revoked_reason: str | None = None
    is_active: bool


class RecordDecisionRequest(BaseModel):
    """Payload for recording a new decision."""

    decision_type: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="approve | reject | waive | suppress | annotate | escalate",
    )
    decided_by_user_id: str = Field(..., min_length=1, max_length=128)
    source: str = Field(
        ...,
        description=(
            "dashboard | api | plugin | sdk | share_link | "
            "approval_chain | desktop | system | migration"
        ),
    )
    decision_value: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    decided_by_email: str | None = Field(default=None, max_length=255)
    decision_metadata: dict[str, Any] | None = None


class RevokeDecisionRequest(BaseModel):
    """Payload for soft-revoking an existing decision (Q-2)."""

    revoked_by_user_id: str = Field(..., min_length=1, max_length=128)
    revoked_reason: str | None = None


class DecisionListResponse(BaseModel):
    decisions: list[DecisionResponse]
    count: int


# ---- helpers -------------------------------------------------------------


def _parse_uuid(raw: str, *, kind: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found.",
        ) from exc


def _load_owned_job(db: Session, *, tenant_id: uuid_mod.UUID, job_id: uuid_mod.UUID) -> Job:
    from sqlalchemy import select

    row = db.execute(
        select(Job).where(
            Job.id == job_id,
            Job.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return row


def _load_owned_finding(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    job_id: uuid_mod.UUID,
    finding_id: uuid_mod.UUID,
) -> JobFinding:
    from sqlalchemy import select

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


def _to_response(d: Decision) -> DecisionResponse:
    return DecisionResponse(
        id=str(d.id),
        job_id=str(d.job_id),
        finding_id=str(d.finding_id) if d.finding_id else None,
        decision_type=d.decision_type,
        decision_value=d.decision_value,
        decision_metadata=d.decision_metadata,
        notes=d.notes,
        decided_by_user_id=d.decided_by_user_id,
        decided_by_email=d.decided_by_email,
        decided_at=d.decided_at,
        source=d.source,
        request_id=d.request_id,
        revoked_at=d.revoked_at,
        revoked_by_user_id=d.revoked_by_user_id,
        revoked_reason=d.revoked_reason,
        is_active=d.is_active,
    )


def _request_id(request: Request) -> str | None:
    """Pull the X-Request-ID header for audit-row provenance."""
    rid = request.headers.get("x-request-id")
    return rid[:64] if rid else None


# ---- routes --------------------------------------------------------------


@router.get(
    "/{job_id}/decisions",
    response_model=DecisionListResponse,
)
async def list_decisions(
    job_id: str,
    include_revoked: bool = False,
    limit: int = 200,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> DecisionListResponse:
    """List decisions on a job (newest first, active-only by default)."""
    job_uid = _parse_uuid(job_id, kind="Job")
    job = _load_owned_job(db, tenant_id=tenant.id, job_id=job_uid)
    rows = decisions_service.list_for_job(
        db,
        tenant_id=tenant.id,
        job_id=job.id,
        include_revoked=include_revoked,
        limit=max(1, min(limit, 500)),
    )
    return DecisionListResponse(
        decisions=[_to_response(r) for r in rows],
        count=len(rows),
    )


@router.post(
    "/{job_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_job_decision(
    job_id: str,
    payload: RecordDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> DecisionResponse:
    """Record a job-level decision (no finding scope)."""
    job_uid = _parse_uuid(job_id, kind="Job")
    job = _load_owned_job(db, tenant_id=tenant.id, job_id=job_uid)
    try:
        row = decisions_service.record_decision(
            db,
            tenant_id=tenant.id,
            job_id=job.id,
            decision_type=payload.decision_type,
            decided_by_user_id=payload.decided_by_user_id,
            source=payload.source,
            decision_value=payload.decision_value,
            metadata=payload.decision_metadata,
            notes=payload.notes,
            decided_by_email=payload.decided_by_email,
            request_id=_request_id(request),
        )
    except decisions_service.InvalidDecisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.post(
    "/{job_id}/findings/{finding_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_finding_decision(
    job_id: str,
    finding_id: str,
    payload: RecordDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> DecisionResponse:
    """Record a finding-level decision."""
    job_uid = _parse_uuid(job_id, kind="Job")
    finding_uid = _parse_uuid(finding_id, kind="Finding")
    job = _load_owned_job(db, tenant_id=tenant.id, job_id=job_uid)
    finding = _load_owned_finding(db, tenant_id=tenant.id, job_id=job.id, finding_id=finding_uid)
    try:
        row = decisions_service.record_decision(
            db,
            tenant_id=tenant.id,
            job_id=job.id,
            finding_id=finding.id,
            decision_type=payload.decision_type,
            decided_by_user_id=payload.decided_by_user_id,
            source=payload.source,
            decision_value=payload.decision_value,
            metadata=payload.decision_metadata,
            notes=payload.notes,
            decided_by_email=payload.decided_by_email,
            request_id=_request_id(request),
        )
    except decisions_service.InvalidDecisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.post(
    "/{job_id}/decisions/{decision_id}/revoke",
    response_model=DecisionResponse,
)
async def revoke_decision_route(
    job_id: str,
    decision_id: str,
    payload: RevokeDecisionRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> DecisionResponse:
    """Soft-revoke a decision (Q-2). Idempotent: re-revoking is a no-op."""
    job_uid = _parse_uuid(job_id, kind="Job")
    decision_uid = _parse_uuid(decision_id, kind="Decision")
    _load_owned_job(db, tenant_id=tenant.id, job_id=job_uid)
    try:
        row = decisions_service.revoke_decision(
            db,
            tenant_id=tenant.id,
            decision_id=decision_uid,
            revoked_by_user_id=payload.revoked_by_user_id,
            revoked_reason=payload.revoked_reason,
        )
    except decisions_service.InvalidDecisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if row is None or row.job_id != job_uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision not found.",
        )
    db.commit()
    db.refresh(row)
    return _to_response(row)
