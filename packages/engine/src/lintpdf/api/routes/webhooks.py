"""Webhook management endpoints."""

from __future__ import annotations

import ipaddress
import secrets
import uuid as uuid_mod
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import Tenant, WebhookEndpoint
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
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
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
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
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
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
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
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
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
    db: Session = Depends(get_db),  # noqa: B008
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
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
        "timestamp": datetime.now(UTC).isoformat(),
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
