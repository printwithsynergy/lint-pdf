"""Webhook management endpoints."""

from __future__ import annotations

import ipaddress
import secrets
import uuid as uuid_mod
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import Tenant, WebhookDelivery, WebhookEndpoint
from lintpdf.api.schemas import (
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdateRequest,
)
from lintpdf.webhooks.dispatcher import WebhookDispatcher


class WebhookTestResponse(BaseModel):
    """Response from a webhook test delivery."""

    success: bool
    status_code: int = 0
    error: str = ""
    event: str = "test.ping"


router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Private/reserved IP ranges that webhook URLs must not resolve to
_BLOCKED_HOSTNAMES = frozenset(
    {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "metadata.google.internal"}
)


def _validate_webhook_url(url: str) -> None:
    """Validate a webhook URL is safe (not SSRF target)."""
    parsed = urlparse(url)

    if parsed.scheme not in ("https",):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Webhook URL must use HTTPS.",
        )

    hostname = parsed.hostname or ""

    if hostname in _BLOCKED_HOSTNAMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Webhook URL must not point to private/local addresses.",
        )

    # Block private IP ranges
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Webhook URL must not point to private/local addresses.",
            )
    except ValueError:
        pass  # Not an IP literal — hostname is fine


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: WebhookCreateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WebhookResponse:
    """Register a new webhook endpoint."""
    from lintpdf.tenants.entitlements import resolve_entitlements

    entitlements = resolve_entitlements(tenant)

    if not entitlements.webhooks_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhooks (Tower Alerts) require Growth plan or above.",
        )

    # Enforce max webhook count
    existing_count = (
        db.query(WebhookEndpoint).filter(WebhookEndpoint.tenant_id == tenant.id).count()
    )
    if existing_count >= entitlements.max_webhooks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Webhook limit reached ({entitlements.max_webhooks}). Upgrade your plan for more.",
        )

    _validate_webhook_url(request.url)

    webhook = WebhookEndpoint(
        id=uuid_mod.uuid4(),
        tenant_id=tenant.id,
        url=request.url,
        events=request.events,
        secret=secrets.token_urlsafe(32),
        is_active=True,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        created_at=webhook.created_at,
    )


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WebhookListResponse:
    """List all registered webhook endpoints for the current tenant."""
    endpoints: list[WebhookEndpoint] = (
        db.query(WebhookEndpoint).filter(WebhookEndpoint.tenant_id == tenant.id).all()
    )
    return WebhookListResponse(
        webhooks=[
            WebhookResponse(
                id=e.id,
                url=e.url,
                events=e.events,
                is_active=e.is_active,
                created_at=e.created_at,
            )
            for e in endpoints
        ]
    )


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WebhookResponse:
    """Update a webhook endpoint (URL, events, or active status)."""
    try:
        uid = uuid_mod.UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid webhook ID format.",
        ) from exc

    endpoint: WebhookEndpoint | None = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.id == uid, WebhookEndpoint.tenant_id == tenant.id)
        .first()
    )
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found.",
        )

    if request.url is not None:
        _validate_webhook_url(request.url)
        endpoint.url = request.url

    if request.events is not None:
        endpoint.events = request.events

    if request.is_active is not None:
        endpoint.is_active = request.is_active

    db.commit()
    db.refresh(endpoint)

    return WebhookResponse(
        id=endpoint.id,
        url=endpoint.url,
        events=endpoint.events,
        is_active=endpoint.is_active,
        created_at=endpoint.created_at,
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    """Remove a webhook endpoint."""
    try:
        uid = uuid_mod.UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid webhook ID format.",
        ) from exc

    endpoint: WebhookEndpoint | None = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.id == uid, WebhookEndpoint.tenant_id == tenant.id)
        .first()
    )
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found.",
        )

    db.delete(endpoint)
    db.commit()


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WebhookTestResponse:
    """Send a test payload to a webhook endpoint to verify connectivity."""
    try:
        uid = uuid_mod.UUID(webhook_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid webhook ID format.",
        ) from exc

    endpoint: WebhookEndpoint | None = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.id == uid, WebhookEndpoint.tenant_id == tenant.id)
        .first()
    )
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook '{webhook_id}' not found.",
        )

    test_payload = {
        "event": "test.ping",
        "job_id": "00000000-0000-0000-0000-000000000000",
        "tenant_id": str(tenant.id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test": True,
        "message": "This is a test webhook delivery from LintPDF.",
    }

    dispatcher = WebhookDispatcher(max_retries=0, timeout=10.0)
    result = dispatcher.deliver(
        url=endpoint.url,
        secret=endpoint.secret,
        event="test.ping",
        payload=test_payload,
    )

    return WebhookTestResponse(
        success=result.success,
        status_code=result.status_code,
        error=result.error,
        event="test.ping",
    )


# ---------------------------------------------------------------------------
# Delivery audit + replay
# ---------------------------------------------------------------------------


class WebhookDeliveryResponse(BaseModel):
    """One row from the webhook delivery audit log."""

    id: str
    webhook_id: str
    event: str
    url: str
    attempt_count: int
    final_status_code: int
    success: bool
    last_error: str | None = None
    created_at: str
    delivered_at: str | None = None


class WebhookDeliveryDetail(WebhookDeliveryResponse):
    """Delivery row + the exact signed payload we POSTed."""

    payload: dict


class WebhookDeliveryListResponse(BaseModel):
    deliveries: list[WebhookDeliveryResponse]
    total: int
    page: int
    page_size: int


def _row_to_summary(d: WebhookDelivery) -> WebhookDeliveryResponse:
    return WebhookDeliveryResponse(
        id=str(d.id),
        webhook_id=str(d.webhook_id),
        event=d.event,
        url=d.url,
        attempt_count=d.attempt_count,
        final_status_code=d.final_status_code,
        success=d.success,
        last_error=d.last_error,
        created_at=d.created_at.isoformat(),
        delivered_at=d.delivered_at.isoformat() if d.delivered_at else None,
    )


@router.get("/deliveries", response_model=WebhookDeliveryListResponse)
async def list_deliveries(
    webhook_id: str | None = None,
    event: str | None = None,
    success: bool | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WebhookDeliveryListResponse:
    """List webhook delivery attempts for the authenticated tenant.

    Newest first. Filter by ``webhook_id``, ``event``, or
    ``success=false`` to narrow in on failures. Paginates via
    ``?page=`` + ``?page_size=`` (default 50, capped at 200).
    """
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 200:
        page_size = 50

    query = db.query(WebhookDelivery).filter(WebhookDelivery.tenant_id == tenant.id)
    if webhook_id:
        try:
            wid = uuid_mod.UUID(webhook_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid webhook_id UUID.",
            ) from None
        query = query.filter(WebhookDelivery.webhook_id == wid)
    if event:
        query = query.filter(WebhookDelivery.event == event)
    if success is not None:
        query = query.filter(WebhookDelivery.success.is_(success))

    total = query.count()
    rows = (
        query.order_by(WebhookDelivery.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return WebhookDeliveryListResponse(
        deliveries=[_row_to_summary(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/deliveries/{delivery_id}", response_model=WebhookDeliveryDetail)
async def get_delivery(
    delivery_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WebhookDeliveryDetail:
    """Fetch one delivery row + the exact signed payload we POSTed."""
    try:
        did = uuid_mod.UUID(delivery_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        ) from None
    row = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.id == did, WebhookDelivery.tenant_id == tenant.id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        )
    summary = _row_to_summary(row)
    return WebhookDeliveryDetail(**summary.model_dump(), payload=row.payload)


@router.post(
    "/deliveries/{delivery_id}/replay",
    response_model=WebhookDeliveryDetail,
    status_code=status.HTTP_201_CREATED,
)
async def replay_delivery(
    delivery_id: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> WebhookDeliveryDetail:
    """Re-fire a previously-recorded delivery against its original URL.

    Creates a NEW ``WebhookDelivery`` row with the same event + payload
    so the audit log grows rather than mutating history. The endpoint's
    current secret signs the replayed body (if it was rotated since
    the original attempt, the replay will sign with the new secret --
    callers who rotate secrets lose replayability of older bodies,
    which is the expected security tradeoff).
    """
    try:
        did = uuid_mod.UUID(delivery_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        ) from None
    original = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.id == did, WebhookDelivery.tenant_id == tenant.id)
        .first()
    )
    if original is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found.",
        )
    endpoint = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.id == original.webhook_id)
        .first()
    )
    if endpoint is None or not endpoint.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot replay: webhook endpoint is inactive or deleted.",
        )

    new_row = WebhookDelivery(
        id=uuid_mod.uuid4(),
        webhook_id=endpoint.id,
        tenant_id=tenant.id,
        event=original.event,
        payload=original.payload,
        url=endpoint.url,
        attempt_count=0,
        final_status_code=0,
        success=False,
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)

    # Queue async dispatch. Errors here are logged but don't rollback
    # the audit row -- "we attempted a replay" is worth preserving.
    try:
        from lintpdf.queue.tasks import dispatch_webhook

        dispatch_webhook.delay(  # type: ignore[attr-defined]
            webhook_url=endpoint.url,
            webhook_secret=endpoint.secret,
            event=original.event,
            payload=original.payload,
            delivery_id=str(new_row.id),
        )
    except Exception:
        import logging as _logging

        _logging.getLogger(__name__).exception(
            "replay_delivery: failed to queue dispatch for %s", new_row.id
        )

    summary = _row_to_summary(new_row)
    return WebhookDeliveryDetail(**summary.model_dump(), payload=new_row.payload)
