"""Tenant-defined import mapping CRUD + preview endpoints.

Teams running proprietary or niche preflight tools supply a JSON
mapping config that tells the engine how to walk their report shape
and pull out finding fields. These endpoints let tenants manage those
mappings from the dashboard and preview a mapping against a stored
sample payload before putting it into production.
"""

from __future__ import annotations

import uuid as uuid_mod
from datetime import datetime  # noqa: TC003

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import Tenant, TenantImportMapping
from lintpdf.imports.base import ParserError
from lintpdf.imports.custom import CustomMappingParser

router = APIRouter(tags=["import_mappings"])


# --- Schemas --------------------------------------------------------------


class ImportMappingRequest(BaseModel):
    """Create or update payload for a tenant import mapping."""

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    format: str = Field(default="xml", pattern=r"^(xml|json)$")
    config: dict = Field(default_factory=dict)
    sample_payload: str | None = None
    sample_mime: str | None = Field(default=None, max_length=64)
    is_active: bool = True


class ImportMappingResponse(BaseModel):
    id: uuid_mod.UUID
    name: str
    description: str | None
    format: str
    config: dict
    sample_payload: str | None
    sample_mime: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ImportMappingListResponse(BaseModel):
    mappings: list[ImportMappingResponse]


class ImportMappingPreviewRequest(BaseModel):
    """Override payload for a one-off preview without saving the mapping.

    When omitted the preview uses the saved ``sample_payload`` on the
    mapping row. When supplied the config/payload here win so tenants
    can iterate on a mapping in the editor without clicking Save first.
    """

    config: dict | None = None
    sample_payload: str | None = None


class PreviewFindingResponse(BaseModel):
    severity: str
    message: str
    page_num: int
    inspection_id: str
    bbox: tuple[float, float, float, float] | None = None
    object_id: str | None = None
    object_type: str | None = None
    category: str | None = None


class ImportMappingPreviewResponse(BaseModel):
    ok: bool
    findings_count: int
    sample_findings: list[PreviewFindingResponse]
    error: str | None = None


# --- Helpers --------------------------------------------------------------


def _to_response(mapping: TenantImportMapping) -> ImportMappingResponse:
    return ImportMappingResponse(
        id=mapping.id,
        name=mapping.name,
        description=mapping.description,
        format=mapping.format,
        config=mapping.config or {},
        sample_payload=mapping.sample_payload,
        sample_mime=mapping.sample_mime,
        is_active=mapping.is_active,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
    )


def _parse_uuid(value: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid mapping ID format.",
        ) from exc


def _load_owned_mapping(
    db: Session, tenant: Tenant, mapping_id: str
) -> TenantImportMapping:
    uid = _parse_uuid(mapping_id)
    mapping = (
        db.query(TenantImportMapping)
        .filter(
            TenantImportMapping.id == uid,
            TenantImportMapping.tenant_id == tenant.id,
        )
        .first()
    )
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import mapping not found.",
        )
    return mapping


def _merged_config(request_config: dict, base_format: str) -> dict:
    """Ensure the config carries a ``format`` key the parser expects."""
    cfg = dict(request_config or {})
    cfg.setdefault("format", base_format)
    return cfg


# --- Routes ---------------------------------------------------------------


@router.get(
    "/api/v1/tenant/import-mappings",
    response_model=ImportMappingListResponse,
)
async def list_import_mappings(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ImportMappingListResponse:
    """List every import mapping owned by the current tenant."""
    rows = (
        db.query(TenantImportMapping)
        .filter(TenantImportMapping.tenant_id == tenant.id)
        .order_by(TenantImportMapping.created_at)
        .all()
    )
    return ImportMappingListResponse(mappings=[_to_response(r) for r in rows])


@router.post(
    "/api/v1/tenant/import-mappings",
    response_model=ImportMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_import_mapping(
    request: ImportMappingRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ImportMappingResponse:
    """Create a new import mapping.

    The mapping config is validated by instantiating
    :class:`CustomMappingParser`; a ``ParserError`` becomes a 422.
    """
    config = _merged_config(request.config, request.format)
    try:
        CustomMappingParser(config)
    except ParserError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    mapping = TenantImportMapping(
        id=uuid_mod.uuid4(),
        tenant_id=tenant.id,
        name=request.name.strip(),
        description=request.description,
        format=request.format,
        config=config,
        sample_payload=request.sample_payload,
        sample_mime=request.sample_mime,
        is_active=request.is_active,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return _to_response(mapping)


@router.get(
    "/api/v1/tenant/import-mappings/{mapping_id}",
    response_model=ImportMappingResponse,
)
async def get_import_mapping(
    mapping_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ImportMappingResponse:
    mapping = _load_owned_mapping(db, tenant, mapping_id)
    return _to_response(mapping)


@router.put(
    "/api/v1/tenant/import-mappings/{mapping_id}",
    response_model=ImportMappingResponse,
)
async def update_import_mapping(
    mapping_id: str,
    request: ImportMappingRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ImportMappingResponse:
    mapping = _load_owned_mapping(db, tenant, mapping_id)
    config = _merged_config(request.config, request.format)
    try:
        CustomMappingParser(config)
    except ParserError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    mapping.name = request.name.strip()
    mapping.description = request.description
    mapping.format = request.format
    mapping.config = config
    mapping.sample_payload = request.sample_payload
    mapping.sample_mime = request.sample_mime
    mapping.is_active = request.is_active
    db.commit()
    db.refresh(mapping)
    return _to_response(mapping)


@router.delete(
    "/api/v1/tenant/import-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_import_mapping(
    mapping_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Soft-delete by flipping ``is_active`` to false.

    Keeps historical rows around so a job that was submitted with this
    mapping still has a config to point back to for audit.
    """
    mapping = _load_owned_mapping(db, tenant, mapping_id)
    mapping.is_active = False
    db.commit()


@router.post(
    "/api/v1/tenant/import-mappings/{mapping_id}/preview",
    response_model=ImportMappingPreviewResponse,
)
async def preview_import_mapping(
    mapping_id: str,
    request: ImportMappingPreviewRequest | None = None,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ImportMappingPreviewResponse:
    """Run the mapping against a sample payload without persisting anything.

    Lets tenants iterate on a config in the editor: the request may
    override ``config`` and ``sample_payload``; anything not overridden
    falls back to the stored mapping row. Parser errors surface as
    ``ok=false`` with a human-readable ``error`` instead of an HTTP 422
    so the UI can render inline feedback.
    """
    mapping = _load_owned_mapping(db, tenant, mapping_id)

    overrides = request or ImportMappingPreviewRequest()
    raw_config = overrides.config if overrides.config is not None else mapping.config
    cfg = _merged_config(raw_config or {}, mapping.format)
    payload_str = (
        overrides.sample_payload
        if overrides.sample_payload is not None
        else mapping.sample_payload
    )
    if not payload_str:
        return ImportMappingPreviewResponse(
            ok=False,
            findings_count=0,
            sample_findings=[],
            error="No sample payload — save or paste one before previewing.",
        )

    try:
        parser = CustomMappingParser(cfg, mapping_id=str(mapping.id))
        report = parser.parse(payload_str.encode("utf-8"))
    except ParserError as exc:
        return ImportMappingPreviewResponse(
            ok=False,
            findings_count=0,
            sample_findings=[],
            error=str(exc),
        )

    sample = [
        PreviewFindingResponse(
            severity=f.severity.value,
            message=f.message,
            page_num=f.page_num,
            inspection_id=f.inspection_id,
            bbox=f.bbox,
            object_id=f.object_id,
            object_type=f.object_type,
            category=f.category or None,
        )
        for f in report.findings[:5]
    ]
    return ImportMappingPreviewResponse(
        ok=True,
        findings_count=len(report.findings),
        sample_findings=sample,
        error=None,
    )
