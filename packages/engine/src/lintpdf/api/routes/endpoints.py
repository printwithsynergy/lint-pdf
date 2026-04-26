"""Custom API endpoint management — vanity URL slugs bound to profiles.

Phase 0.7 PR-B5 — backed by ``workflows`` rows + the unified-config
substrate. The endpoint's ``profile_id`` and ``default_brand_spec_id``
live as a single ``ToggleOverride(toggle_id='endpoint_defaults',
scope=WORKFLOW)`` row keyed by the workflow id. URLs preserved
(``/api/v1/endpoints*``) but the ``id`` field shape changed: it's now
a 22-char cuid string instead of a UUID4 (Workflow ids are
cuid-style).

The legacy ``custom_endpoints`` table is dropped in alembic 047 along
with this rewrite.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import uuid as uuid_mod
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.config import get_settings
from lintpdf.api.database import get_db
from lintpdf.api.middleware import check_burst_rate_limit, check_rate_limit
from lintpdf.api.models import Job, JobStatus, Tenant
from lintpdf.api.schemas import (
    EndpointCreateRequest,
    EndpointListResponse,
    EndpointResponse,
    EndpointUpdateRequest,
    JobCreateResponse,
)
from lintpdf.api.storage import get_storage
from lintpdf.api.upload_security import PDF_TYPES, validate_upload_streaming
from lintpdf.profiles.registry import ProfileRegistry
from lintpdf.profiles.resolver import profile_exists_for_tenant
from lintpdf.tenants import toggle_audit
from lintpdf.tenants.config_resolver import ConfigResolver
from lintpdf.tenants.toggle_models import ToggleOverride, ToggleScope, Workflow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/endpoints", tags=["endpoints"])

_registry = ProfileRegistry()


# ---- helpers ------------------------------------------------------------


def _profile_exists(profile_id: str, db: Session, tenant: Tenant) -> bool:
    """Check if a profile exists (system-visible-to-tenant or custom)."""
    return profile_exists_for_tenant(db, tenant, profile_id)


def _validate_brand_spec_id(
    db: Session, tenant_id: uuid_mod.UUID, spec_id: uuid_mod.UUID | None
) -> uuid_mod.UUID | None:
    """404 if ``spec_id`` is non-None but missing/archived in the tenant's
    brand storage. Returns the validated UUID unchanged.
    """
    if spec_id is None:
        return None
    from lintpdf.brand_specs import storage as _brand_storage

    value = _brand_storage.get_spec(db, tenant_id, spec_id)
    if value is None or value.get("is_archived"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand spec '{spec_id}' not found or archived.",
        )
    return spec_id


def _read_endpoint_defaults(
    db: Session, workflow_id: str
) -> tuple[str | None, uuid_mod.UUID | None]:
    """Return ``(profile_id, default_brand_spec_id)`` for a workflow.

    Both values come from the ``endpoint_defaults`` ToggleOverride at
    WORKFLOW scope. Missing override → ``(None, None)``.
    """
    row = (
        db.query(ToggleOverride)
        .filter(
            ToggleOverride.toggle_id == "endpoint_defaults",
            ToggleOverride.scope == ToggleScope.WORKFLOW,
            ToggleOverride.scope_id == workflow_id,
        )
        .first()
    )
    if row is None:
        return None, None
    value = dict(row.value or {})
    profile_id = value.get("profile_id")
    raw_brand = value.get("default_brand_spec_id")
    brand_id: uuid_mod.UUID | None = None
    if raw_brand:
        try:
            brand_id = uuid_mod.UUID(raw_brand) if isinstance(raw_brand, str) else raw_brand
        except (TypeError, ValueError):
            brand_id = None
    return profile_id, brand_id


def _write_endpoint_defaults(
    db: Session,
    *,
    tenant_id: uuid_mod.UUID,
    workflow_id: str,
    profile_id: str,
    default_brand_spec_id: uuid_mod.UUID | None,
) -> None:
    """Upsert the ``endpoint_defaults`` override at WORKFLOW scope.

    Generates one ``ToggleAuditLog`` row per mutation; the audit hook
    fires BEFORE mutating ``existing.value`` so the trail captures
    the pre-state.
    """
    new_value = {
        "profile_id": profile_id,
        "default_brand_spec_id": (
            str(default_brand_spec_id) if default_brand_spec_id is not None else None
        ),
    }

    existing = (
        db.query(ToggleOverride)
        .filter(
            ToggleOverride.toggle_id == "endpoint_defaults",
            ToggleOverride.scope == ToggleScope.WORKFLOW,
            ToggleOverride.scope_id == workflow_id,
        )
        .first()
    )
    if existing is None:
        db.add(
            ToggleOverride(
                id=secrets.token_urlsafe(12),
                toggle_id="endpoint_defaults",
                scope=ToggleScope.WORKFLOW,
                scope_id=workflow_id,
                value=new_value,
                locked=False,
                set_by="api",
                surface="api",
            )
        )
        toggle_audit.record(
            db,
            tenant_id=tenant_id,
            toggle_id="endpoint_defaults",
            scope=ToggleScope.WORKFLOW,
            scope_id=workflow_id,
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
            toggle_id="endpoint_defaults",
            scope=ToggleScope.WORKFLOW,
            scope_id=workflow_id,
            action=toggle_audit.UPDATE,
            before=existing,
            after_value=new_value,
            after_locked=existing.locked,
            actor="api",
            surface="api",
        )
        existing.value = new_value
        existing.set_by = "api"

    db.commit()
    ConfigResolver(db).invalidate(tenant_id=tenant_id, workflow_id=workflow_id)


def _to_response(wf: Workflow, profile_id: str, brand_id: uuid_mod.UUID | None) -> EndpointResponse:
    return EndpointResponse(
        id=wf.id,
        slug=wf.slug,
        profile_id=profile_id or "",
        description=wf.description or "",
        is_active=wf.is_active,
        response_mode=wf.response_mode,
        created_at=wf.created_at,
        default_brand_spec_id=brand_id,
    )


def _find_workflow(
    identifier: str, db: Session, tenant_id: uuid_mod.UUID
) -> Workflow | None:
    """Look up a workflow by slug first, then by id (string)."""
    wf = (
        db.query(Workflow)
        .filter(Workflow.tenant_id == tenant_id, Workflow.slug == identifier)
        .first()
    )
    if wf is not None:
        return wf
    return (
        db.query(Workflow)
        .filter(Workflow.tenant_id == tenant_id, Workflow.id == identifier)
        .first()
    )


# ---- CRUD endpoints -----------------------------------------------------


@router.post("", response_model=EndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    request: EndpointCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> EndpointResponse:
    """Create a custom API endpoint bound to a profile."""
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if not entitlements.custom_profiles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Custom API endpoints require Growth plan or above.",
        )

    if not _profile_exists(request.profile_id, db, tenant):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{request.profile_id}' not found.",
        )

    existing = (
        db.query(Workflow)
        .filter(Workflow.tenant_id == tenant.id, Workflow.slug == request.slug)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Endpoint slug '{request.slug}' already exists.",
        )

    default_brand_spec_id = _validate_brand_spec_id(
        db, tenant.id, request.default_brand_spec_id
    )

    wf = Workflow(
        id=secrets.token_urlsafe(16),
        tenant_id=tenant.id,
        slug=request.slug,
        human_name=request.description or request.slug,
        description=request.description or None,
        is_default=False,
        is_active=True,
        response_mode=request.response_mode,
        server_revision=1,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)

    _write_endpoint_defaults(
        db,
        tenant_id=tenant.id,
        workflow_id=wf.id,
        profile_id=request.profile_id,
        default_brand_spec_id=default_brand_spec_id,
    )

    return _to_response(wf, request.profile_id, default_brand_spec_id)


@router.get("", response_model=EndpointListResponse)
async def list_endpoints(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> EndpointListResponse:
    """List all custom endpoints for the current tenant."""
    workflows = (
        db.query(Workflow)
        .filter(Workflow.tenant_id == tenant.id)
        .order_by(Workflow.created_at)
        .all()
    )
    items: list[EndpointResponse] = []
    for wf in workflows:
        profile_id, brand_id = _read_endpoint_defaults(db, wf.id)
        # Skip workflows that don't have endpoint_defaults at all —
        # those are workflow-only rows (not endpoint-shaped) created
        # via the future workflow-management UI.
        if not profile_id:
            continue
        items.append(_to_response(wf, profile_id, brand_id))
    return EndpointListResponse(endpoints=items)


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: str,
    request: EndpointUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> EndpointResponse:
    """Update a custom endpoint (slug, profile binding, branding, etc)."""
    wf = _find_workflow(endpoint_id, db, tenant.id)
    if wf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found.",
        )

    current_profile_id, current_brand_id = _read_endpoint_defaults(db, wf.id)

    new_profile_id = current_profile_id or ""
    new_brand_id = current_brand_id

    if request.slug is not None:
        existing = (
            db.query(Workflow)
            .filter(
                Workflow.tenant_id == tenant.id,
                Workflow.slug == request.slug,
                Workflow.id != wf.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Endpoint slug '{request.slug}' already exists.",
            )
        wf.slug = request.slug

    if request.profile_id is not None:
        if not _profile_exists(request.profile_id, db, tenant):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile '{request.profile_id}' not found.",
            )
        new_profile_id = request.profile_id

    if request.description is not None:
        wf.description = request.description or None

    if request.is_active is not None:
        wf.is_active = request.is_active

    if request.response_mode is not None:
        wf.response_mode = request.response_mode

    # ``default_brand_spec_id`` three-state: None=leave, "null"=clear, UUID=set
    if request.default_brand_spec_id is not None:
        raw = request.default_brand_spec_id
        if isinstance(raw, str) and raw.strip().lower() == "null":
            new_brand_id = None
        else:
            try:
                spec_uuid = raw if isinstance(raw, uuid_mod.UUID) else uuid_mod.UUID(str(raw))
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="default_brand_spec_id must be a UUID or the string 'null'.",
                ) from exc
            new_brand_id = _validate_brand_spec_id(db, tenant.id, spec_uuid)

    wf.server_revision = (wf.server_revision or 0) + 1
    db.commit()

    if new_profile_id != (current_profile_id or "") or new_brand_id != current_brand_id:
        _write_endpoint_defaults(
            db,
            tenant_id=tenant.id,
            workflow_id=wf.id,
            profile_id=new_profile_id,
            default_brand_spec_id=new_brand_id,
        )

    db.refresh(wf)
    return _to_response(wf, new_profile_id, new_brand_id)


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Delete a custom endpoint (hard delete, including the Workflow row)."""
    wf = _find_workflow(endpoint_id, db, tenant.id)
    if wf is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found.",
        )

    # Drop the endpoint_defaults override + the Workflow row.
    db.query(ToggleOverride).filter(
        ToggleOverride.toggle_id == "endpoint_defaults",
        ToggleOverride.scope == ToggleScope.WORKFLOW,
        ToggleOverride.scope_id == wf.id,
    ).delete(synchronize_session=False)
    db.delete(wf)
    db.commit()
    ConfigResolver(db).invalidate(tenant_id=tenant.id, workflow_id=wf.id)


# ---- submit-via-endpoint (vanity URL) -----------------------------------


@router.post(
    "/{identifier}/submit", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED
)
async def submit_to_endpoint(
    identifier: str,
    file: UploadFile = File(..., description="PDF file to preflight"),
    wait: float | None = Query(
        default=None,
        ge=0,
        description=(
            "Override this endpoint's configured ``response_mode`` for a "
            "single request. Set to any positive value to block for "
            "inline results (bounded by ``LINTPDF_SYNC_MAX_WAIT_S``), or "
            "``0`` to force async 202 even on a ``sync``-mode endpoint. "
            "When unset, the endpoint's own ``response_mode`` decides."
        ),
    ),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> JSONResponse:
    """Submit a PDF to a custom endpoint, using its bound profile."""
    wf = _find_workflow(identifier, db, tenant.id)
    if wf is None or not wf.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{identifier}' not found.",
        )
    profile_id, brand_id = _read_endpoint_defaults(db, wf.id)
    if not profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{identifier}' has no bound profile.",
        )

    check_burst_rate_limit(tenant)
    check_rate_limit(tenant)

    spool, file_size = await validate_upload_streaming(
        file,
        allowed_types=PDF_TYPES,
        max_size_bytes=tenant.max_file_size_mb * 1024 * 1024,
        settings=get_settings(),
    )

    job_id = uuid_mod.uuid4()
    storage = get_storage()
    loop = asyncio.get_running_loop()
    try:
        file_key = await loop.run_in_executor(
            None,
            storage.upload_pdf_stream,
            str(tenant.id),
            str(job_id),
            spool,
        )
    finally:
        with contextlib.suppress(Exception):
            spool.close()

    job = Job(
        id=job_id,
        tenant_id=tenant.id,
        status=JobStatus.PENDING,
        profile_id=profile_id,
        file_key=file_key,
        file_name=file.filename,
        file_size=file_size,
        # Inherit the endpoint's default brand spec at submit time so
        # the worker has a stable pointer even if the endpoint's
        # default is re-bound later.
        brand_spec_id=brand_id,
    )
    db.add(job)
    db.commit()

    # Phase 0.7 PR-A snapshot — bind this submission to the workflow
    # so the resolved-config snapshot captures WORKFLOW-scope overrides.
    try:
        from lintpdf.tenants.snapshot import write_snapshot

        write_snapshot(
            db,
            job_id=job.id,
            tenant_id=tenant.id,
            workflow_id=wf.id,
            call_overrides=None,
        )
    except Exception:
        logger.exception("failed to write resolved_config_snapshot for endpoint job %s", job.id)

    from lintpdf.queue.tasks import run_preflight
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    try:
        from lintpdf.profiles.registry import ProfileNotFoundError, ProfileRegistry

        profile_ai_enabled = bool(ProfileRegistry().get(profile_id).ai.enabled)
    except ProfileNotFoundError:
        profile_ai_enabled = True
    except Exception:
        profile_ai_enabled = True

    if profile_ai_enabled:
        queue_name = "ai_heavy"
    elif entitlements.priority_processing:
        queue_name = "priority"
    else:
        queue_name = "default"

    run_preflight.apply_async(
        args=[str(job_id), profile_id, file_key],
        queue=queue_name,
    )

    settings_obj = get_settings()
    effective_wait: float = 0.0
    if wait is not None:
        effective_wait = min(wait, settings_obj.sync_max_wait_s)
    elif wf.response_mode == "sync":
        effective_wait = settings_obj.sync_max_wait_s

    if effective_wait > 0:
        from lintpdf.api.routes.jobs import poll_job_until_terminal

        job_response = await poll_job_until_terminal(
            job_id=job_id,
            tenant_id=tenant.id,
            db=db,
            max_wait_s=effective_wait,
        )
        if job_response is not None:
            return JSONResponse(
                content=job_response.model_dump(mode="json"),
                status_code=status.HTTP_200_OK,
            )

    return JSONResponse(
        content=JobCreateResponse(job_id=job_id).model_dump(mode="json"),
        status_code=status.HTTP_202_ACCEPTED,
    )
