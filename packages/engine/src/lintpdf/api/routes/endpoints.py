"""Custom API endpoint management — vanity URL slugs bound to profiles."""

from __future__ import annotations

import uuid as uuid_mod

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import CustomEndpoint, CustomProfile, Tenant
from lintpdf.api.schemas import (
    EndpointCreateRequest,
    EndpointListResponse,
    EndpointResponse,
    EndpointUpdateRequest,
)
from lintpdf.profiles.registry import ProfileRegistry

router = APIRouter(prefix="/api/v1/endpoints", tags=["endpoints"])

_registry = ProfileRegistry()


def _profile_exists(profile_id: str, db: Session, tenant_id: uuid_mod.UUID) -> bool:
    """Check if a profile exists (built-in or custom for this tenant)."""
    if _registry.has(profile_id):
        return True
    row = (
        db.query(CustomProfile)
        .filter(CustomProfile.tenant_id == tenant_id, CustomProfile.profile_id == profile_id)
        .first()
    )
    return row is not None


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
    if not _profile_exists(request.profile_id, db, tenant.id):
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

    endpoint = CustomEndpoint(
        id=uuid_mod.uuid4(),
        tenant_id=tenant.id,
        slug=request.slug,
        profile_id=request.profile_id,
        description=request.description,
        is_active=True,
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
        created_at=endpoint.created_at,
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
                created_at=e.created_at,
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
        if not _profile_exists(request.profile_id, db, tenant.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile '{request.profile_id}' not found.",
            )
        ep.profile_id = request.profile_id

    if request.description is not None:
        ep.description = request.description

    if request.is_active is not None:
        ep.is_active = request.is_active

    db.commit()
    db.refresh(ep)

    return EndpointResponse(
        id=ep.id,
        slug=ep.slug,
        profile_id=ep.profile_id,
        description=ep.description,
        is_active=ep.is_active,
        created_at=ep.created_at,
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
