"""Phase 0.7 PR-A — workflow CRUD + workflow-scoped override endpoints.

Sibling to ``toggles.py``. Splits cleanly because:

* ``toggles.py`` owns the registry + the TENANT scope (the easy case
  where ``scope_id`` is just the tenant uuid).
* ``workflows.py`` owns the WORKFLOW scope which needs a parent
  ``Workflow`` row — every override path here validates the workflow
  exists and belongs to the requesting tenant.

Endpoints:

* ``GET    /api/v1/workflows`` — list this tenant's workflows
* ``POST   /api/v1/workflows`` — create a workflow
* ``GET    /api/v1/workflows/{id}`` — single workflow
* ``PATCH  /api/v1/workflows/{id}`` — update mutable fields
* ``DELETE /api/v1/workflows/{id}`` — soft delete (``is_active = false``)
* ``GET    /api/v1/workflows/{id}/toggles`` — list workflow-scope overrides
* ``PUT    /api/v1/workflows/{id}/toggles/{toggle_id}`` — set workflow-scope override
* ``DELETE /api/v1/workflows/{id}/toggles/{toggle_id}`` — remove workflow-scope override

The CALL scope is NOT exposed here — call overrides are passed
in-request via ``JobCreate.overrides`` (DQ-A3 in-request only) and
their durable record is the ``resolved_config_snapshots`` row, not a
``toggle_overrides`` row.
"""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.tenants import toggle_audit
from lintpdf.tenants.config_resolver import ConfigResolver
from lintpdf.tenants.toggle_models import (
    Toggle,
    ToggleOverride,
    ToggleScope,
    Workflow,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["workflows"])


# ---- response / request schemas -----------------------------------------


class WorkflowResponse(BaseModel):
    id: str
    tenant_id: str
    slug: str
    human_name: str
    description: str | None
    is_default: bool
    is_active: bool
    response_mode: str
    server_revision: int
    created_by_user_id: str | None
    created_at: str
    updated_at: str


class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    total: int


class WorkflowCreateRequest(BaseModel):
    slug: str = Field(..., min_length=1, max_length=128)
    human_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10_000)
    is_default: bool = False
    response_mode: str = Field("async", pattern="^(async|sync)$")


class WorkflowUpdateRequest(BaseModel):
    human_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10_000)
    is_default: bool | None = None
    is_active: bool | None = None
    response_mode: str | None = Field(None, pattern="^(async|sync)$")


class WorkflowOverrideRequest(BaseModel):
    value: Any


class WorkflowOverrideResponse(BaseModel):
    workflow_id: str
    toggle_id: str
    value: Any


class WorkflowOverrideListResponse(BaseModel):
    items: list[WorkflowOverrideResponse]
    total: int


# ---- helpers ------------------------------------------------------------


def _to_response(wf: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=wf.id,
        tenant_id=str(wf.tenant_id),
        slug=wf.slug,
        human_name=wf.human_name,
        description=wf.description,
        is_default=wf.is_default,
        is_active=wf.is_active,
        response_mode=wf.response_mode,
        server_revision=wf.server_revision,
        created_by_user_id=wf.created_by_user_id,
        created_at=wf.created_at.isoformat() if wf.created_at else "",
        updated_at=wf.updated_at.isoformat() if wf.updated_at else "",
    )


def _load_workflow(db: Session, workflow_id: str, tenant_id: Any) -> Workflow:
    """Load a workflow row, 404 if missing, 403 if cross-tenant."""
    wf = db.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"unknown workflow {workflow_id!r}",
        )
    if wf.tenant_id != tenant_id:
        # Don't leak existence — return 404 not 403.
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"unknown workflow {workflow_id!r}",
        )
    return wf


def _clear_other_defaults(db: Session, tenant_id: Any, keep_id: str) -> None:
    """Make sure at most one is_default workflow exists per tenant."""
    db.execute(
        select(Workflow)
        .where(
            Workflow.tenant_id == tenant_id,
            Workflow.is_default.is_(True),
            Workflow.id != keep_id,
        )
        .execution_options(synchronize_session=False)
    )
    rows = (
        db.execute(
            select(Workflow).where(
                Workflow.tenant_id == tenant_id,
                Workflow.is_default.is_(True),
                Workflow.id != keep_id,
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.is_default = False


# ---- workflow CRUD ------------------------------------------------------


@router.get("/workflows", response_model=WorkflowListResponse)
def list_workflows(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WorkflowListResponse:
    stmt = select(Workflow).where(Workflow.tenant_id == tenant.id)
    if not include_inactive:
        stmt = stmt.where(Workflow.is_active.is_(True))
    rows = db.execute(stmt.order_by(Workflow.created_at)).scalars().all()
    items = [_to_response(wf) for wf in rows]
    return WorkflowListResponse(items=items, total=len(items))


@router.post(
    "/workflows",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow(
    body: WorkflowCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WorkflowResponse:
    # Slug uniqueness inside the tenant's workflows
    existing_slug = (
        db.execute(
            select(Workflow).where(
                Workflow.tenant_id == tenant.id,
                Workflow.slug == body.slug,
            )
        )
        .scalars()
        .first()
    )
    if existing_slug is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"workflow slug {body.slug!r} already exists for this tenant",
        )

    wf = Workflow(
        id=secrets.token_urlsafe(16),
        tenant_id=tenant.id,
        slug=body.slug,
        human_name=body.human_name,
        description=body.description,
        is_default=body.is_default,
        is_active=True,
        response_mode=body.response_mode,
        server_revision=1,
    )
    db.add(wf)
    if body.is_default:
        _clear_other_defaults(db, tenant.id, wf.id)
    db.commit()
    db.refresh(wf)
    return _to_response(wf)


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WorkflowResponse:
    return _to_response(_load_workflow(db, workflow_id, tenant.id))


@router.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: str,
    body: WorkflowUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WorkflowResponse:
    wf = _load_workflow(db, workflow_id, tenant.id)
    if body.human_name is not None:
        wf.human_name = body.human_name
    if body.description is not None:
        wf.description = body.description
    if body.response_mode is not None:
        wf.response_mode = body.response_mode
    if body.is_active is not None:
        wf.is_active = body.is_active
    if body.is_default is not None:
        wf.is_default = body.is_default
        if body.is_default:
            _clear_other_defaults(db, tenant.id, wf.id)
    wf.server_revision = (wf.server_revision or 0) + 1
    db.commit()
    db.refresh(wf)
    return _to_response(wf)


@router.delete(
    "/workflows/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Soft-delete a workflow. Snapshot history stays intact."""
    wf = _load_workflow(db, workflow_id, tenant.id)
    wf.is_active = False
    wf.is_default = False
    wf.server_revision = (wf.server_revision or 0) + 1
    db.commit()


# ---- workflow-scope override CRUD ---------------------------------------


@router.get(
    "/workflows/{workflow_id}/toggles",
    response_model=WorkflowOverrideListResponse,
)
def list_workflow_overrides(
    workflow_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WorkflowOverrideListResponse:
    wf = _load_workflow(db, workflow_id, tenant.id)
    rows = (
        db.execute(
            select(ToggleOverride).where(
                ToggleOverride.scope == ToggleScope.WORKFLOW,
                ToggleOverride.scope_id == wf.id,
            )
        )
        .scalars()
        .all()
    )
    items = [
        WorkflowOverrideResponse(
            workflow_id=wf.id,
            toggle_id=row.toggle_id,
            value=row.value,
        )
        for row in rows
    ]
    return WorkflowOverrideListResponse(items=items, total=len(items))


@router.put(
    "/workflows/{workflow_id}/toggles/{toggle_id:path}",
    status_code=status.HTTP_200_OK,
    response_model=WorkflowOverrideResponse,
)
def set_workflow_override(
    workflow_id: str,
    toggle_id: str,
    body: WorkflowOverrideRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WorkflowOverrideResponse:
    wf = _load_workflow(db, workflow_id, tenant.id)

    t = db.get(Toggle, toggle_id)
    if t is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"unknown toggle {toggle_id!r}",
        )
    if ToggleScope.WORKFLOW not in (t.override_at or []):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"toggle {toggle_id!r} cannot be overridden at WORKFLOW scope",
        )

    existing = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == toggle_id,
            ToggleOverride.scope == ToggleScope.WORKFLOW,
            ToggleOverride.scope_id == wf.id,
        )
    ).scalar_one_or_none()

    if existing is not None:
        toggle_audit.record(
            db,
            tenant_id=tenant.id,
            toggle_id=toggle_id,
            scope=ToggleScope.WORKFLOW,
            scope_id=wf.id,
            action=toggle_audit.UPDATE,
            before=existing,
            after_value=body.value,
            after_locked=False,
            actor="api",
            surface="api",
        )
        existing.value = body.value
        existing.set_by = "api"
    else:
        db.add(
            ToggleOverride(
                id=secrets.token_urlsafe(12),
                toggle_id=toggle_id,
                scope=ToggleScope.WORKFLOW,
                scope_id=wf.id,
                value=body.value,
                locked=False,
                set_by="api",
                surface="api",
            )
        )
        toggle_audit.record(
            db,
            tenant_id=tenant.id,
            toggle_id=toggle_id,
            scope=ToggleScope.WORKFLOW,
            scope_id=wf.id,
            action=toggle_audit.CREATE,
            before=None,
            after_value=body.value,
            after_locked=False,
            actor="api",
            surface="api",
        )

    wf.server_revision = (wf.server_revision or 0) + 1
    db.commit()
    ConfigResolver(db).invalidate(tenant_id=tenant.id, workflow_id=wf.id)
    return WorkflowOverrideResponse(
        workflow_id=wf.id,
        toggle_id=toggle_id,
        value=body.value,
    )


@router.delete(
    "/workflows/{workflow_id}/toggles/{toggle_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workflow_override(
    workflow_id: str,
    toggle_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    wf = _load_workflow(db, workflow_id, tenant.id)
    existing = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == toggle_id,
            ToggleOverride.scope == ToggleScope.WORKFLOW,
            ToggleOverride.scope_id == wf.id,
        )
    ).scalar_one_or_none()
    if existing is None:
        return
    toggle_audit.record(
        db,
        tenant_id=tenant.id,
        toggle_id=toggle_id,
        scope=ToggleScope.WORKFLOW,
        scope_id=wf.id,
        action=toggle_audit.DELETE,
        before=existing,
        after_value=None,
        after_locked=None,
        actor="api",
        surface="api",
    )
    db.delete(existing)
    wf.server_revision = (wf.server_revision or 0) + 1
    db.commit()
    ConfigResolver(db).invalidate(tenant_id=tenant.id, workflow_id=wf.id)
