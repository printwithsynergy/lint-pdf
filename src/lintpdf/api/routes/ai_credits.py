"""AI credit management endpoints."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/api/v1/ai/credits", tags=["x:saas-only", "ai-credits"])


def _app_base_url() -> str:
    from lintpdf.api.config import get_settings

    return get_settings().app_base_url.rstrip("/")


@router.get("/packages")
async def list_my_credit_packages(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, object]:
    """Return every AI-credit package for the authenticated tenant.

    Drives the "Package history" table on the tenant credits page.
    Doesn't require check_ai_access — customers should see their own
    history even if ai is disabled.
    """
    from sqlalchemy import desc

    from lintpdf.api.models import TenantAICreditPackage

    rows = (
        db.query(TenantAICreditPackage)
        .filter(
            TenantAICreditPackage.tenant_id == tenant.id,
            TenantAICreditPackage.kind == "credits",
        )
        .order_by(desc(TenantAICreditPackage.purchased_at))
        .all()
    )
    return {
        "packages": [
            {
                "id": str(p.id),
                "kind": p.kind,
                "source": p.source,
                "credits_purchased": p.credits_purchased,
                "credits_remaining": p.credits_remaining,
                "price_paid": float(p.price_paid) if p.price_paid is not None else 0.0,
                "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in rows
        ]
    }


@router.get("", response_model=CreditBalanceResponse)
async def get_credits(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
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


@router.post(
    "/topup",
    response_model=CreditTopupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def topup_credits(
    request: CreditTopupRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> CreditTopupResponse:
    """Create a Stripe Checkout session for a credit top-up purchase.

    The endpoint does NOT insert a package row. The package is only
    inserted when Stripe posts back ``checkout.session.completed`` to
    our webhook, which calls
    :py:func:`lintpdf.billing.allocation.fulfill_purchase`. This is
    the standard Stripe pattern — the server never trusts that the
    customer actually paid until Stripe says so.
    """
    from lintpdf.ai.access import check_ai_access
    from lintpdf.billing.metered_packs import pack_for_size, resolve_price_id
    from lintpdf.billing.stripe_client import (
        StripeError,
        create_checkout_session,
        load_config,
    )

    check_ai_access(tenant, db)

    cfg = load_config()
    pack_size = int(request.pack)
    defn = pack_for_size("credits", pack_size)
    if defn is None:
        # The Pydantic ``Literal`` already rejects unknown values, but
        # belt-and-suspenders since the catalogue is the source of truth.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown credit pack size: {pack_size}",
        )
    price_id = resolve_price_id(f"credits_{pack_size}", sandbox=cfg.sandbox)

    app_base = _app_base_url()
    success_url = os.environ.get(
        "LINTPDF_CHECKOUT_SUCCESS_URL",
        f"{app_base}/dashboard/account/ai/credits?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
    )
    cancel_url = os.environ.get(
        "LINTPDF_CHECKOUT_CANCEL_URL",
        f"{app_base}/dashboard/account/ai/credits?checkout=cancelled",
    )

    try:
        session = create_checkout_session(
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            customer=tenant.stripe_customer_id,
            customer_email=tenant.contact_email,
            client_reference_id=str(tenant.id),
            metadata={
                "lintpdf_kind": "credits",
                "lintpdf_pack_size": str(pack_size),
                "lintpdf_tenant_id": str(tenant.id),
            },
            config=cfg,
        )
    except StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe Checkout session creation failed: {exc}",
        ) from exc

    return CreditTopupResponse(
        checkout_url=session["url"],
        session_id=session["id"],
        pack_size=pack_size,
        usd_cents=defn.usd_cents,
    )
