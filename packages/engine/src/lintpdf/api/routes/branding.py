"""Brand profile CRUD endpoints."""

from __future__ import annotations

import uuid as uuid_mod

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import BrandProfile, BrandProfileType, Tenant
from lintpdf.api.schemas import (
    BrandProfileCreateRequest,
    BrandProfileListResponse,
    BrandProfileResponse,
    BrandProfileUpdateRequest,
    SetDefaultBrandProfileRequest,
)

router = APIRouter(tags=["branding"])


def _profile_to_response(profile: BrandProfile, tenant: Tenant) -> BrandProfileResponse:
    """Convert a BrandProfile model to a response schema."""
    return BrandProfileResponse(
        id=profile.id,
        name=profile.name,
        profile_type=profile.profile_type.value,
        brand_name=profile.brand_name,
        logo_url=profile.logo_url,
        primary_color=profile.primary_color,
        accent_color=profile.accent_color,
        footer_text=profile.footer_text,
        hide_footer=profile.hide_footer,
        is_default=tenant.default_brand_profile_id == profile.id,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "/api/v1/tenants/{tenant_id}/brand-profiles",
    response_model=BrandProfileListResponse,
)
async def list_brand_profiles(
    tenant_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileListResponse:
    """List all brand profiles for the tenant."""
    profiles = (
        db.query(BrandProfile)
        .filter(BrandProfile.tenant_id == tenant.id)
        .order_by(BrandProfile.created_at)
        .all()
    )
    return BrandProfileListResponse(profiles=[_profile_to_response(p, tenant) for p in profiles])


@router.post(
    "/api/v1/tenants/{tenant_id}/brand-profiles",
    response_model=BrandProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand_profile(
    tenant_id: str,
    request: BrandProfileCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Create a new brand profile."""
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)
    if not entitlements.whitelabel_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brand profiles require Scale or Enterprise plan.",
        )

    # Validate profile type
    try:
        profile_type = BrandProfileType(request.profile_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid profile type: {request.profile_type}. Must be custom, lintpdf, or none.",
        ) from exc

    profile = BrandProfile(
        id=uuid_mod.uuid4(),
        tenant_id=tenant.id,
        name=request.name,
        profile_type=profile_type,
        brand_name=request.brand_name,
        logo_url=request.logo_url,
        primary_color=request.primary_color,
        accent_color=request.accent_color,
        footer_text=request.footer_text,
        hide_footer=request.hide_footer,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)


@router.get(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}",
    response_model=BrandProfileResponse,
)
async def get_brand_profile(
    tenant_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Get a brand profile by ID."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    return _profile_to_response(profile, tenant)


@router.put(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}",
    response_model=BrandProfileResponse,
)
async def update_brand_profile(
    tenant_id: str,
    profile_id: str,
    request: BrandProfileUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Update a brand profile."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    if request.name is not None:
        profile.name = request.name
    if request.profile_type is not None:
        try:
            profile.profile_type = BrandProfileType(request.profile_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid profile type: {request.profile_type}.",
            ) from exc
    if request.brand_name is not None:
        profile.brand_name = request.brand_name
    if request.logo_url is not None:
        profile.logo_url = request.logo_url
    if request.primary_color is not None:
        profile.primary_color = request.primary_color
    if request.accent_color is not None:
        profile.accent_color = request.accent_color
    if request.footer_text is not None:
        profile.footer_text = request.footer_text
    if request.hide_footer is not None:
        profile.hide_footer = request.hide_footer

    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)


@router.delete(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_brand_profile(
    tenant_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Delete a brand profile."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    # Clear default if this was the default profile
    if tenant.default_brand_profile_id == uid:
        tenant.default_brand_profile_id = None

    db.delete(profile)
    db.commit()


@router.post(
    "/api/v1/tenants/{tenant_id}/brand-profiles/{profile_id}/logo",
    response_model=BrandProfileResponse,
)
async def upload_brand_logo(
    tenant_id: str,
    profile_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse:
    """Upload a logo for a brand profile."""
    try:
        uid = uuid_mod.UUID(profile_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid profile ID format.",
        ) from exc

    profile = (
        db.query(BrandProfile)
        .filter(BrandProfile.id == uid, BrandProfile.tenant_id == tenant.id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    # Validate file type
    if file.content_type not in ("image/png", "image/jpeg", "image/svg+xml", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Logo must be PNG, JPEG, SVG, or WebP.",
        )

    # Read file content
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Logo file must be under 2 MB.",
        )

    # Upload to storage
    from lintpdf.api.storage import get_storage

    storage = get_storage()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    file_key = f"brand-logos/{tenant.id}/{profile.id}.{ext}"
    storage.upload_file(file_key, content, content_type=file.content_type or "image/png")

    # Update profile logo URL
    from lintpdf.api.config import get_settings

    settings = get_settings()
    logo_url = f"{settings.report_base_url}/assets/{file_key}"
    profile.logo_url = logo_url

    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)


@router.patch(
    "/api/v1/tenants/{tenant_id}/default-brand-profile",
    response_model=BrandProfileResponse | None,
)
async def set_default_brand_profile(
    tenant_id: str,
    request: SetDefaultBrandProfileRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BrandProfileResponse | None:
    """Set or clear the tenant's default brand profile."""
    if request.brand_profile_id is None:
        tenant.default_brand_profile_id = None
        db.commit()
        return None

    profile = (
        db.query(BrandProfile)
        .filter(
            BrandProfile.id == request.brand_profile_id,
            BrandProfile.tenant_id == tenant.id,
        )
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand profile not found.",
        )

    tenant.default_brand_profile_id = profile.id
    db.commit()
    db.refresh(profile)

    return _profile_to_response(profile, tenant)
