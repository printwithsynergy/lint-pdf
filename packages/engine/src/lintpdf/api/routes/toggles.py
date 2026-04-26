"""Wave V V-07 — toggle registry + tenant override endpoints.

* ``GET    /api/v1/toggles`` — list registry rows (filter by category)
* ``GET    /api/v1/toggles/{id}`` — single registry row + deprecation status
* ``GET    /api/v1/toggles/resolve`` — resolved value for current tenant
  (optionally with ``workflow_id`` query param)
* ``PUT    /api/v1/tenant/toggles/{id}`` — set tenant override
* ``DELETE /api/v1/tenant/toggles/{id}`` — remove tenant override

Per-call overrides are NOT set via these endpoints — they live in the
job submission body's ``overrides{}`` map and are resolved by the same
:class:`ConfigResolver` per-request.

Workflow CRUD and workflow-scoped overrides land in a sibling router
(``workflows.py``) — kept separate to keep this file scoped.
"""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.tenants import toggle_audit
from lintpdf.tenants.config_resolver import ConfigResolver
from lintpdf.tenants.toggle_models import (
    MergeStrategy,
    Toggle,
    ToggleAuditLog,
    ToggleOverride,
    ToggleScope,
    ToggleType,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["toggles"])


# ---- response schemas ---------------------------------------------------


class ToggleResponse(BaseModel):
    """Public registry row."""

    id: str
    category: str
    human_name: str
    type: ToggleType
    default_value: Any
    allowed_range: Any | None
    override_at: list[ToggleScope]
    lockable: bool
    merge_strategy: MergeStrategy
    description: str | None
    deprecated: bool = Field(
        ...,
        description="True iff a non-NULL deprecated_at is set on the row.",
    )


class ToggleListResponse(BaseModel):
    items: list[ToggleResponse]
    total: int


class ResolveResponse(BaseModel):
    toggle_id: str
    value: Any
    locked: bool = Field(
        ...,
        description="True iff the resolved value comes from a locked tenant override.",
    )


class TenantOverrideRequest(BaseModel):
    value: Any
    locked: bool = False


class AuditEntryResponse(BaseModel):
    """Single audit-log row exposed to tenants (V-08)."""

    id: str
    toggle_id: str
    scope: ToggleScope
    scope_id: str
    action: str
    before_value: Any | None
    after_value: Any | None
    before_locked: bool | None
    after_locked: bool | None
    actor: str
    surface: str
    created_at: str


class AuditListResponse(BaseModel):
    items: list[AuditEntryResponse]
    total: int


# ---- helpers ------------------------------------------------------------


def _to_response(t: Toggle) -> ToggleResponse:
    return ToggleResponse(
        id=t.id,
        category=t.category,
        human_name=t.human_name,
        type=t.type,
        default_value=t.default_value,
        allowed_range=t.allowed_range,
        override_at=list(t.override_at or []),
        lockable=t.lockable,
        merge_strategy=t.merge_strategy,
        description=t.description,
        deprecated=t.deprecated_at is not None,
    )


# ---- registry endpoints -------------------------------------------------


@router.get("/toggles", response_model=ToggleListResponse)
def list_toggles(
    category: str | None = Query(None, description="Filter by category prefix"),
    db: Session = Depends(get_db),
) -> ToggleListResponse:
    stmt = select(Toggle)
    if category:
        stmt = stmt.where(Toggle.category == category)
    rows = db.execute(stmt.order_by(Toggle.id)).scalars().all()
    items = [_to_response(t) for t in rows]
    return ToggleListResponse(items=items, total=len(items))


@router.get("/toggles/resolve", response_model=ResolveResponse)
def resolve_toggle(
    toggle_id: str = Query(..., description="Dot-notation toggle id"),
    workflow_id: str | None = Query(None),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ResolveResponse:
    resolver = ConfigResolver(db)
    try:
        value = resolver.resolve(toggle_id, tenant_id=tenant.id, workflow_id=workflow_id)
    except KeyError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    locked = (
        db.execute(
            select(ToggleOverride.locked).where(
                ToggleOverride.toggle_id == toggle_id,
                ToggleOverride.scope == ToggleScope.TENANT,
                ToggleOverride.scope_id == str(tenant.id),
            )
        ).scalar()
        or False
    )
    return ResolveResponse(toggle_id=toggle_id, value=value, locked=locked)


@router.get("/toggles/{toggle_id:path}", response_model=ToggleResponse)
def get_toggle(
    toggle_id: str,
    db: Session = Depends(get_db),
) -> ToggleResponse:
    t = db.get(Toggle, toggle_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"unknown toggle {toggle_id!r}")
    return _to_response(t)


# ---- tenant override CRUD -----------------------------------------------


@router.put("/tenant/toggles/{toggle_id:path}", status_code=status.HTTP_200_OK)
def set_tenant_override(
    toggle_id: str,
    body: TenantOverrideRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, Any]:
    t = db.get(Toggle, toggle_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"unknown toggle {toggle_id!r}")
    if ToggleScope.TENANT not in (t.override_at or []):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"toggle {toggle_id!r} cannot be overridden at TENANT scope",
        )
    if body.locked and not t.lockable:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"toggle {toggle_id!r} is not lockable",
        )

    existing = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == toggle_id,
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant.id),
        )
    ).scalar_one_or_none()

    if existing is not None:
        toggle_audit.record(
            db,
            tenant_id=tenant.id,
            toggle_id=toggle_id,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant.id),
            action=toggle_audit.UPDATE,
            before=existing,
            after_value=body.value,
            after_locked=body.locked,
            actor="api",
            surface="api",
        )
        existing.value = body.value
        existing.locked = body.locked
        existing.set_by = "api"
    else:
        db.add(
            ToggleOverride(
                id=secrets.token_urlsafe(12),
                toggle_id=toggle_id,
                scope=ToggleScope.TENANT,
                scope_id=str(tenant.id),
                value=body.value,
                locked=body.locked,
                set_by="api",
                surface="api",
            )
        )
        toggle_audit.record(
            db,
            tenant_id=tenant.id,
            toggle_id=toggle_id,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant.id),
            action=toggle_audit.CREATE,
            before=None,
            after_value=body.value,
            after_locked=body.locked,
            actor="api",
            surface="api",
        )
    db.commit()

    # Synchronous cache invalidation per design — see ConfigResolver.invalidate.
    ConfigResolver(db).invalidate(tenant_id=tenant.id)

    return {"toggle_id": toggle_id, "scope": "TENANT", "value": body.value, "locked": body.locked}


@router.delete("/tenant/toggles/{toggle_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant_override(
    toggle_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    existing = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == toggle_id,
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant.id),
        )
    ).scalar_one_or_none()
    if existing is not None:
        toggle_audit.record(
            db,
            tenant_id=tenant.id,
            toggle_id=toggle_id,
            scope=ToggleScope.TENANT,
            scope_id=str(tenant.id),
            action=toggle_audit.DELETE,
            before=existing,
            after_value=None,
            after_locked=None,
            actor="api",
            surface="api",
        )
        db.delete(existing)
        db.commit()
        ConfigResolver(db).invalidate(tenant_id=tenant.id)


# ---- audit log (V-08) -------------------------------------------------


@router.get("/tenant/toggles/audit", response_model=AuditListResponse)
def list_tenant_audit(
    toggle_id: str | None = Query(None, description="Filter by exact toggle id"),
    scope: ToggleScope | None = Query(None, description="Filter by scope"),
    action: str | None = Query(
        None,
        description="Filter by action (CREATE | UPDATE | DELETE)",
    ),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AuditListResponse:
    stmt = select(ToggleAuditLog).where(ToggleAuditLog.tenant_id == tenant.id)
    if toggle_id:
        stmt = stmt.where(ToggleAuditLog.toggle_id == toggle_id)
    if scope is not None:
        stmt = stmt.where(ToggleAuditLog.scope == scope)
    if action is not None:
        stmt = stmt.where(ToggleAuditLog.action == action)
    stmt = stmt.order_by(ToggleAuditLog.created_at.desc()).offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    items = [
        AuditEntryResponse(
            id=str(r.id),
            toggle_id=r.toggle_id,
            scope=r.scope,
            scope_id=r.scope_id,
            action=r.action,
            before_value=r.before_value,
            after_value=r.after_value,
            before_locked=r.before_locked,
            after_locked=r.after_locked,
            actor=r.actor,
            surface=r.surface,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
    return AuditListResponse(items=items, total=len(items))
