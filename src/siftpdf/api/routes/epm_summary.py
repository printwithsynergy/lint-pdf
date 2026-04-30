"""EPM candidacy summary endpoint.

Surfaces :func:`siftpdf.epm.scoring.score_epm_candidacy` over a job's
fired EPM findings so the dashboard, plugin, and SDK can ask the
engine "is this job EPM-eligible?" without re-implementing the
scoring logic against the raw findings list.

URL: ``GET /api/v1/jobs/{job_id}/epm``

Response shape mirrors :class:`siftpdf.epm.scoring.EpmVerdict` with
the addition of:

* ``job_id`` — echoed for client convenience.
* ``epm_findings_count`` — how many EPM-prefixed inspection IDs the
  scorer ingested. Useful for "did we even check?" sanity.

Response codes:

* ``200 OK`` — verdict rendered (even when tier == REJECT).
* ``404 Not Found`` — job not owned by the authenticated tenant.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from siftpdf.api.auth import get_current_tenant
from siftpdf.api.database import get_db
from siftpdf.api.models import Job, JobFinding, Tenant
from siftpdf.epm.scoring import EpmTier, score_epm_candidacy

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["x:saas-only", "epm"])


class EpmVerdictResponse(BaseModel):
    """Public-facing rendition of an EpmVerdict."""

    job_id: str
    tier: EpmTier
    rejection_drivers: list[str] = Field(default_factory=list)
    advisories: list[str] = Field(default_factory=list)
    recommends_indichrome: bool = False
    legacy_codes_fired: list[str] = Field(default_factory=list)
    epm_findings_count: int = Field(
        ...,
        description=(
            "Number of EPM-prefixed inspection IDs fed into the scorer."
            " A zero count with tier=PASS means no EPM analyzers ran or"
            " the document is too clean to surface anything."
        ),
    )


def _parse_uuid(raw: str, *, kind: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found.",
        ) from exc


def _load_owned_job(db: Session, *, tenant_id: uuid_mod.UUID, job_id: uuid_mod.UUID) -> Job:
    """404 unless the job is non-deleted and owned by the tenant."""
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


@router.get(
    "/{job_id}/epm",
    response_model=EpmVerdictResponse,
)
async def get_epm_verdict(
    job_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> EpmVerdictResponse:
    """Return the EPM candidacy verdict for the job's fired findings."""
    job_uid = _parse_uuid(job_id, kind="Job")
    job = _load_owned_job(db, tenant_id=tenant.id, job_id=job_uid)

    # Pull every EPM-prefixed inspection_id off the job's findings. The
    # scorer dedups internally so we don't have to here; but pulling
    # only EPM rows keeps the query cheap on jobs with thousands of
    # non-EPM findings.
    rows = (
        db.execute(
            select(JobFinding.inspection_id).where(
                JobFinding.job_id == job.id,
                JobFinding.inspection_id.like("LPDF_EPM%"),
            )
        )
        .scalars()
        .all()
    )
    fired_codes = list(rows)

    verdict = score_epm_candidacy(fired_codes)

    return EpmVerdictResponse(
        job_id=str(job.id),
        tier=verdict.tier,
        rejection_drivers=list(verdict.rejection_drivers),
        advisories=list(verdict.advisories),
        recommends_indichrome=verdict.recommends_indichrome,
        legacy_codes_fired=list(verdict.legacy_codes_fired),
        epm_findings_count=len(fired_codes),
    )
