"""AI configuration service — CRUD operations for tenant AI settings."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import TenantAIConfig


def get_or_create_ai_config(tenant_id: uuid.UUID, db: Session) -> TenantAIConfig:
    """Get existing AI config or create a default one."""
    from lintpdf.api.models import TenantAIConfig

    config = db.query(TenantAIConfig).filter(TenantAIConfig.tenant_id == tenant_id).first()
    if config is None:
        config = TenantAIConfig(tenant_id=tenant_id)
        db.add(config)
        db.flush()
    return config


def update_ai_config(
    tenant_id: uuid.UUID,
    updates: dict[str, Any],
    db: Session,
) -> TenantAIConfig:
    """Update AI config fields. Only updates provided keys."""
    config = get_or_create_ai_config(tenant_id, db)

    # Allowed updatable fields (tenant self-service)
    allowed_fields = {
        "enabled_categories",
        "default_ai_features",
        "brand_palette",
        "custom_dictionary",
        "industry_type",
        "regulatory_market",
        "default_safe_zone_mm",
        "default_package_capacity_ml",
        "default_package_surface_area_cm2",
        "min_image_quality_score",
        "delta_e_warning_threshold",
        "delta_e_error_threshold",
        "monthly_spending_limit",
    }

    for key, value in updates.items():
        if key in allowed_fields and hasattr(config, key):
            setattr(config, key, value)

    db.flush()
    return config


def admin_update_ai_config(
    tenant_id: uuid.UUID,
    updates: dict[str, Any],
    db: Session,
) -> TenantAIConfig:
    """Admin-level AI config update. Can toggle ai_enabled, billing_mode, etc."""
    config = get_or_create_ai_config(tenant_id, db)

    admin_fields = {
        "ai_enabled",
        "billing_mode",
        "credit_balance",
        "overage_rate",
        "trial_enabled",
        "trial_expires_at",
        "enabled_categories",
        "monthly_spending_limit",
    }

    for key, value in updates.items():
        if key in admin_fields and hasattr(config, key):
            setattr(config, key, value)

    db.flush()
    return config


def add_reference_logo(
    tenant_id: uuid.UUID,
    logo_name: str,
    storage_key: str,
    db: Session,
) -> dict[str, str]:
    """Add a reference logo to the tenant's AI config."""
    config = get_or_create_ai_config(tenant_id, db)

    logo_entry = {
        "id": str(uuid.uuid4()),
        "name": logo_name,
        "storage_key": storage_key,
    }

    logos = list(config.reference_logos or [])
    logos.append(logo_entry)
    config.reference_logos = logos
    db.flush()

    return logo_entry


def remove_reference_logo(
    tenant_id: uuid.UUID,
    logo_id: str,
    db: Session,
) -> bool:
    """Remove a reference logo by ID. Returns True if found and removed."""
    config = get_or_create_ai_config(tenant_id, db)

    if not config.reference_logos:
        return False

    logos = [lg for lg in config.reference_logos if lg.get("id") != logo_id]
    if len(logos) == len(config.reference_logos):
        return False

    config.reference_logos = logos
    db.flush()
    return True
