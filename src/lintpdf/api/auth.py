"""Authentication and authorization for LintPDF API."""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.database import get_db
from lintpdf.services.tenant_context import (
    TenantContext,
    get_tenant_context_service,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

# Sentinel tenant returned when ``LINTPDF_AUTH_MODE=open``. The id is
# fixed so logs / decision audit trails attribute every open-mode call
# to the same synthetic tenant rather than minting a fresh UUID per
# request. Plan is intentionally non-billing — quota gates that read
# ``plan`` route through the OSS-friendly path. ``rate_limit_daily``
# defaults to 0 on ``TenantContext`` (which the daily-rate middleware
# treats as "no allowance"); we override to 1_000_000 so open-mode
# deploys aren't blocked the moment they ship the first request. Hosts
# that want a tighter cap can wrap ``get_current_tenant`` themselves.
_OSS_OPEN_TENANT = TenantContext(
    id=uuid.UUID("00000000-0000-0000-0000-00000000050a"),
    name="OSS open-mode",
    is_active=True,
    plan="oss",
    rate_limit_daily=1_000_000,
    max_file_size_mb=1024,
)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return f"lpdf_{secrets.token_urlsafe(32)}"


def _extract_api_key(authorization: str | None) -> str | None:
    """Extract the raw API key from an Authorization header value.

    Returns None if the header is missing or empty.
    """
    if not authorization:
        return None
    api_key = authorization
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:]
    return api_key or None


async def get_current_tenant(
    authorization: str | None = Security(_api_key_header),
    db: Session = Depends(get_db),  # noqa: B008
) -> TenantContext:
    """Extract and validate the API key from the Authorization header.

    Expects: Authorization: Bearer <api_key>

    Dispatches through :class:`TenantContextService` so the OSS engine
    never imports the SaaS-only ``Tenant`` ORM. The service's SaaS impl
    walks the ``ApiKey`` + ``Tenant`` tables (with ``last_used_at`` write
    side-effect); OSS default returns ``None`` so OSS-only deploys
    must install their own auth service.

    When ``LINTPDF_AUTH_MODE=open`` the API key check is bypassed and a
    built-in OSS sentinel tenant is returned. Use only on deployments
    where access is gated upstream.

    Args:
        authorization: Raw Authorization header value.
        db: Database session (injected by FastAPI).

    Returns:
        The authenticated tenant's context snapshot.

    Raises:
        HTTPException: 401 if key is missing/invalid, 403 if tenant inactive.
    """
    from lintpdf.api.config import get_settings

    if get_settings().auth_mode == "open":
        return _OSS_OPEN_TENANT

    api_key = _extract_api_key(authorization)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide Authorization: Bearer <api_key>",
        )

    key_hash = hash_api_key(api_key)
    tenant = get_tenant_context_service().load_by_api_key_hash(key_hash, db)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive.",
        )

    return tenant


async def get_optional_tenant(
    authorization: str | None = Security(_api_key_header),
    db: Session = Depends(get_db),  # noqa: B008
) -> TenantContext | None:
    """Optionally authenticate a tenant from the Authorization header.

    Returns None instead of raising 401 when no key is provided or the key
    is invalid. Useful for endpoints that provide richer responses to
    authenticated callers but still work without auth.

    When ``LINTPDF_AUTH_MODE=open`` the OSS sentinel tenant is returned
    instead of None, so optional-auth endpoints behave as if the caller
    were authenticated.
    """
    from lintpdf.api.config import get_settings

    if get_settings().auth_mode == "open":
        return _OSS_OPEN_TENANT

    api_key = _extract_api_key(authorization)
    if api_key is None:
        return None

    key_hash = hash_api_key(api_key)
    tenant = get_tenant_context_service().load_by_api_key_hash(key_hash, db)

    if tenant is None or not tenant.is_active:
        return None

    return tenant


def verify_admin_key(x_admin_key: str | None = Header(None)) -> str:
    """Verify the admin API key from the X-Admin-Key header.

    Args:
        x_admin_key: Raw X-Admin-Key header value.

    Returns:
        The validated admin key string.

    Raises:
        HTTPException: 503 if admin key not configured, 401 if invalid.
    """
    from lintpdf.api.config import get_settings

    settings = get_settings()
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API not configured.",
        )
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key.",
        )
    return x_admin_key


def is_admin_request(x_admin_key: str | None) -> bool:
    """Soft variant of :func:`verify_admin_key` — returns True/False
    without raising. Used by routes that accept both tenant and admin
    auth (PR B Slot 2B's submit-with-admin-override path).
    """
    if not x_admin_key:
        return False
    from lintpdf.api.config import get_settings

    settings = get_settings()
    return bool(settings.admin_api_key) and x_admin_key == settings.admin_api_key
    return x_admin_key


def require_any_auth(*strategies: Callable[..., Any]) -> Callable[..., Any]:
    """Create a dependency that tries multiple auth strategies in order.

    The first strategy that returns a non-None result wins.
    If all strategies raise HTTPException or return None, raises 401.

    Usage::

        @router.get("/something")
        async def something(
            auth=Depends(require_any_auth(get_current_tenant, verify_admin_key)),
        ):
            ...
    """

    async def _try_strategies(
        authorization: str | None = Security(_api_key_header),
        x_admin_key: str | None = Header(None),
        db: Session = Depends(get_db),  # noqa: B008
    ) -> Any:
        for strategy in strategies:
            try:
                if strategy is get_current_tenant or strategy is get_optional_tenant:
                    result = await strategy(authorization=authorization, db=db)
                elif strategy is verify_admin_key:
                    result = strategy(x_admin_key=x_admin_key)
                else:
                    result = strategy()
                if result is not None:
                    return result
            except HTTPException:
                continue
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return _try_strategies
