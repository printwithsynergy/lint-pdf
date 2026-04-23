"""BrandSpec CRUD routes.

Each tenant maintains an independent collection of named colour
specifications (typically one per end-customer). These routes are
the control plane for that collection:

* ``GET    /api/v1/brand-specs`` — list visible specs.
* ``POST   /api/v1/brand-specs`` — create.
* ``GET    /api/v1/brand-specs/{id}`` — detail.
* ``PATCH  /api/v1/brand-specs/{id}`` — update any subset of
  fields; passing ``is_default=true`` demotes the currently-
  default spec atomically.
* ``DELETE /api/v1/brand-specs/{id}`` — soft-delete (archive).
  Historical jobs that captured this spec at submit time still
  resolve against it.
* ``POST   /api/v1/brand-specs/{id}/restore`` — un-archive.

Resolution at job-time lives in
:mod:`lintpdf.brand_specs.resolver`; these routes only manage
the rows.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import BrandSpec, Tenant
from lintpdf.api.schemas import (
    BrandSpecColorEntry,
    BrandSpecCreateRequest,
    BrandSpecListResponse,
    BrandSpecResponse,
    BrandSpecRichBlackSpec,
    BrandSpecUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brand-specs", tags=["brand-specs"])


def _to_response(spec: BrandSpec) -> BrandSpecResponse:
    return BrandSpecResponse(
        id=spec.id,
        tenant_id=spec.tenant_id,
        name=spec.name,
        customer_name=spec.customer_name,
        description=spec.description,
        colors=[BrandSpecColorEntry(**c) for c in (spec.colors or [])],
        rich_black_spec=(
            BrandSpecRichBlackSpec(**spec.rich_black_spec)
            if spec.rich_black_spec
            else None
        ),
        is_default=spec.is_default,
        is_archived=spec.is_archived,
        created_at=spec.created_at,
        updated_at=spec.updated_at,
    )


def _clear_existing_default(db: Session, tenant_id: uuid_mod.UUID) -> None:
    """Demote whichever non-archived spec currently carries
    ``is_default=TRUE`` for this tenant. Called before setting a
    new default so the partial-unique index never rejects the
    insert/update. No-op when no default row exists.
    """
    (
        db.query(BrandSpec)
        .filter(
            BrandSpec.tenant_id == tenant_id,
            BrandSpec.is_default.is_(True),
            BrandSpec.is_archived.is_(False),
        )
        .update({BrandSpec.is_default: False}, synchronize_session=False)
    )


@router.get("", response_model=BrandSpecListResponse)
async def list_brand_specs(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecListResponse:
    """List BrandSpecs for the current tenant.

    Archived rows are hidden by default so the UI picker stays
    short; pass ``?include_archived=true`` to fetch them for the
    management view.
    """
    q = db.query(BrandSpec).filter(BrandSpec.tenant_id == tenant.id)
    if not include_archived:
        q = q.filter(BrandSpec.is_archived.is_(False))
    specs = q.order_by(
        BrandSpec.is_default.desc(),
        BrandSpec.name.asc(),
    ).all()
    return BrandSpecListResponse(brand_specs=[_to_response(s) for s in specs])


@router.post("", response_model=BrandSpecResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_spec(
    request: BrandSpecCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecResponse:
    """Create a new BrandSpec for the current tenant."""
    if request.is_default:
        _clear_existing_default(db, tenant.id)

    spec = BrandSpec(
        id=uuid_mod.uuid4(),
        tenant_id=tenant.id,
        name=request.name,
        customer_name=request.customer_name,
        description=request.description,
        colors=[c.model_dump() for c in request.colors],
        rich_black_spec=(
            request.rich_black_spec.model_dump()
            if request.rich_black_spec is not None
            else None
        ),
        is_default=request.is_default,
        is_archived=False,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return _to_response(spec)


def _get_spec_or_404(
    db: Session, spec_id: str, tenant_id: uuid_mod.UUID
) -> BrandSpec:
    try:
        uid = uuid_mod.UUID(spec_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid brand spec ID format.",
        ) from exc

    spec: BrandSpec | None = (
        db.query(BrandSpec)
        .filter(BrandSpec.id == uid, BrandSpec.tenant_id == tenant_id)
        .first()
    )
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand spec '{spec_id}' not found.",
        )
    return spec


@router.get("/{spec_id}", response_model=BrandSpecResponse)
async def get_brand_spec(
    spec_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecResponse:
    spec = _get_spec_or_404(db, spec_id, tenant.id)
    return _to_response(spec)


@router.patch("/{spec_id}", response_model=BrandSpecResponse)
async def update_brand_spec(
    spec_id: str,
    request: BrandSpecUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecResponse:
    """Patch any subset of fields. ``is_default=true`` demotes
    any existing default spec atomically inside the same
    transaction so the partial-unique index never sees two
    defaults simultaneously.
    """
    spec = _get_spec_or_404(db, spec_id, tenant.id)

    if request.name is not None:
        spec.name = request.name
    if request.customer_name is not None:
        spec.customer_name = request.customer_name
    if request.description is not None:
        spec.description = request.description
    if request.colors is not None:
        spec.colors = [c.model_dump() for c in request.colors]
    if request.rich_black_spec is not None:
        spec.rich_black_spec = request.rich_black_spec.model_dump()
    if request.is_default is not None:
        if request.is_default and not spec.is_default:
            _clear_existing_default(db, tenant.id)
        spec.is_default = request.is_default

    db.commit()
    db.refresh(spec)
    return _to_response(spec)


@router.delete("/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_brand_spec(
    spec_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Soft-delete a BrandSpec.

    The row is kept so historical jobs that resolved against it
    still render their findings with the same palette context.
    Archiving also clears ``is_default`` so the tenant-default
    slot frees up for another spec.
    """
    spec = _get_spec_or_404(db, spec_id, tenant.id)
    spec.is_archived = True
    spec.is_default = False
    db.commit()


@router.post("/{spec_id}/restore", response_model=BrandSpecResponse)
async def restore_brand_spec(
    spec_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecResponse:
    """Un-archive a BrandSpec. ``is_default`` stays ``false`` —
    the caller must explicitly mark it default again if that's
    the intent.
    """
    spec = _get_spec_or_404(db, spec_id, tenant.id)
    spec.is_archived = False
    db.commit()
    db.refresh(spec)
    return _to_response(spec)
