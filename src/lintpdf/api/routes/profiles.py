"""Profile management endpoints.

Phase 0.7 PR-B3e — custom profiles live as keys inside the tenant's
``ToggleOverride(toggle_id='profile_rules', scope=TENANT)`` row, keyed
by string profile_id. The legacy ``custom_profiles`` table is no
longer read or written here; PR-B4 drops it.

System profiles (``system_profiles`` table) stay — they're an
admin-managed global registry, not tenant configuration, and have no
equivalent ``ToggleScope`` value (the cascade has TENANT/WORKFLOW/CALL
only). Tenant-level shadowing of a system profile_id with a custom
preset of the same id continues to work via the standard
custom-over-system precedence.

URLs and response shapes are preserved.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status  # noqa: E402
from sqlalchemy.orm import Session  # noqa: TC002, E402

from lintpdf.api.auth import get_current_tenant  # noqa: E402
from lintpdf.api.database import get_db  # noqa: E402
from lintpdf.api.models import Tenant  # noqa: E402, TC001
from lintpdf.api.schemas import (  # noqa: E402
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileDetailResponse,
    ProfileListResponse,
    ProfileSummaryResponse,
)
from lintpdf.profiles import storage as _profile_storage  # noqa: E402
from lintpdf.profiles.registry import ProfileRegistry  # noqa: E402
from lintpdf.profiles.resolver import (  # noqa: E402
    get_custom_profile,
    get_visible_system_profile,
    list_visible_system_profiles,
)
from lintpdf.profiles.schema import PreflightProfile  # noqa: E402
from lintpdf.services.entitlements import (  # noqa: E402
    EntitlementsService,
    get_entitlements_service,
)

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])

# Shared registry instance for built-in profiles
_registry = ProfileRegistry()


def get_registry() -> ProfileRegistry:
    """Get the profile registry. Can be overridden in tests."""
    return _registry


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ProfileListResponse:
    """List all preflight profiles visible to ``tenant``.

    Source of truth is the ``system_profiles`` table (seeded from the
    bundled JSON at first boot) filtered by per-row visibility +
    the tenant's ``profile_rules`` ToggleOverride dict. On a collision
    between a tenant's custom ``profile_id`` and a system one, the
    custom wins inside that tenant's own view.
    """
    custom_profiles = _profile_storage.load_profiles(db, tenant.id)
    custom_ids = set(custom_profiles.keys())

    profiles: list[ProfileSummaryResponse] = []

    for sp in list_visible_system_profiles(db, tenant):
        if sp.profile_id in custom_ids:
            # Tenant has shadowed this system preset with a custom of
            # their own — emit only the custom.
            continue
        try:
            fp = PreflightProfile.model_validate(sp.preflight_profile_json)
        except Exception:
            logger.warning("Skipping malformed system profile: %s", sp.profile_id, exc_info=True)
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

    for profile_id, value in custom_profiles.items():
        try:
            fp = PreflightProfile.model_validate(value.get("preflight_profile_json") or {})
            profiles.append(
                ProfileSummaryResponse(
                    profile_id=profile_id,
                    name=fp.name,
                    description=fp.description,
                    conformance=fp.conformance,
                    workflow=fp.workflow,
                    is_builtin=False,
                )
            )
        except Exception:
            logger.warning("Skipping malformed custom profile: %s", profile_id, exc_info=True)

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
    entitlements_service: EntitlementsService = Depends(get_entitlements_service),
) -> ProfileCreateResponse:
    """Create or update a custom preflight profile.

    Phase 0.7 PR-B3e — writes to the unified-config substrate.
    """
    import uuid as uuid_mod

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
    entitlements = entitlements_service.resolve(tenant)

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

    existing = _profile_storage.get_profile(db, tenant.id, request.profile_id)

    # Enforce max custom profiles limit (only for new profiles, not updates)
    if existing is None:
        current_count = _profile_storage.count_profiles(db, tenant.id)
        if current_count >= entitlements.max_custom_profiles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Custom profile limit reached ({entitlements.max_custom_profiles})."
                    " Upgrade your plan for more."
                ),
            )

    now = _profile_storage.now_iso()
    if existing is None:
        new_value = {
            "id": str(uuid_mod.uuid4()),
            "profile_id": request.profile_id,
            "preflight_profile_json": fp.model_dump(mode="json"),
            "created_at": now,
            "updated_at": now,
        }
    else:
        new_value = {
            **existing,
            "preflight_profile_json": fp.model_dump(mode="json"),
            "updated_at": now,
        }

    def _mutator(profiles: dict) -> dict:
        profiles[request.profile_id] = new_value
        return profiles

    _profile_storage.mutate_profiles(db, tenant_id=tenant.id, mutator=_mutator)
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

    if _profile_storage.get_profile(db, tenant.id, profile_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found.",
        )

    def _mutator(profiles: dict) -> dict:
        profiles.pop(profile_id, None)
        return profiles

    _profile_storage.mutate_profiles(db, tenant_id=tenant.id, mutator=_mutator)
