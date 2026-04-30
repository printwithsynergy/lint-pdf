"""Redis cache for tenant Pantone overrides.

Provides a fast lookup layer between PostgreSQL (source of truth) and Celery
workers that need tenant-specific Pantone color data during job processing.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "pantone_overrides:"
_CACHE_TTL = 3600  # 1 hour


def _cache_key(tenant_id: str) -> str:
    return f"{_CACHE_PREFIX}{tenant_id}"


def get_overrides(redis_client: Any, tenant_id: str) -> dict[str, dict[str, Any]] | None:
    """Get tenant Pantone overrides from Redis cache.

    Returns the cached dict on hit, or ``None`` on miss / error so the
    caller can fall back to the database.
    """
    if redis_client is None:
        return None
    try:
        data = redis_client.get(_cache_key(tenant_id))
        if data:
            return json.loads(data)  # type: ignore[no-any-return]
        return None
    except Exception:
        logger.debug("Redis cache miss for pantone overrides: %s", tenant_id, exc_info=True)
        return None


def set_overrides(
    redis_client: Any,
    tenant_id: str,
    overrides: dict[str, dict[str, Any]],
) -> None:
    """Cache tenant Pantone overrides in Redis with TTL."""
    if redis_client is None:
        return
    try:
        redis_client.setex(_cache_key(tenant_id), _CACHE_TTL, json.dumps(overrides))
    except Exception:
        logger.debug("Failed to cache pantone overrides for %s", tenant_id, exc_info=True)


def invalidate(redis_client: Any, tenant_id: str) -> None:
    """Remove cached overrides — call on update or delete."""
    if redis_client is None:
        return
    try:
        redis_client.delete(_cache_key(tenant_id))
    except Exception:
        logger.debug("Failed to invalidate pantone cache for %s", tenant_id, exc_info=True)
