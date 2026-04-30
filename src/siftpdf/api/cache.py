"""Lightweight Redis cache helpers.

The engine's ``_redis_state`` singleton (see ``siftpdf.api.middleware``)
is already wired up for rate limiting and idempotency. This module adds
a small on-top layer so routes that read stable tenant/brand-profile
rows dozens of times per second don't have to round-trip through
Postgres for every request.

Design choices:

* **JSON payloads only** — keeps the stored bytes language-agnostic and
  makes debugging trivial (``redis-cli GET <key>`` returns a readable
  string instead of a pickle blob). Non-JSON types must be pre-encoded
  by the caller.
* **Fail-open** — a missing/unreachable Redis is treated as a cache
  miss, never as an error. The engine's existing patterns fail-open
  everywhere (rate limiter, idempotency) and this mirrors that stance.
* **Short TTLs by default** — the expected use case is "cheap,
  readable copy" not "source of truth". 300 s (5 min) strikes a
  balance between DB pressure reduction and propagation of mutations.
* **Explicit invalidation** — mutating routes call
  :func:`invalidate` with the same key factory used by the read path.
  No "smart" cache dependency graph; easy to reason about.
"""

from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

from siftpdf.api.middleware import get_redis_client

logger = logging.getLogger(__name__)


DEFAULT_TTL_SECONDS = 300


def get_json(key: str) -> Any | None:
    """Return the cached JSON value for ``key`` or None on miss/failure."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception:
        logger.exception("cache.get failed for key=%s", key)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        logger.warning("cache.get corrupt payload for key=%s — deleting", key)
        with contextlib.suppress(Exception):
            client.delete(key)
        return None


def set_json(key: str, value: Any, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    """Store ``value`` under ``key`` with a TTL. Silent on failure."""
    client = get_redis_client()
    if client is None:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        logger.exception("cache.set failed for key=%s", key)


def invalidate(*keys: str) -> None:
    """Delete one or more cache keys. Silent on failure."""
    client = get_redis_client()
    if client is None or not keys:
        return
    try:
        client.delete(*keys)
    except Exception:
        logger.exception("cache.invalidate failed for keys=%s", keys)


# ---------------------------------------------------------------------------
# Domain-specific key factories
# ---------------------------------------------------------------------------


def brand_profile_key(tenant_id: str, profile_id: str) -> str:
    return f"brand_profile:{tenant_id}:{profile_id}"


def tenant_branding_key(tenant_id: str) -> str:
    return f"tenant_branding:{tenant_id}"
