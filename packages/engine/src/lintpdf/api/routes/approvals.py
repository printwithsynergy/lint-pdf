"""API endpoints for approval chain templates and chains."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import (
    ApprovalChain,
    ApprovalChainTemplate,
    ApprovalStep,
    Job,
    JobStatus,
    Tenant,
)
from lintpdf.approvals import service as approval_service
from lintpdf.approvals.schemas import (
    AttachChainRequest,
    ChainResponse,
    DecideRequest,
    StepConfig,
    TemplateCreateRequest,
    TemplateResponse,
    TemplateUpdateRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["approvals"])


def _check_approval_entitlement(tenant: Tenant) -> None:
    """Raise 403 if the tenant's plan does not include approval chains."""
    from lintpdf.tenants.entitlements import resolve_entitlements

    ent = resolve_entitlements(tenant)
    if not getattr(ent, "approval_chains_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approval chains require a Growth, Scale, or Enterprise plan.",
        )


def _template_to_response(t: ApprovalChainTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=str(t.id),
        tenant_id=str(t.tenant_id),
        name=t.name,
        description=t.description,
        is_default=t.is_default,
        steps=t.steps,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _chain_to_response(db: Session, chain: ApprovalChain) -> ChainResponse:
    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.chain_id == chain.id)
        .order_by(ApprovalStep.step_index, ApprovalStep.created_at)
        .all()
    )
    return ChainResponse(
        id=str(chain.id),
        job_id=str(chain.job_id),
        template_id=str(chain.template_id) if chain.template_id else None,
        status=chain.status,
        current_step=chain.current_step,
        steps=chain.steps,
        step_history=[
            {
                "id": str(s.id),
                "step_index": s.step_index,
                "step_name": s.step_name,
                "approver_email": s.approver_email,
                "decision": s.decision,
                "notes": s.notes,
                "decided_at": s.decided_at,
            }
            for s in steps
        ],
        created_at=chain.created_at,
        completed_at=chain.completed_at,
    )


# ── Template CRUD ──


@router.get("/approval-templates", response_model=list[TemplateResponse])
async def list_templates(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> list[TemplateResponse]:
    _check_approval_entitlement(tenant)
    templates = (
        db.query(ApprovalChainTemplate)
        .filter(ApprovalChainTemplate.tenant_id == tenant.id)
        .order_by(ApprovalChainTemplate.created_at.desc())
        .all()
    )
    return [_template_to_response(t) for t in templates]


@router.post("/approval-templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    _check_approval_entitlement(tenant)

    # Check template count limit from entitlements
    from lintpdf.tenants.entitlements import resolve_entitlements

    ent = resolve_entitlements(tenant)
    max_templates = getattr(ent, "max_approval_templates", None)
    if max_templates is not None:
        existing = (
            db.query(ApprovalChainTemplate)
            .filter(ApprovalChainTemplate.tenant_id == tenant.id)
            .count()
        )
        if existing >= max_templates:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your plan allows a maximum of {max_templates} approval templates.",
            )

    # If setting as default, unset previous default
    if body.is_default:
        db.query(ApprovalChainTemplate).filter(
            ApprovalChainTemplate.tenant_id == tenant.id,
            ApprovalChainTemplate.is_default.is_(True),
        ).update({"is_default": False}, synchronize_session=False)

    template = ApprovalChainTemplate(
        id=uuid4(),
        tenant_id=tenant.id,
        name=body.name,
        description=body.description,
        is_default=body.is_default,
        steps=[s.model_dump() for s in body.steps],
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_to_response(template)


@router.patch("/approval-templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    _check_approval_entitlement(tenant)

    try:
        tid = UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found.") from None

    template = (
        db.query(ApprovalChainTemplate)
        .filter(
            ApprovalChainTemplate.id == tid,
            ApprovalChainTemplate.tenant_id == tenant.id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")

    if body.name is not None:
        template.name = body.name
    if body.description is not None:
        template.description = body.description
    if body.is_default is not None:
        if body.is_default:
            db.query(ApprovalChainTemplate).filter(
                ApprovalChainTemplate.tenant_id == tenant.id,
                ApprovalChainTemplate.id != tid,
                ApprovalChainTemplate.is_default.is_(True),
            ).update({"is_default": False}, synchronize_session=False)
        template.is_default = body.is_default
    if body.steps is not None:
        template.steps = [s.model_dump() for s in body.steps]

    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)
    return _template_to_response(template)


@router.delete("/approval-templates/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> None:
    _check_approval_entitlement(tenant)
    try:
        tid = UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Template not found.") from None
    template = (
        db.query(ApprovalChainTemplate)
        .filter(
            ApprovalChainTemplate.id == tid,
            ApprovalChainTemplate.tenant_id == tenant.id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")
    db.delete(template)
    db.commit()


# ── Chain attach/get/cancel (tenant-authenticated) ──


@router.post("/jobs/{job_id}/approval-chain", response_model=ChainResponse, status_code=201)
async def attach_chain(
    job_id: str,
    body: AttachChainRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> ChainResponse:
    _check_approval_entitlement(tenant)

    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found.") from None

    job = db.query(Job).filter(Job.id == jid, Job.tenant_id == tenant.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=409, detail="Job must be complete to attach an approval chain."
        )

    # Check no existing chain
    existing = db.query(ApprovalChain).filter(ApprovalChain.job_id == job.id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An approval chain is already attached to this job.",
        )

    # Resolve steps from template or ad-hoc
    if body.template_id:
        try:
            tid = UUID(body.template_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Template not found.") from None
        template = (
            db.query(ApprovalChainTemplate)
            .filter(
                ApprovalChainTemplate.id == tid,
                ApprovalChainTemplate.tenant_id == tenant.id,
            )
            .first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found.")
        steps = template.steps
        template_uuid = template.id
    elif body.steps:
        # Validate ad-hoc steps
        validated = [
            StepConfig(**s.model_dump()) if isinstance(s, StepConfig) else StepConfig(**s)
            for s in body.steps
        ]
        steps = [s.model_dump() for s in validated]
        template_uuid = None
    else:
        raise HTTPException(status_code=400, detail="Either template_id or steps is required.")

    chain = approval_service.create_chain(
        db=db, job=job, tenant=tenant, steps=steps, template_id=template_uuid
    )
    return _chain_to_response(db, chain)


@router.get("/jobs/{job_id}/approval-chain", response_model=ChainResponse)
async def get_chain(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> ChainResponse:
    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Chain not found.") from None
    chain = (
        db.query(ApprovalChain)
        .filter(ApprovalChain.job_id == jid, ApprovalChain.tenant_id == tenant.id)
        .first()
    )
    if not chain:
        raise HTTPException(status_code=404, detail="No approval chain for this job.")
    return _chain_to_response(db, chain)


@router.post("/jobs/{job_id}/approval-chain/cancel", status_code=200)
async def cancel_chain_endpoint(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        jid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Chain not found.") from None
    chain = (
        db.query(ApprovalChain)
        .filter(ApprovalChain.job_id == jid, ApprovalChain.tenant_id == tenant.id)
        .first()
    )
    if not chain:
        raise HTTPException(status_code=404, detail="No approval chain for this job.")
    if chain.status != "pending":
        raise HTTPException(status_code=409, detail=f"Chain is already {chain.status}.")
    approval_service.cancel_chain(db=db, chain=chain, tenant=tenant)
    return {"status": "cancelled"}


# ── Public approver endpoints (access_token auth) ──


class PublicChainResponse(BaseModel):
    id: str
    job_id: str
    status: str
    current_step: int
    total_steps: int
    current_step_name: str | None
    completed_steps: list[dict]
    file_name: str
    health_summary: dict


@router.get("/approvals/info/{access_token}", response_model=PublicChainResponse)
async def public_chain_info(
    access_token: str,
    db: Session = Depends(get_db),
) -> PublicChainResponse:
    """Public info endpoint for the approver landing page."""
    step = db.query(ApprovalStep).filter(ApprovalStep.access_token == access_token).first()
    if not step:
        raise HTTPException(status_code=404, detail="Approval link not found.")

    chain = db.query(ApprovalChain).filter(ApprovalChain.id == step.chain_id).first()
    if not chain:
        raise HTTPException(status_code=404, detail="Approval chain not found.")

    job = db.query(Job).filter(Job.id == chain.job_id).first()

    # Get completed step decisions for context
    all_steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.chain_id == chain.id)
        .order_by(ApprovalStep.step_index, ApprovalStep.created_at)
        .all()
    )
    completed = [
        {
            "step_index": s.step_index,
            "step_name": s.step_name,
            "approver_email": s.approver_email,
            "decision": s.decision,
            "notes": s.notes,
            "decided_at": s.decided_at.isoformat() if s.decided_at else None,
        }
        for s in all_steps
        if s.decision != "pending"
    ]

    current_name = None
    if chain.current_step < len(chain.steps):
        current_name = chain.steps[chain.current_step].get("name")

    summary = (job.result_json or {}).get("summary", {}) if job else {}
    health_summary = {
        "total_findings": summary.get("total_findings", 0),
        "error_count": summary.get("error_count", 0),
        "warning_count": summary.get("warning_count", 0),
        "advisory_count": summary.get("advisory_count", 0),
        "passed": summary.get("passed", True),
        "page_count": summary.get("page_count", 0),
    }

    return PublicChainResponse(
        id=str(chain.id),
        job_id=str(chain.job_id),
        status=chain.status,
        current_step=chain.current_step,
        total_steps=len(chain.steps),
        current_step_name=current_name,
        completed_steps=completed,
        file_name=job.file_name if job else "",
        health_summary=health_summary,
    )


@router.post("/approvals/decide/{access_token}")
async def public_decide(
    access_token: str,
    body: DecideRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = approval_service.decide_step(
        db=db,
        access_token=access_token,
        decision=body.decision,
        notes=body.notes,
    )
    if "error" in result:
        raise HTTPException(status_code=result.get("status", 400), detail=result["error"])
    return result


# ── Public chain state for viewer ──


@router.get("/viewer/public/{token}/approval-chain")
async def public_viewer_chain(
    token: str,
    db: Session = Depends(get_db),
) -> dict[str, Any] | None:
    """Return the chain attached to the job (if any) identified by report token."""
    from lintpdf.api.models import ReportToken

    record = db.query(ReportToken).filter(ReportToken.token == token).first()
    if not record:
        raise HTTPException(status_code=404, detail="Token not found.")

    chain = db.query(ApprovalChain).filter(ApprovalChain.job_id == record.job_id).first()
    if not chain:
        return None

    all_steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.chain_id == chain.id)
        .order_by(ApprovalStep.step_index, ApprovalStep.created_at)
        .all()
    )
    return {
        "id": str(chain.id),
        "status": chain.status,
        "current_step": chain.current_step,
        "steps": chain.steps,
        "step_history": [
            {
                "step_index": s.step_index,
                "step_name": s.step_name,
                "approver_email": s.approver_email,
                "decision": s.decision,
                "notes": s.notes,
                "decided_at": s.decided_at.isoformat() if s.decided_at else None,
            }
            for s in all_steps
        ],
        "created_at": chain.created_at.isoformat(),
        "completed_at": chain.completed_at.isoformat() if chain.completed_at else None,
    }
