"""BrandSpec CRUD routes.

Phase 0.7 PR-B3b — rewritten to read / write via the unified-config
substrate. Brand specs live as keys inside the tenant's
``ToggleOverride(toggle_id='brand', scope=TENANT)`` row, keyed by
str(uuid). The legacy ``brand_specs`` table is no longer read or
written here; PR-B4 drops it.

URLs and response shapes are preserved for backward compatibility.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from siftpdf.api.auth import get_current_tenant
from siftpdf.api.database import get_db
from siftpdf.api.models import Tenant  # noqa: TC001
from siftpdf.api.schemas import (
    BrandSpecColorEntry,
    BrandSpecCreateRequest,
    BrandSpecListResponse,
    BrandSpecResponse,
    BrandSpecRichBlackSpec,
    BrandSpecUpdateRequest,
)
from siftpdf.brand_specs import storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/brand-specs", tags=["brand-specs"])

_FALLBACK_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _parse_iso(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return _FALLBACK_TS


def _to_response(value: dict, tenant_id: uuid_mod.UUID) -> BrandSpecResponse:
    raw_id = value.get("id")
    parsed_id = uuid_mod.UUID(raw_id) if raw_id else uuid_mod.uuid4()
    return BrandSpecResponse(
        id=parsed_id,
        tenant_id=tenant_id,
        name=value.get("name", ""),
        customer_name=value.get("customer_name"),
        description=value.get("description"),
        colors=[BrandSpecColorEntry(**c) for c in (value.get("colors") or [])],
        rich_black_spec=(
            BrandSpecRichBlackSpec(**value["rich_black_spec"])
            if value.get("rich_black_spec")
            else None
        ),
        is_default=bool(value.get("is_default", False)),
        is_archived=bool(value.get("is_archived", False)),
        created_at=_parse_iso(value.get("created_at")),
        updated_at=_parse_iso(value.get("updated_at")),
    )


def _parse_uuid(spec_id: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(spec_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid brand spec ID format.",
        ) from exc


def _get_or_404(db: Session, tenant_id: uuid_mod.UUID, spec_id: str) -> dict:
    uid = _parse_uuid(spec_id)
    value = storage.get_spec(db, tenant_id, uid)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand spec '{spec_id}' not found.",
        )
    return value


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
    specs = list(storage.load_specs(db, tenant.id).values())
    if not include_archived:
        specs = [s for s in specs if not s.get("is_archived")]
    specs.sort(
        key=lambda v: (
            not bool(v.get("is_default")),  # default first
            (v.get("name") or "").lower(),
        )
    )
    return BrandSpecListResponse(brand_specs=[_to_response(v, tenant.id) for v in specs])


@router.post("", response_model=BrandSpecResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_spec(
    request: BrandSpecCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecResponse:
    """Create a new BrandSpec for the current tenant."""
    new_id = uuid_mod.uuid4()
    now = storage.now_iso()
    new_value = {
        "id": str(new_id),
        "name": request.name,
        "customer_name": request.customer_name,
        "description": request.description,
        "colors": [c.model_dump() for c in request.colors],
        "rich_black_spec": (
            request.rich_black_spec.model_dump() if request.rich_black_spec is not None else None
        ),
        "is_default": bool(request.is_default),
        "is_archived": False,
        "created_at": now,
        "updated_at": now,
    }

    def _mutator(specs: dict) -> dict:
        if request.is_default:
            storage.clear_default(specs, except_id=str(new_id))
        specs[str(new_id)] = new_value
        return specs

    storage.mutate_specs(db, tenant_id=tenant.id, mutator=_mutator)
    return _to_response(new_value, tenant.id)


@router.get("/{spec_id}", response_model=BrandSpecResponse)
async def get_brand_spec(
    spec_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecResponse:
    value = _get_or_404(db, tenant.id, spec_id)
    return _to_response(value, tenant.id)


@router.patch("/{spec_id}", response_model=BrandSpecResponse)
async def update_brand_spec(
    spec_id: str,
    request: BrandSpecUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandSpecResponse:
    """Patch any subset of fields. ``is_default=true`` demotes any
    existing default spec atomically inside the same transaction.
    """
    _get_or_404(db, tenant.id, spec_id)  # 404 fast if missing
    uid = _parse_uuid(spec_id)
    key = str(uid)

    def _mutator(specs: dict) -> dict:
        value = dict(specs.get(key) or {})
        if request.name is not None:
            value["name"] = request.name
        if request.customer_name is not None:
            value["customer_name"] = request.customer_name
        if request.description is not None:
            value["description"] = request.description
        if request.colors is not None:
            value["colors"] = [c.model_dump() for c in request.colors]
        if request.rich_black_spec is not None:
            value["rich_black_spec"] = request.rich_black_spec.model_dump()
        if request.is_default is not None:
            if request.is_default and not value.get("is_default"):
                storage.clear_default(specs, except_id=key)
            value["is_default"] = bool(request.is_default)
        value["updated_at"] = storage.now_iso()
        specs[key] = value
        return specs

    new_specs = storage.mutate_specs(db, tenant_id=tenant.id, mutator=_mutator)
    return _to_response(new_specs[key], tenant.id)


@router.delete("/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_brand_spec(
    spec_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Soft-delete a BrandSpec.

    The entry stays so historical jobs that resolved against it
    still render their findings with the same palette context.
    Archiving also clears ``is_default`` so the tenant-default
    slot frees up for another spec.
    """
    _get_or_404(db, tenant.id, spec_id)
    key = str(_parse_uuid(spec_id))

    def _mutator(specs: dict) -> dict:
        value = dict(specs.get(key) or {})
        value["is_archived"] = True
        value["is_default"] = False
        value["updated_at"] = storage.now_iso()
        specs[key] = value
        return specs

    storage.mutate_specs(db, tenant_id=tenant.id, mutator=_mutator)


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
    _get_or_404(db, tenant.id, spec_id)
    key = str(_parse_uuid(spec_id))

    def _mutator(specs: dict) -> dict:
        value = dict(specs.get(key) or {})
        value["is_archived"] = False
        value["updated_at"] = storage.now_iso()
        specs[key] = value
        return specs

    new_specs = storage.mutate_specs(db, tenant_id=tenant.id, mutator=_mutator)
    return _to_response(new_specs[key], tenant.id)
