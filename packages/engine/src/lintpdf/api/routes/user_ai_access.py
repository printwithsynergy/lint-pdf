"""User AI access configuration endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import Tenant, UserAIAccess
from lintpdf.api.schemas import (
    UserAIAccessResponse,
    UserAIAccessUpdateRequest,
)

if TYPE_CHECKING:
    import uuid as uuid_mod

router = APIRouter(prefix="/users", tags=["user-ai-access"])


@router.put("/{user_id}/ai-access", response_model=UserAIAccessResponse)
async def update_user_ai_access(
    user_id: uuid_mod.UUID,
    request: UserAIAccessUpdateRequest,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> UserAIAccessResponse:
    """Update user AI access configuration."""
    access = (
        db.query(UserAIAccess)
        .filter(UserAIAccess.user_id == user_id, UserAIAccess.tenant_id == tenant.id)
        .first()
    )
    if not access:
        access = UserAIAccess(user_id=user_id, tenant_id=tenant.id)
        db.add(access)

    updates = request.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(access, key, value)

    db.commit()
    db.refresh(access)

    return UserAIAccessResponse(
        user_id=access.user_id,
        ai_enabled=access.ai_enabled,
        personal_spending_limit=(
            float(access.personal_spending_limit) if access.personal_spending_limit else None
        ),
        trial_enabled=access.trial_enabled,
        trial_expires_at=access.trial_expires_at,
    )


@router.post("/{user_id}/ai-access/trial", response_model=UserAIAccessResponse)
async def start_user_trial(
    user_id: uuid_mod.UUID,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> UserAIAccessResponse:
    """Start an AI trial for a user (30 days)."""
    access = (
        db.query(UserAIAccess)
        .filter(UserAIAccess.user_id == user_id, UserAIAccess.tenant_id == tenant.id)
        .first()
    )
    if not access:
        access = UserAIAccess(user_id=user_id, tenant_id=tenant.id)
        db.add(access)

    if access.trial_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has an active trial.",
        )

    access.trial_enabled = True
    access.trial_expires_at = datetime.now(UTC) + timedelta(days=30)
    access.ai_enabled = True

    db.commit()
    db.refresh(access)

    return UserAIAccessResponse(
        user_id=access.user_id,
        ai_enabled=access.ai_enabled,
        personal_spending_limit=(
            float(access.personal_spending_limit) if access.personal_spending_limit else None
        ),
        trial_enabled=access.trial_enabled,
        trial_expires_at=access.trial_expires_at,
    )
