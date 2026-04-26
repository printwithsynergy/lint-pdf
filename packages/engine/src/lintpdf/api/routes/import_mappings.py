"""Tenant-defined import mapping CRUD + preview endpoints.

Phase 0.7 PR-B3a — rewritten to read / write via the unified-config
substrate. Mappings live as keys inside the tenant's
``ToggleOverride(toggle_id='import_mapping', scope=TENANT)`` row,
keyed by str(uuid). The ``TenantImportMapping`` table is no longer
read or written here; the v13 legacy-fold migration carries
production data into the new shape and PR-B4 drops the table.

URLs and response shapes are preserved for backward compatibility
with the dashboard, plugin, and SDK callers.
"""

from __future__ import annotations

import secrets
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.imports.base import ParserError
from lintpdf.imports.custom import CustomMappingParser
from lintpdf.tenants import toggle_audit
from lintpdf.tenants.config_resolver import ConfigResolver
from lintpdf.tenants.toggle_models import (
    ToggleOverride,
    ToggleScope,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import Tenant

router = APIRouter(tags=["import_mappings"])

# Stable epoch fallback for created_at / updated_at when the override
# row predates timestamping inside the value (legacy migrated rows
# don't carry per-instance timestamps).
_FALLBACK_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)


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


def _to_response_from_value(value: dict[str, Any]) -> ImportMappingResponse:
    """Convert a per-instance dict (a value from the tenant's mapping dict)
    into the legacy response shape callers still expect.
    """
    raw_id = value.get("id")
    parsed_id = uuid_mod.UUID(raw_id) if raw_id else uuid_mod.uuid4()
    created = value.get("created_at")
    updated = value.get("updated_at")
    return ImportMappingResponse(
        id=parsed_id,
        name=value.get("name", ""),
        description=value.get("description"),
        format=value.get("format", "xml"),
        config=dict(value.get("config") or {}),
        sample_payload=value.get("sample_payload"),
        sample_mime=value.get("sample_mime"),
        is_active=bool(value.get("is_active", True)),
        created_at=_parse_iso(created) if created else _FALLBACK_TS,
        updated_at=_parse_iso(updated) if updated else _FALLBACK_TS,
    )


def _parse_iso(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return _FALLBACK_TS


def _parse_uuid(value: str) -> uuid_mod.UUID:
    try:
        return uuid_mod.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid mapping ID format.",
        ) from exc


def _merged_config(request_config: dict, base_format: str) -> dict:
    """Ensure the config carries a ``format`` key the parser expects."""
    cfg = dict(request_config or {})
    cfg.setdefault("format", base_format)
    return cfg


def _load_mappings_dict(db: Session, tenant_id: uuid_mod.UUID) -> dict[str, Any]:
    """Read the tenant's import_mapping override; return the value dict."""
    row = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == "import_mapping",
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant_id),
        )
    ).scalar_one_or_none()
    if row is None:
        return {}
    return dict(row.value or {})


def _persist_mappings_dict(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    new_value: dict[str, Any],
    audit_action: str,
) -> None:
    """Persist a mutated mappings dict + emit one ToggleAuditLog row.

    ``toggle_audit.record`` reads ``before.value`` lazily, so this
    helper captures the before-snapshot and calls record() BEFORE
    mutating the row.
    """
    existing = db.execute(
        select(ToggleOverride).where(
            ToggleOverride.toggle_id == "import_mapping",
            ToggleOverride.scope == ToggleScope.TENANT,
            ToggleOverride.scope_id == str(tenant_id),
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            ToggleOverride(
                id=secrets.token_urlsafe(12),
                toggle_id="import_mapping",
                scope=ToggleScope.TENANT,
                scope_id=str(tenant_id),
                value=new_value,
                locked=False,
                set_by="api",
                surface="api",
            )
        )
        toggle_audit.record(
            db,
            tenant_id=tenant_id,
            toggle_id="import_mapping",
            scope=ToggleScope.TENANT,
            scope_id=str(tenant_id),
            action=toggle_audit.CREATE,
            before=None,
            after_value=new_value,
            after_locked=False,
            actor="api",
            surface="api",
        )
    else:
        toggle_audit.record(
            db,
            tenant_id=tenant_id,
            toggle_id="import_mapping",
            scope=ToggleScope.TENANT,
            scope_id=str(tenant_id),
            action=audit_action,
            before=existing,
            after_value=new_value,
            after_locked=existing.locked,
            actor="api",
            surface="api",
        )
        existing.value = new_value
        existing.set_by = "api"

    db.commit()
    ConfigResolver(db).invalidate(tenant_id=tenant_id)


def _load_owned_mapping(
    db: Session, tenant: Tenant, mapping_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Look up a mapping by id; return ``(mappings_dict, mapping_value)``.

    Raises 404 if the id isn't present in the tenant's mapping dict.
    """
    uid = _parse_uuid(mapping_id)
    mappings = _load_mappings_dict(db, tenant.id)
    value = mappings.get(str(uid))
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import mapping not found.",
        )
    return mappings, dict(value)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


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
    mappings = _load_mappings_dict(db, tenant.id)
    rows = list(mappings.values())
    rows.sort(key=lambda v: v.get("created_at") or "")
    return ImportMappingListResponse(
        mappings=[_to_response_from_value(v) for v in rows]
    )


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

    new_id = uuid_mod.uuid4()
    now = _now_iso()
    new_mapping = {
        "id": str(new_id),
        "name": request.name.strip(),
        "description": request.description,
        "format": request.format,
        "config": config,
        "sample_payload": request.sample_payload,
        "sample_mime": request.sample_mime,
        "is_active": request.is_active,
        "created_at": now,
        "updated_at": now,
    }

    mappings = _load_mappings_dict(db, tenant.id)
    audit_action = toggle_audit.CREATE if not mappings else toggle_audit.UPDATE
    mappings[str(new_id)] = new_mapping
    _persist_mappings_dict(
        db,
        tenant_id=tenant.id,
        new_value=mappings,
        audit_action=audit_action,
    )
    return _to_response_from_value(new_mapping)


@router.get(
    "/api/v1/tenant/import-mappings/{mapping_id}",
    response_model=ImportMappingResponse,
)
async def get_import_mapping(
    mapping_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ImportMappingResponse:
    _, value = _load_owned_mapping(db, tenant, mapping_id)
    return _to_response_from_value(value)


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
    mappings, value = _load_owned_mapping(db, tenant, mapping_id)
    config = _merged_config(request.config, request.format)
    try:
        CustomMappingParser(config)
    except ParserError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    updated = {
        "id": value.get("id", mapping_id),
        "name": request.name.strip(),
        "description": request.description,
        "format": request.format,
        "config": config,
        "sample_payload": request.sample_payload,
        "sample_mime": request.sample_mime,
        "is_active": request.is_active,
        "created_at": value.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
    }
    mappings[str(_parse_uuid(mapping_id))] = updated
    _persist_mappings_dict(
        db,
        tenant_id=tenant.id,
        new_value=mappings,
        audit_action=toggle_audit.UPDATE,
    )
    return _to_response_from_value(updated)


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

    Keeps historical entries around so a job that was submitted with
    this mapping still has a config to point back to for audit.
    """
    mappings, value = _load_owned_mapping(db, tenant, mapping_id)
    value["is_active"] = False
    value["updated_at"] = _now_iso()
    mappings[str(_parse_uuid(mapping_id))] = value
    _persist_mappings_dict(
        db,
        tenant_id=tenant.id,
        new_value=mappings,
        audit_action=toggle_audit.UPDATE,
    )


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
    falls back to the stored mapping value. Parser errors surface as
    ``ok=false`` with a human-readable ``error`` instead of an HTTP 422
    so the UI can render inline feedback.
    """
    _, value = _load_owned_mapping(db, tenant, mapping_id)

    overrides = request or ImportMappingPreviewRequest()
    raw_config = (
        overrides.config
        if overrides.config is not None
        else value.get("config")
    )
    cfg = _merged_config(raw_config or {}, value.get("format", "xml"))
    payload_str = (
        overrides.sample_payload
        if overrides.sample_payload is not None
        else value.get("sample_payload")
    )
    if not payload_str:
        return ImportMappingPreviewResponse(
            ok=False,
            findings_count=0,
            sample_findings=[],
            error="No sample payload — save or paste one before previewing.",
        )

    try:
        parser = CustomMappingParser(cfg, mapping_id=str(value.get("id") or mapping_id))
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
