"""Profile management endpoints."""

from __future__ import annotations

import logging
import uuid as uuid_mod

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status  # noqa: E402
from sqlalchemy.orm import Session  # noqa: TC002, E402

from lintpdf.api.auth import get_current_tenant  # noqa: E402
from lintpdf.api.database import get_db  # noqa: E402
from lintpdf.api.models import CustomProfile, Tenant  # noqa: E402
from lintpdf.api.schemas import (  # noqa: E402
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileDetailResponse,
    ProfileListResponse,
    ProfileSummaryResponse,
)
from lintpdf.profiles.registry import ProfileRegistry  # noqa: E402
from lintpdf.profiles.resolver import (  # noqa: E402
    get_custom_profile,
    get_visible_system_profile,
    list_visible_system_profiles,
)
from lintpdf.profiles.schema import PreflightProfile  # noqa: E402

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])

# Shared registry instance for built-in profiles
_registry = ProfileRegistry()


def get_registry() -> ProfileRegistry:
    """Get the profile registry. Can be overridden in tests."""
    return _registry


def _load_custom_profiles_from_db(db: Session, tenant_id: uuid_mod.UUID) -> list[CustomProfile]:
    """Load custom profiles for a tenant from the database."""
    return db.query(CustomProfile).filter(CustomProfile.tenant_id == tenant_id).all()


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ProfileListResponse:
    """List all preflight profiles visible to ``tenant``.

    Source of truth is the ``system_profiles`` table (seeded from the
    bundled JSON at first boot) filtered by per-row visibility +
    the tenant's ``custom_profiles`` rows. On a collision between a
    tenant's custom ``profile_id`` and a system one, the custom wins
    inside that tenant's own view — the reverse of the pre-DB
    registry's behavior. This matches the expected "tenant can
    override a system preset by cloning + editing" UX.
    """
    custom_rows = _load_custom_profiles_from_db(db, tenant.id)
    custom_ids = {row.profile_id for row in custom_rows}

    profiles: list[ProfileSummaryResponse] = []

    for sp in list_visible_system_profiles(db, tenant):
        if sp.profile_id in custom_ids:
            # Tenant has shadowed this system preset with a custom of
            # their own — emit only the custom.
            continue
        try:
            fp = PreflightProfile.model_validate(sp.preflight_profile_json)
        except Exception:
            logger.warning(
                "Skipping malformed system profile: %s", sp.profile_id, exc_info=True
            )
            continue
        profiles.append(
            ProfileSummaryResponse(
                profile_id=sp.profile_id,
                name=fp.name,
                description=fp.description,
                conformance=fp.conformance,
                workflow=fp.workflow,
                is_builtin=True,
            )
        )

    for row in custom_rows:
        try:
            fp = PreflightProfile.model_validate(row.preflight_profile_json)
            profiles.append(
                ProfileSummaryResponse(
                    profile_id=row.profile_id,
                    name=fp.name,
                    description=fp.description,
                    conformance=fp.conformance,
                    workflow=fp.workflow,
                    is_builtin=False,
                )
            )
        except Exception:
            logger.warning(
                "Skipping malformed custom profile: %s", row.profile_id, exc_info=True
            )

    return ProfileListResponse(profiles=profiles)


@router.get("/{profile_id}", response_model=ProfileDetailResponse)
async def get_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ProfileDetailResponse:
    """Get detailed profile configuration.

    Custom-over-system precedence matches ``list_profiles``.
    """
    custom = get_custom_profile(db, tenant, profile_id)
    if custom is not None:
        fp = PreflightProfile.model_validate(custom.preflight_profile_json)
        return ProfileDetailResponse(
            profile_id=profile_id,
            name=fp.name,
            description=fp.description,
            version=fp.version,
            conformance=fp.conformance,
            workflow=fp.workflow,
            checks=fp.checks.model_dump(),
            thresholds=fp.thresholds.model_dump(),
            is_builtin=False,
        )

    sp = get_visible_system_profile(db, tenant, profile_id)
    if sp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found.",
        )

    fp = PreflightProfile.model_validate(sp.preflight_profile_json)
    return ProfileDetailResponse(
        profile_id=profile_id,
        name=fp.name,
        description=fp.description,
        version=fp.version,
        conformance=fp.conformance,
        workflow=fp.workflow,
        checks=fp.checks.model_dump(),
        thresholds=fp.thresholds.model_dump(),
        is_builtin=True,
    )


@router.post("", response_model=ProfileCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    request: ProfileCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ProfileCreateResponse:
    """Create a custom preflight profile."""
    registry = get_registry()

    # Validate the preflight profile JSON
    try:
        fp = PreflightProfile.model_validate(request.preflight_profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid Preflight Profile: {e}",
        ) from e

    # Enforce tier-based restrictions on custom profiles
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    if not entitlements.custom_profiles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Custom Preflight Profiles require Growth plan or above.",
        )

    # Prevent overwriting builtins
    if registry.has(request.profile_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile '{request.profile_id}' is a built-in profile and cannot be overwritten.",
        )

    # Check for existing custom profile for this tenant
    existing: CustomProfile | None = (
        db.query(CustomProfile)
        .filter(
            CustomProfile.tenant_id == tenant.id, CustomProfile.profile_id == request.profile_id
        )
        .first()
    )

    # Enforce max custom profiles limit (only for new profiles, not updates)
    if existing is None:
        current_count = db.query(CustomProfile).filter(CustomProfile.tenant_id == tenant.id).count()
        if current_count >= entitlements.max_custom_profiles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Custom profile limit reached ({entitlements.max_custom_profiles}). Upgrade your plan for more.",
            )

    if existing:
        # Update existing custom profile
        existing.preflight_profile_json = fp.model_dump(mode="json")
        db.commit()
    else:
        # Create new custom profile row
        row = CustomProfile(
            id=uuid_mod.uuid4(),
            tenant_id=tenant.id,
            profile_id=request.profile_id,
            preflight_profile_json=fp.model_dump(mode="json"),
        )
        db.add(row)
        db.commit()

    return ProfileCreateResponse(profile_id=request.profile_id)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Delete a custom profile. Built-in profiles cannot be deleted."""
    registry = get_registry()

    if registry.has(profile_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete built-in profiles.",
        )

    row: CustomProfile | None = (
        db.query(CustomProfile)
        .filter(CustomProfile.tenant_id == tenant.id, CustomProfile.profile_id == profile_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found.",
        )

    db.delete(row)
    db.commit()
