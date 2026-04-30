"""Stripe webhook dispatch for metered-resource fulfillment.

Handles:

* ``checkout.session.completed`` with ``metadata.lintpdf_kind`` ∈
  {"credits", "files"} — a tenant finished buying a pack. We insert
  a ``source='purchase'`` row in ``tenant_ai_credit_packages``,
  idempotent via the Stripe session id.

* ``invoice.paid`` on a subscription — plan billing succeeded. Grant
  the tenant's plan-monthly allotment for both kinds. Idempotent on
  ``(tenant_id, kind, billing_period_start)``.

The existing Stripe billing plugin (packages/stripe) handles the
subscription sync (plan changes, cancellations); this endpoint only
owns metered-resource grants so the two concerns don't tangle.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.database import get_db

if TYPE_CHECKING:
    from lintpdf.api.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/billing/stripe",
    tags=["x:saas-only", "billing-stripe"],
)


def _find_tenant(
    db: Session,
    *,
    metadata_tenant_id: str | None,
    stripe_customer_id: str | None,
    client_reference_id: str | None,
) -> Tenant | None:
    from lintpdf.api.models import Tenant

    for candidate in (metadata_tenant_id, client_reference_id):
        if candidate:
            try:
                tid = uuid.UUID(candidate)
            except ValueError:
                continue
            t = db.query(Tenant).filter(Tenant.id == tid).first()
            if t is not None:
                return t
    if stripe_customer_id:
        t = db.query(Tenant).filter(Tenant.stripe_customer_id == stripe_customer_id).first()
        if t is not None:
            return t
    return None


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Receive + verify Stripe webhook events.

    Unlike the other LintPDF endpoints this one accepts no API key —
    it's public and gated entirely by the Stripe-Signature header,
    which the engine verifies with the shared webhook secret. Any
    mismatch or missing header returns 400.
    """
    from lintpdf.billing.allocation import allocate_monthly, fulfill_purchase
    from lintpdf.billing.stripe_client import StripeError, verify_webhook_signature

    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        verify_webhook_signature(payload, sig)
    except StripeError as exc:
        logger.warning("Stripe webhook rejected: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body is not valid JSON",
        ) from exc

    event_type = event.get("type", "")
    data_object = (event.get("data") or {}).get("object", {}) or {}

    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata") or {}
        kind = metadata.get("lintpdf_kind")
        if kind not in ("credits", "files"):
            # Not ours — checkout for something else (subscription signup, etc.)
            return {"received": True, "handled": False, "reason": "foreign_checkout"}

        if data_object.get("payment_status") != "paid":
            return {"received": True, "handled": False, "reason": "not_paid"}

        pack_size = int(metadata.get("lintpdf_pack_size", 0))
        session_id = data_object.get("id") or ""
        price_cents = int(data_object.get("amount_total") or 0)

        tenant = _find_tenant(
            db,
            metadata_tenant_id=metadata.get("lintpdf_tenant_id"),
            stripe_customer_id=data_object.get("customer"),
            client_reference_id=data_object.get("client_reference_id"),
        )
        if tenant is None:
            logger.error("checkout.session.completed: tenant not resolved session=%s", session_id)
            # Returning 200 so Stripe stops retrying, but the ops alert is logged.
            return {"received": True, "handled": False, "reason": "tenant_not_found"}

        result = fulfill_purchase(
            tenant_id=tenant.id,
            kind=kind,
            pack_size=pack_size,
            price_cents=price_cents,
            stripe_session_id=session_id,
            db=db,
        )
        db.commit()
        return {
            "received": True,
            "handled": True,
            "event": event_type,
            "tenant_id": str(tenant.id),
            "package_id": str(result.package_id),
            "created": result.created,
        }

    if event_type == "invoice.paid":
        subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        # ``period_start`` on the invoice is the canonical billing
        # period anchor — dedupe keys on this.
        period_start_epoch = data_object.get("period_start")
        if not subscription_id or not customer_id or period_start_epoch is None:
            return {"received": True, "handled": False, "reason": "insufficient_invoice_data"}

        tenant = _find_tenant(
            db,
            metadata_tenant_id=None,
            stripe_customer_id=customer_id,
            client_reference_id=None,
        )
        if tenant is None:
            logger.warning("invoice.paid: tenant not resolved customer=%s", customer_id)
            return {"received": True, "handled": False, "reason": "tenant_not_found"}

        billing_period_start = datetime.fromtimestamp(int(period_start_epoch), tz=timezone.utc)
        grants: list[dict[str, Any]] = []
        for kind in ("credits", "files"):
            try:
                allocation = allocate_monthly(
                    tenant,
                    kind,  # type: ignore[arg-type]
                    db,
                    billing_period_start=billing_period_start,
                    source_event="invoice.paid",
                )
            except Exception:
                logger.exception("allocate_monthly failed tenant=%s kind=%s", tenant.id, kind)
                continue
            if allocation is not None:
                grants.append(
                    {
                        "kind": kind,
                        "amount": allocation.amount,
                        "created": allocation.created,
                        "package_id": str(allocation.package_id),
                    }
                )
        db.commit()
        return {
            "received": True,
            "handled": True,
            "event": event_type,
            "tenant_id": str(tenant.id),
            "grants": grants,
        }

    # Known-but-uninteresting events: 200 with no-op.
    return {"received": True, "handled": False, "reason": "unhandled_event_type"}
