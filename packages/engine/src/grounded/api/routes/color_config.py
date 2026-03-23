"""Color management configuration endpoints — tenant color config management."""

from __future__ import annotations

import uuid as uuid_mod

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session  # noqa: TC002

from grounded.api.auth import get_current_tenant
from grounded.api.database import get_db
from grounded.api.models import Tenant, TenantColorConfig  # noqa: TC001
from grounded.api.schemas import (
    ColorConfigResponse,
    ColorConfigUpdateRequest,
    GamutConditionsListResponse,
    GamutConditionResponse,
    IccProfileUploadResponse,
    PaletteUpdateRequest,
    PantoneOverridesResponse,
    PantoneOverridesUpdateRequest,
)

router = APIRouter(prefix="/tenants", tags=["color-config"])


@router.get("/{tenant_id}/color-config", response_model=ColorConfigResponse)
async def get_color_config(
    tenant_id: uuid_mod.UUID,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> ColorConfigResponse:
    """Get tenant color management configuration."""
    config = db.query(TenantColorConfig).filter(TenantColorConfig.tenant_id == tenant_id).first()
    if not config:
        config = TenantColorConfig(tenant_id=tenant_id)
        db.add(config)
        db.commit()
        db.refresh(config)

    return ColorConfigResponse(
        default_output_condition=config.default_output_condition,
        custom_icc_profiles=config.custom_icc_profiles,
        brand_palette=config.brand_palette,
        custom_dictionary_words=config.custom_dictionary_words,
        default_tac_threshold=config.default_tac_threshold,
        default_safe_zone_margin_mm=float(config.default_safe_zone_margin_mm),
        package_capacity_default=config.package_capacity_default,
        package_surface_area_default=(
            float(config.package_surface_area_default)
            if config.package_surface_area_default
            else None
        ),
        target_market=config.target_market,
        epm_mode_default=config.epm_mode_default,
        custom_pantone_overrides=config.custom_pantone_overrides,
    )


@router.put("/{tenant_id}/color-config", response_model=ColorConfigResponse)
async def update_color_config(
    tenant_id: uuid_mod.UUID,
    request: ColorConfigUpdateRequest,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> ColorConfigResponse:
    """Update color management configuration."""
    config = db.query(TenantColorConfig).filter(TenantColorConfig.tenant_id == tenant_id).first()
    if not config:
        config = TenantColorConfig(tenant_id=tenant_id)
        db.add(config)

    updates = request.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)

    return ColorConfigResponse(
        default_output_condition=config.default_output_condition,
        custom_icc_profiles=config.custom_icc_profiles,
        brand_palette=config.brand_palette,
        custom_dictionary_words=config.custom_dictionary_words,
        default_tac_threshold=config.default_tac_threshold,
        default_safe_zone_margin_mm=float(config.default_safe_zone_margin_mm),
        package_capacity_default=config.package_capacity_default,
        package_surface_area_default=(
            float(config.package_surface_area_default)
            if config.package_surface_area_default
            else None
        ),
        target_market=config.target_market,
        epm_mode_default=config.epm_mode_default,
        custom_pantone_overrides=config.custom_pantone_overrides,
    )


@router.post(
    "/{tenant_id}/color-config/profiles",
    response_model=IccProfileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_icc_profile(
    tenant_id: uuid_mod.UUID,
    file: UploadFile = File(..., description="ICC profile file"),  # noqa: B008
    name: str = "",
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> IccProfileUploadResponse:
    """Upload a custom ICC profile for gamut checking."""
    from grounded.profiles.icc.profile_manager import validate_icc_profile_bytes

    content = await file.read()
    profile_info = validate_icc_profile_bytes(content)

    if not profile_info.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=profile_info.get("error", "Invalid ICC profile."),
        )

    config = db.query(TenantColorConfig).filter(TenantColorConfig.tenant_id == tenant_id).first()
    if not config:
        config = TenantColorConfig(tenant_id=tenant_id)
        db.add(config)

    profile_id = str(uuid_mod.uuid4())
    profile_entry = {
        "id": profile_id,
        "name": name or file.filename or "Unnamed",
        "color_space": profile_info.get("color_space"),
        "version": profile_info.get("version"),
    }

    profiles = list(config.custom_icc_profiles or [])
    profiles.append(profile_entry)
    config.custom_icc_profiles = profiles

    db.commit()

    return IccProfileUploadResponse(
        profile_id=profile_id,
        name=profile_entry["name"],
        color_space=profile_info.get("color_space"),
        version=profile_info.get("version"),
    )


@router.delete(
    "/{tenant_id}/color-config/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_icc_profile(
    tenant_id: uuid_mod.UUID,
    profile_id: str,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> None:
    """Remove a custom ICC profile."""
    config = db.query(TenantColorConfig).filter(TenantColorConfig.tenant_id == tenant_id).first()
    if not config or not config.custom_icc_profiles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found.",
        )

    original_count = len(config.custom_icc_profiles)
    config.custom_icc_profiles = [
        p for p in config.custom_icc_profiles if p.get("id") != profile_id
    ]

    if len(config.custom_icc_profiles) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found.",
        )

    db.commit()


@router.put("/{tenant_id}/color-config/palette")
async def set_brand_palette(
    tenant_id: uuid_mod.UUID,
    request: PaletteUpdateRequest,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> dict[str, object]:
    """Set brand color palette for color compliance checking."""
    config = db.query(TenantColorConfig).filter(TenantColorConfig.tenant_id == tenant_id).first()
    if not config:
        config = TenantColorConfig(tenant_id=tenant_id)
        db.add(config)

    config.brand_palette = request.colors
    db.commit()

    return {"message": "Brand palette updated", "colors": len(request.colors)}


# --- Pantone override endpoints ---


def _get_or_create_config(
    db: Session, tenant_id: uuid_mod.UUID
) -> TenantColorConfig:
    config = db.query(TenantColorConfig).filter(
        TenantColorConfig.tenant_id == tenant_id
    ).first()
    if not config:
        config = TenantColorConfig(tenant_id=tenant_id)
        db.add(config)
    return config


def _invalidate_pantone_cache(tenant_id: uuid_mod.UUID) -> None:
    """Best-effort Redis cache invalidation after DB writes."""
    try:
        from grounded.api.middleware import get_redis_client
        from grounded.profiles.icc.pantone_cache import invalidate

        invalidate(get_redis_client(), str(tenant_id))
    except Exception:
        pass  # Non-critical — cache will expire via TTL


@router.get(
    "/{tenant_id}/color-config/pantone-overrides",
    response_model=PantoneOverridesResponse,
)
async def get_pantone_overrides(
    tenant_id: uuid_mod.UUID,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> PantoneOverridesResponse:
    """Get current Pantone color overrides for a tenant."""
    config = db.query(TenantColorConfig).filter(
        TenantColorConfig.tenant_id == tenant_id
    ).first()
    overrides = (config.custom_pantone_overrides or {}) if config else {}
    return PantoneOverridesResponse(count=len(overrides), overrides=overrides)


@router.put(
    "/{tenant_id}/color-config/pantone-overrides",
    response_model=PantoneOverridesResponse,
)
async def set_pantone_overrides(
    tenant_id: uuid_mod.UUID,
    request: PantoneOverridesUpdateRequest,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> PantoneOverridesResponse:
    """Bulk set / replace all Pantone color overrides for a tenant.

    Names are normalized to uppercase with collapsed whitespace so they
    match ``PantoneManager`` lookup keys.
    """
    from grounded.profiles.icc.pantone_manager import _normalize_pantone_name

    config = _get_or_create_config(db, tenant_id)

    overrides: dict[str, dict[str, object]] = {}
    for entry in request.overrides:
        key = _normalize_pantone_name(entry.name)
        data: dict[str, object] = {"lab": entry.lab}
        if entry.cmyk_bridge is not None:
            data["cmyk_bridge"] = entry.cmyk_bridge
        overrides[key] = data

    config.custom_pantone_overrides = overrides
    db.commit()

    _invalidate_pantone_cache(tenant_id)

    return PantoneOverridesResponse(count=len(overrides), overrides=overrides)


@router.delete(
    "/{tenant_id}/color-config/pantone-overrides",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_pantone_overrides(
    tenant_id: uuid_mod.UUID,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> None:
    """Clear all Pantone overrides for a tenant."""
    config = db.query(TenantColorConfig).filter(
        TenantColorConfig.tenant_id == tenant_id
    ).first()
    if config and config.custom_pantone_overrides:
        config.custom_pantone_overrides = None
        db.commit()

    _invalidate_pantone_cache(tenant_id)


@router.get(
    "/{tenant_id}/color-config/gamut-conditions", response_model=GamutConditionsListResponse
)
async def list_gamut_conditions(
    tenant_id: uuid_mod.UUID,
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> GamutConditionsListResponse:
    """List available gamut conditions."""
    from grounded.profiles.icc.profile_manager import get_available_conditions

    raw = get_available_conditions()
    conditions = [
        GamutConditionResponse(
            slug=slug,
            name=info.get("name", slug),
            region=info.get("region", ""),
            use_case=info.get("use_case", ""),
            tac_limit=info.get("tac_limit"),
        )
        for slug, info in raw.items()
    ]

    return GamutConditionsListResponse(conditions=conditions)
