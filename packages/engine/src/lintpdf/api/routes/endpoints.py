"""Custom API endpoint management — vanity URL slugs bound to profiles."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid as uuid_mod

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.config import get_settings
from lintpdf.api.database import get_db
from lintpdf.api.middleware import check_burst_rate_limit, check_rate_limit
from lintpdf.api.models import (
    CustomEndpoint,
    Job,
    JobStatus,
    Tenant,
)
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/endpoints", tags=["endpoints"])

_registry = ProfileRegistry()


def _profile_exists(profile_id: str, db: Session, tenant: Tenant) -> bool:
    """Check if a profile exists (system-visible-to-tenant or custom).

    Delegates to :func:`lintpdf.profiles.resolver.profile_exists_for_tenant`
    so submission guards share the same visibility semantics as the
    tenant's ``/api/v1/profiles`` list.
    """
    return profile_exists_for_tenant(db, tenant, profile_id)


def _resolve_brand_spec_id(
    db: Session, tenant_id: uuid_mod.UUID, spec_id: uuid_mod.UUID | None
) -> uuid_mod.UUID | None:
    """Validate that ``spec_id`` (if non-None) points at a
    non-archived brand spec owned by this tenant. Raises 404
    otherwise. Returns the validated UUID unchanged so callers
    can store it on the endpoint row without re-querying.

    Phase 0.7 PR-B3b — brand specs live in the unified-config
    ``ToggleOverride(toggle_id='brand')`` row now.
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

    # Validate that the target profile exists
    if not _profile_exists(request.profile_id, db, tenant):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{request.profile_id}' not found.",
        )

    # Check for slug uniqueness within tenant
    existing = (
        db.query(CustomEndpoint)
        .filter(CustomEndpoint.tenant_id == tenant.id, CustomEndpoint.slug == request.slug)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Endpoint slug '{request.slug}' already exists.",
        )

    default_brand_spec_id = _resolve_brand_spec_id(db, tenant.id, request.default_brand_spec_id)

    endpoint = CustomEndpoint(
        id=uuid_mod.uuid4(),
        tenant_id=tenant.id,
        slug=request.slug,
        profile_id=request.profile_id,
        description=request.description,
        is_active=True,
        response_mode=request.response_mode,
        default_brand_spec_id=default_brand_spec_id,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)

    return EndpointResponse(
        id=endpoint.id,
        slug=endpoint.slug,
        profile_id=endpoint.profile_id,
        description=endpoint.description,
        is_active=endpoint.is_active,
        response_mode=endpoint.response_mode,
        created_at=endpoint.created_at,
        default_brand_spec_id=endpoint.default_brand_spec_id,
    )


@router.get("", response_model=EndpointListResponse)
async def list_endpoints(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> EndpointListResponse:
    """List all custom endpoints for the current tenant."""
    endpoints = db.query(CustomEndpoint).filter(CustomEndpoint.tenant_id == tenant.id).all()
    return EndpointListResponse(
        endpoints=[
            EndpointResponse(
                id=e.id,
                slug=e.slug,
                profile_id=e.profile_id,
                description=e.description,
                is_active=e.is_active,
                response_mode=e.response_mode,
                created_at=e.created_at,
                default_brand_spec_id=e.default_brand_spec_id,
            )
            for e in endpoints
        ]
    )


@router.patch("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: str,
    request: EndpointUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> EndpointResponse:
    """Update a custom endpoint."""
    try:
        uid = uuid_mod.UUID(endpoint_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid endpoint ID format.",
        ) from exc

    ep: CustomEndpoint | None = (
        db.query(CustomEndpoint)
        .filter(CustomEndpoint.id == uid, CustomEndpoint.tenant_id == tenant.id)
        .first()
    )
    if ep is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found.",
        )

    if request.slug is not None:
        # Check uniqueness of new slug
        existing = (
            db.query(CustomEndpoint)
            .filter(
                CustomEndpoint.tenant_id == tenant.id,
                CustomEndpoint.slug == request.slug,
                CustomEndpoint.id != uid,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Endpoint slug '{request.slug}' already exists.",
            )
        ep.slug = request.slug

    if request.profile_id is not None:
        if not _profile_exists(request.profile_id, db, tenant):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile '{request.profile_id}' not found.",
            )
        ep.profile_id = request.profile_id

    if request.description is not None:
        ep.description = request.description

    if request.is_active is not None:
        ep.is_active = request.is_active

    if request.response_mode is not None:
        ep.response_mode = request.response_mode

    # ``default_brand_spec_id`` uses a three-state convention:
    #   * omitted / None          → leave the FK unchanged
    #   * "null" (case-insensitive) → clear the FK
    #   * UUID                    → validate ownership, then set
    if request.default_brand_spec_id is not None:
        raw = request.default_brand_spec_id
        if isinstance(raw, str) and raw.strip().lower() == "null":
            ep.default_brand_spec_id = None
        else:
            try:
                spec_uuid = raw if isinstance(raw, uuid_mod.UUID) else uuid_mod.UUID(str(raw))
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="default_brand_spec_id must be a UUID or the string 'null'.",
                ) from exc
            ep.default_brand_spec_id = _resolve_brand_spec_id(db, tenant.id, spec_uuid)

    db.commit()
    db.refresh(ep)

    return EndpointResponse(
        id=ep.id,
        slug=ep.slug,
        profile_id=ep.profile_id,
        description=ep.description,
        is_active=ep.is_active,
        response_mode=ep.response_mode,
        created_at=ep.created_at,
        default_brand_spec_id=ep.default_brand_spec_id,
    )


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Delete a custom endpoint."""
    try:
        uid = uuid_mod.UUID(endpoint_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid endpoint ID format.",
        ) from exc

    ep: CustomEndpoint | None = (
        db.query(CustomEndpoint)
        .filter(CustomEndpoint.id == uid, CustomEndpoint.tenant_id == tenant.id)
        .first()
    )
    if ep is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found.",
        )

    db.delete(ep)
    db.commit()


def _find_endpoint(identifier: str, db: Session, tenant_id: uuid_mod.UUID) -> CustomEndpoint | None:
    """Look up an endpoint by slug or UUID within the tenant's scope."""
    # Try slug first — slugs are the canonical access path
    ep: CustomEndpoint | None = (
        db.query(CustomEndpoint)
        .filter(
            CustomEndpoint.tenant_id == tenant_id,
            CustomEndpoint.slug == identifier,
        )
        .first()
    )
    if ep is not None:
        return ep

    # Fall back to UUID lookup
    try:
        uid = uuid_mod.UUID(identifier)
    except ValueError:
        return None
    return (
        db.query(CustomEndpoint)
        .filter(CustomEndpoint.id == uid, CustomEndpoint.tenant_id == tenant_id)
        .first()
    )


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
    """Submit a PDF to a custom endpoint, using its bound profile.

    ``identifier`` may be either the endpoint slug (normal case) or its
    UUID (backwards compat for clients that only track the ID).
    """
    ep = _find_endpoint(identifier, db, tenant.id)
    if ep is None or not ep.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{identifier}' not found.",
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
        profile_id=ep.profile_id,
        file_key=file_key,
        file_name=file.filename,
        file_size=file_size,
        # Inherit the endpoint's default BrandSpec at submit time
        # so the worker has a stable pointer even if the endpoint's
        # default is re-bound later. Submit-time explicit overrides
        # aren't exposed here — the endpoint-submit route is for
        # vanity URLs where the caller pre-committed to the
        # endpoint's configuration.
        brand_spec_id=ep.default_brand_spec_id,
    )
    db.add(job)
    db.commit()

    # Redis pdf_cache write deliberately removed — see routes/jobs.py
    # for the bulk-scale rationale. Workers fall back to R2.

    from lintpdf.queue.tasks import run_preflight
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    # Queue routing (step 3 — queue isolation). Custom-endpoint dispatch
    # pulls AI enablement from the endpoint's bound profile, same
    # pattern as routes/batch.py.
    try:
        from lintpdf.profiles.registry import ProfileNotFoundError, ProfileRegistry

        profile_ai_enabled = bool(ProfileRegistry().get(ep.profile_id).ai.enabled)
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
        args=[str(job_id), ep.profile_id, file_key],
        queue=queue_name,
    )

    # Resolve sync behavior. The ``?wait`` query param, when present,
    # always wins so callers can force-async a sync endpoint (``wait=0``)
    # or probe a particular deadline. When absent, ``response_mode=sync``
    # implies a wait up to the server ceiling.
    settings_obj = get_settings()
    effective_wait: float = 0.0
    if wait is not None:
        effective_wait = min(wait, settings_obj.sync_max_wait_s)
    elif ep.response_mode == "sync":
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
