"""AI configuration endpoints — tenant self-service AI config management."""

from __future__ import annotations

import uuid as uuid_mod

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.ai_schemas import (
    AIConfigResponse,
    AIConfigUpdateRequest,
    DictionaryUpdateRequest,
    LogoUploadResponse,
    PaletteUpdateRequest,
)
from lintpdf.api.auth import get_current_tenant
from lintpdf.api.config import get_settings
from lintpdf.api.database import get_db
from lintpdf.api.models import Tenant  # noqa: TC001 — needed at runtime for FastAPI Depends()
from lintpdf.api.upload_security import PRINT_READY_TYPES, validate_upload

router = APIRouter(prefix="/api/v1/ai/config", tags=["ai-config"])


@router.get("", response_model=AIConfigResponse)
async def get_ai_config(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AIConfigResponse:
    """Get the tenant's AI configuration."""
    from lintpdf.ai.config import get_or_create_ai_config

    config = get_or_create_ai_config(tenant.id, db)
    db.commit()

    return AIConfigResponse(
        ai_enabled=config.ai_enabled,
        billing_mode=str(config.billing_mode),
        credit_balance=config.credit_balance,
        overage_rate=config.overage_rate,
        monthly_spending_limit=config.monthly_spending_limit,
        enabled_categories=config.enabled_categories or [],
        default_ai_features=config.default_ai_features or [],
        trial_enabled=config.trial_enabled,
        trial_expires_at=config.trial_expires_at,
        brand_palette=config.brand_palette,
        reference_logos=config.reference_logos,
        custom_dictionary=config.custom_dictionary,
        industry_type=config.industry_type,
        regulatory_market=config.regulatory_market,
        default_safe_zone_mm=config.default_safe_zone_mm,
        default_package_capacity_ml=config.default_package_capacity_ml,
        default_package_surface_area_cm2=config.default_package_surface_area_cm2,
        min_image_quality_score=config.min_image_quality_score,
        delta_e_warning_threshold=config.delta_e_warning_threshold,
        delta_e_error_threshold=config.delta_e_error_threshold,
    )


@router.put("", response_model=AIConfigResponse)
async def update_ai_config(
    request: AIConfigUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AIConfigResponse:
    """Update tenant AI configuration (self-service fields only)."""
    from lintpdf.ai.access import check_ai_access
    from lintpdf.ai.config import update_ai_config as _update

    check_ai_access(tenant, db)

    updates = request.model_dump(exclude_none=True)
    config = _update(tenant.id, updates, db)
    db.commit()

    return AIConfigResponse(
        ai_enabled=config.ai_enabled,
        billing_mode=str(config.billing_mode),
        credit_balance=config.credit_balance,
        overage_rate=config.overage_rate,
        monthly_spending_limit=config.monthly_spending_limit,
        enabled_categories=config.enabled_categories or [],
        default_ai_features=config.default_ai_features or [],
        trial_enabled=config.trial_enabled,
        trial_expires_at=config.trial_expires_at,
        brand_palette=config.brand_palette,
        reference_logos=config.reference_logos,
        custom_dictionary=config.custom_dictionary,
        industry_type=config.industry_type,
        regulatory_market=config.regulatory_market,
        default_safe_zone_mm=config.default_safe_zone_mm,
        default_package_capacity_ml=config.default_package_capacity_ml,
        default_package_surface_area_cm2=config.default_package_surface_area_cm2,
        min_image_quality_score=config.min_image_quality_score,
        delta_e_warning_threshold=config.delta_e_warning_threshold,
        delta_e_error_threshold=config.delta_e_error_threshold,
    )


@router.post("/logos", response_model=LogoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_reference_logo(
    file: UploadFile = File(..., description="Logo image file"),
    name: str = Form(..., description="Logo name"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> LogoUploadResponse:
    """Upload a reference logo for logo verification."""
    from lintpdf.ai.access import check_ai_access
    from lintpdf.ai.config import add_reference_logo
    from lintpdf.api.storage import get_storage

    check_ai_access(tenant, db)

    content = await validate_upload(
        file,
        allowed_types=PRINT_READY_TYPES,
        max_size_bytes=tenant.max_file_size_mb * 1024 * 1024,
        settings=get_settings(),
    )

    # Store logo in R2
    storage = get_storage()
    logo_key = f"logos/{tenant.id}/{uuid_mod.uuid4()}"
    storage.upload_pdf(str(tenant.id), logo_key, content)

    logo_entry = add_reference_logo(tenant.id, name, logo_key, db)
    db.commit()

    return LogoUploadResponse(
        id=logo_entry["id"],
        name=logo_entry["name"],
        storage_key=logo_entry["storage_key"],
    )


@router.delete("/logos/{logo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference_logo(
    logo_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Remove a reference logo."""
    from lintpdf.ai.access import check_ai_access
    from lintpdf.ai.config import remove_reference_logo

    check_ai_access(tenant, db)

    if not remove_reference_logo(tenant.id, logo_id, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Logo '{logo_id}' not found.",
        )
    db.commit()


@router.put("/palette")
async def set_brand_palette(
    request: PaletteUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, object]:
    """Set the brand color palette for color compliance checks."""
    from lintpdf.ai.access import check_ai_access
    from lintpdf.ai.config import update_ai_config as _update

    check_ai_access(tenant, db)
    _update(tenant.id, {"brand_palette": request.colors}, db)
    db.commit()

    return {"message": "Brand palette updated", "colors": len(request.colors)}


@router.put("/dictionary")
async def set_custom_dictionary(
    request: DictionaryUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, object]:
    """Set custom spell-check dictionary words."""
    from lintpdf.ai.access import check_ai_access
    from lintpdf.ai.config import update_ai_config as _update

    check_ai_access(tenant, db)
    _update(tenant.id, {"custom_dictionary": request.words}, db)
    db.commit()

    return {"message": "Custom dictionary updated", "words": len(request.words)}
