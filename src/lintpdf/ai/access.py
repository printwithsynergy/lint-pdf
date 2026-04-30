"""AI access control — check tenant permissions for AI features."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from lintpdf.api.models import Tenant, TenantAIConfig


def get_ai_config(tenant_id: object, db: Session) -> TenantAIConfig | None:
    """Load AI config for a tenant, or None if not configured."""
    from lintpdf.api.models import TenantAIConfig

    return db.query(TenantAIConfig).filter(TenantAIConfig.tenant_id == tenant_id).first()


def check_ai_access(tenant: Tenant, db: Session) -> TenantAIConfig:
    """Verify tenant has AI access. Raises 403 if not.

    Checks:
    1. AI config exists and is enabled
    2. Trial hasn't expired (if trial mode)

    Returns:
        The tenant's AI config.

    Raises:
        HTTPException: 403 if AI not available.
    """
    config = get_ai_config(tenant.id, db)

    if config is None or not config.ai_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "AI features are not enabled for this tenant. AI Inspections "
                "are gated per-tenant via the admin toggle "
                "(PUT /api/v1/admin/tenants/{tenant_id}/ai?ai_enabled=true) "
                "or via the tenant dashboard by an account owner. This is a "
                "per-tenant flag, not a global waitlist — once enabled, AI "
                "is available on every plan that includes AI credits."
            ),
        )

    # Check trial expiry
    if (
        config.trial_enabled
        and config.trial_expires_at
        and datetime.now(timezone.utc) > config.trial_expires_at
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your AI trial has expired. "
                "Contact your account administrator to purchase AI credits."
            ),
        )

    return config


def is_ai_available(tenant: Tenant, db: Session) -> bool:
    """Non-throwing check for AI availability."""
    config = get_ai_config(tenant.id, db)
    if config is None or not config.ai_enabled:
        return False
    return not (
        config.trial_enabled
        and config.trial_expires_at
        and datetime.now(timezone.utc) > config.trial_expires_at
    )


def check_ai_category_access(config: TenantAIConfig, categories: list[str]) -> None:
    """Verify tenant has access to requested AI categories.

    Raises 403 if any requested category is not enabled.
    """
    if not config.enabled_categories:
        # No categories enabled — block all
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No AI categories are enabled for your account.",
        )

    # "all" in enabled_categories means everything is allowed
    if "all" in config.enabled_categories:
        return

    for cat in categories:
        if cat == "all":
            continue
        if cat not in config.enabled_categories:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"AI category '{cat}' is not enabled for your account.",
            )
