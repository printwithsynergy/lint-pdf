"""AI credit management endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.ai_schemas import (
    CreditBalanceResponse,
    CreditTopupRequest,
    CreditTopupResponse,
)
from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db

if TYPE_CHECKING:
    from lintpdf.api.models import Tenant

router = APIRouter(prefix="/api/v1/ai/credits", tags=["ai-credits"])


@router.get("", response_model=CreditBalanceResponse)
async def get_credits(
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> CreditBalanceResponse:
    """View current AI credit balance and package status."""
    from lintpdf.ai.access import check_ai_access
    from lintpdf.ai.credits import get_credit_balance

    check_ai_access(tenant, db)
    balance = get_credit_balance(tenant.id, db)

    return CreditBalanceResponse(
        credit_balance=balance.credit_balance,
        billing_mode=balance.billing_mode,
        packages_active=balance.packages_active,
        package_credits_remaining=balance.package_credits_remaining,
        monthly_spent=balance.monthly_spent,
        monthly_spending_limit=balance.monthly_spending_limit,
    )


@router.post("/topup", response_model=CreditTopupResponse, status_code=status.HTTP_201_CREATED)
async def topup_credits(
    request: CreditTopupRequest,
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> CreditTopupResponse:
    """Purchase a credit top-up package.

    Note: In production, this would integrate with Stripe for payment.
    Currently creates the package directly.
    """
    from lintpdf.ai.access import check_ai_access

    check_ai_access(tenant, db)

    # Calculate price (example: $0.05 per credit for packages)
    from decimal import Decimal

    from lintpdf.api.models import TenantAICreditPackage

    price = Decimal(str(request.credits)) * Decimal("0.05")

    package = TenantAICreditPackage(
        tenant_id=tenant.id,
        credits_purchased=request.credits,
        credits_remaining=request.credits,
        price_paid=price,
    )
    db.add(package)
    db.commit()

    return CreditTopupResponse(
        package_id=package.id,
        credits_purchased=request.credits,
    )
