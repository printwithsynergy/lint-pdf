"""File-pack purchase + balance endpoints.

Mirrors :mod:`siftpdf.api.routes.ai_credits` for the file-quota side
of the metered-resource system. Both kinds share the allocator and
webhook handler — only the endpoint surface is doubled so customers
see "Buy AI credits" and "Buy file packs" as distinct affordances.
"""

from __future__ import annotations

import os
import uuid  # noqa: TC003
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from siftpdf.api.ai_schemas import FileTopupRequest, FileTopupResponse
from siftpdf.api.auth import get_current_tenant
from siftpdf.api.database import get_db

if TYPE_CHECKING:
    from siftpdf.api.models import Tenant

router = APIRouter(prefix="/api/v1/files", tags=["x:saas-only", "file-packs"])


class FileQuotaResponse(BaseModel):
    """Balance snapshot for the metered file quota."""

    tenant_id: uuid.UUID
    total_remaining: int
    monthly_allotment_remaining: int
    purchased_remaining: int
    active_packages: int
    monthly_allotment: int  # plan default or override, not the remainder


def _app_base_url() -> str:
    from siftpdf.api.config import get_settings

    return get_settings().app_base_url.rstrip("/")


@router.get("/packages")
async def list_my_file_packages(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, object]:
    """Every file pack for the authenticated tenant (history table)."""
    from sqlalchemy import desc

    from siftpdf.api.models import TenantAICreditPackage

    rows = (
        db.query(TenantAICreditPackage)
        .filter(
            TenantAICreditPackage.tenant_id == tenant.id,
            TenantAICreditPackage.kind == "files",
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


@router.get("/quota", response_model=FileQuotaResponse)
async def get_quota(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> FileQuotaResponse:
    """Current file-quota balance + this month's allotment."""
    from siftpdf.billing.file_quota import get_file_quota_balance
    from siftpdf.tenants.entitlements import resolve_entitlements

    bal = get_file_quota_balance(tenant.id, db)
    ents = resolve_entitlements(tenant)
    return FileQuotaResponse(
        tenant_id=bal.tenant_id,
        total_remaining=bal.total_remaining,
        monthly_allotment_remaining=bal.monthly_allotment_remaining,
        purchased_remaining=bal.purchased_remaining,
        active_packages=bal.active_packages,
        monthly_allotment=ents.monthly_files_included,
    )


@router.post(
    "/topup",
    response_model=FileTopupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def topup_files(
    request: FileTopupRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> FileTopupResponse:
    """Create a Stripe Checkout session for a file-pack purchase."""
    from siftpdf.billing.metered_packs import pack_for_size, resolve_price_id
    from siftpdf.billing.stripe_client import (
        StripeError,
        create_checkout_session,
        load_config,
    )

    cfg = load_config()
    pack_size = int(request.pack)
    defn = pack_for_size("files", pack_size)
    if defn is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown file pack size: {pack_size}",
        )
    price_id = resolve_price_id(f"files_{pack_size}", sandbox=cfg.sandbox)

    app_base = _app_base_url()
    success_url = os.environ.get(
        "LINTPDF_CHECKOUT_SUCCESS_URL",
        f"{app_base}/dashboard/account/billing/files?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
    )
    cancel_url = os.environ.get(
        "LINTPDF_CHECKOUT_CANCEL_URL",
        f"{app_base}/dashboard/account/billing/files?checkout=cancelled",
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
                "lintpdf_kind": "files",
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

    return FileTopupResponse(
        checkout_url=session["url"],
        session_id=session["id"],
        pack_size=pack_size,
        usd_cents=defn.usd_cents,
    )
