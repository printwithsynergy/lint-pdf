"""Authentication and authorization for Grounded API."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.database import get_db
from lintpdf.api.models import ApiKey, Tenant

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


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


def _resolve_tenant_by_key(db: Session, key_hash: str) -> Tenant | None:
    """Look up a tenant by API key hash.

    Checks the ApiKey table first (supports multiple keys per tenant with
    rotation), then falls back to the legacy Tenant.api_key_hash column
    for backward compatibility.
    """
    # Try ApiKey table first (multi-key support)
    api_key_row: ApiKey | None = (
        db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)).first()
    )
    if api_key_row is not None:
        api_key_row.last_used_at = datetime.now(UTC)
        tenant = db.query(Tenant).filter(Tenant.id == api_key_row.tenant_id).first()
        if tenant is not None:
            db.commit()
            return tenant

    # Fall back to legacy Tenant.api_key_hash
    return db.query(Tenant).filter(Tenant.api_key_hash == key_hash).first()


async def get_current_tenant(
    authorization: str | None = Security(_api_key_header),
    db: Session = Depends(get_db),  # noqa: B008
) -> Tenant:
    """Extract and validate the API key from the Authorization header.

    Expects: Authorization: Bearer <api_key>

    Checks both the ApiKey table (multi-key rotation) and the legacy
    Tenant.api_key_hash column for backward compatibility.

    Args:
        authorization: Raw Authorization header value.
        db: Database session (injected by FastAPI).

    Returns:
        The authenticated Tenant.

    Raises:
        HTTPException: 401 if key is missing/invalid, 403 if tenant inactive.
    """
    api_key = _extract_api_key(authorization)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide Authorization: Bearer <api_key>",
        )

    key_hash = hash_api_key(api_key)
    tenant = _resolve_tenant_by_key(db, key_hash)

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
) -> Tenant | None:
    """Optionally authenticate a tenant from the Authorization header.

    Returns None instead of raising 401 when no key is provided or the key
    is invalid. Useful for endpoints that provide richer responses to
    authenticated callers but still work without auth.
    """
    api_key = _extract_api_key(authorization)
    if api_key is None:
        return None

    key_hash = hash_api_key(api_key)
    tenant = _resolve_tenant_by_key(db, key_hash)

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
