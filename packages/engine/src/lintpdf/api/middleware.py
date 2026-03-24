"""Rate limiting using Redis counters with billable overage support.

Also provides idempotency key middleware and rate limit response headers.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from lintpdf.tenants.models import PLAN_LIMITS, RATE_LIMIT_WARN_THRESHOLD

logger = logging.getLogger(__name__)

# Module-level container — set via configure_rate_limiter()
_redis_state: dict[str, Any] = {"client": None}
_redis_lock = threading.Lock()


def configure_rate_limiter(redis_url: str) -> None:
    """Initialize the Redis client for rate limiting.

    Args:
        redis_url: Redis connection URL (e.g. redis://localhost:6379/0).
    """
    with _redis_lock:
        if _redis_state["client"] is not None:
            return
        import redis

        _redis_state["client"] = redis.Redis.from_url(redis_url, decode_responses=True)


def set_rate_limiter(client: Any) -> None:
    """Override the Redis client (for testing)."""
    _redis_state["client"] = client


def get_redis_client() -> Any:
    """Return the current Redis client (or None if not configured)."""
    return _redis_state["client"]


# Lua script for atomic increment + expire (avoids TOCTOU race on TTL)
_INCR_WITH_TTL_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


@dataclass
class UsageInfo:
    """Current rate limit usage for a tenant."""

    used: int
    limit: int
    percentage: int
    in_overage: bool
    overage_count: int
    overage_rate_cents: int
    overage_cost_cents: int
    overage_enabled: bool
    overage_cap_cents: int | None
    blocked: bool

    @property
    def remaining_included(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def cap_remaining_cents(self) -> int | None:
        if self.overage_cap_cents is None:
            return None
        return max(0, self.overage_cap_cents - self.overage_cost_cents)

    @property
    def warning(self) -> bool:
        return self.percentage >= RATE_LIMIT_WARN_THRESHOLD and not self.blocked


def get_current_usage(tenant: Any) -> int:
    """Read the current daily usage count without incrementing.

    Args:
        tenant: Tenant model instance.

    Returns:
        Current usage count, or 0 if Redis unavailable.
    """
    if _redis_state["client"] is None:
        return 0

    tenant_id = str(tenant.id)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    rate_key = f"rate:{tenant_id}:{today}"

    try:
        val = _redis_state["client"].get(rate_key)
        return int(val) if val is not None else 0
    except Exception:
        logger.exception("Failed to read usage from Redis")
        return 0


def build_usage_info(tenant: Any, current: int) -> UsageInfo:
    """Build a UsageInfo from a tenant and current count."""
    limit = tenant.rate_limit_daily
    plan = getattr(tenant, "plan", None)

    rate_cents = 0
    if plan is not None:
        rate_cents = PLAN_LIMITS.get(plan, {}).get("overage_rate_cents", 0)
    # Allow per-tenant override
    override = getattr(tenant, "overage_rate_override_cents", None)
    if override is not None:
        rate_cents = override

    overage_enabled = getattr(tenant, "overage_enabled", False)
    overage_cap = getattr(tenant, "overage_cap_cents", None)

    pct = int((current / limit) * 100) if limit > 0 else 100
    in_overage = current > limit
    overage_count = max(0, current - limit)
    overage_cost = overage_count * rate_cents

    # Determine if blocked
    if current <= limit:
        blocked = False
    elif not overage_enabled or rate_cents == 0:
        # No overages allowed — hard block at limit
        blocked = True
    elif overage_cap is not None and overage_cost > overage_cap:
        # Spending cap exceeded
        blocked = True
    else:
        blocked = False

    return UsageInfo(
        used=current,
        limit=limit,
        percentage=pct,
        in_overage=in_overage,
        overage_count=overage_count,
        overage_rate_cents=rate_cents,
        overage_cost_cents=overage_cost,
        overage_enabled=overage_enabled,
        overage_cap_cents=overage_cap,
        blocked=blocked,
    )


def check_rate_limit(tenant: Any) -> UsageInfo | None:
    """Check rate limit for a tenant. Raises HTTPException(429) if blocked.

    Paid plans with overage_enabled=True can exceed their daily limit and
    pay per-job at overage_rate_cents. An optional spending cap blocks
    when total overage cost exceeds overage_cap_cents.

    Free plans and tenants without overage enabled are hard-blocked at 100%.

    Args:
        tenant: Authenticated Tenant model instance.

    Returns:
        UsageInfo with current usage, or None if Redis not configured.

    Raises:
        HTTPException: 429 if blocked.
    """
    if _redis_state["client"] is None:
        return None

    tenant_id = str(tenant.id)
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    rate_key = f"rate:{tenant_id}:{today}"

    try:
        current = _redis_state["client"].eval(_INCR_WITH_TTL_SCRIPT, 1, rate_key, 86400)
        usage = build_usage_info(tenant, current)

        if usage.blocked:
            if (
                usage.overage_cap_cents is not None
                and usage.overage_cost_cents > usage.overage_cap_cents
            ):
                detail = "Daily overage spending cap reached."
            elif usage.overage_enabled:
                detail = "Daily rate limit exceeded."
            else:
                detail = "Daily rate limit exceeded."

            logger.warning(
                "Rate limit blocked tenant %s: %d/%d (overage_enabled=%s)",
                tenant_id,
                current,
                usage.limit,
                usage.overage_enabled,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
                headers={
                    "X-RateLimit-Limit": str(usage.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Used": str(usage.used),
                    "Retry-After": "86400",
                },
            )

        if usage.in_overage:
            logger.info(
                "Tenant %s in billable overage: %d/%d (cost: %d cents)",
                tenant_id,
                current,
                usage.limit,
                usage.overage_cost_cents,
            )

        return usage

    except HTTPException:
        raise
    except Exception:
        logger.exception("Rate limiter error — allowing request through")
        return None


# ---------------------------------------------------------------------------
# Rate limit response headers
# ---------------------------------------------------------------------------


def attach_rate_limit_headers(response: Response, usage: UsageInfo) -> None:
    """Attach standard rate limit headers to an HTTP response.

    Headers set:
        X-RateLimit-Limit: The tenant's daily request limit.
        X-RateLimit-Remaining: Remaining requests within the included quota.
        X-RateLimit-Reset: UTC epoch timestamp when the current window resets
                           (midnight UTC of the next day).
    """
    # Compute seconds until midnight UTC
    now = datetime.now(UTC)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Move to next day
    tomorrow = tomorrow.replace(day=now.day + 1) if now.day < 28 else tomorrow  # rough
    # Safer: use timedelta
    from datetime import timedelta

    end_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    reset_epoch = int(end_of_day.timestamp())

    response.headers["X-RateLimit-Limit"] = str(usage.limit)
    response.headers["X-RateLimit-Remaining"] = str(usage.remaining_included)
    response.headers["X-RateLimit-Reset"] = str(reset_epoch)


# ---------------------------------------------------------------------------
# Idempotency key middleware
# ---------------------------------------------------------------------------

_IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours


def _idempotency_cache_key(tenant_id: str, idempotency_key: str) -> str:
    """Build the Redis key for an idempotency entry."""
    return f"idempotency:{tenant_id}:{idempotency_key}"


def _serialize_response(status_code: int, body: bytes, headers: dict[str, str]) -> str:
    """Serialize a response to JSON for caching."""
    return json.dumps(
        {
            "status_code": status_code,
            "body": body.decode("utf-8", errors="replace"),
            "headers": headers,
        }
    )


def _deserialize_response(data: str) -> dict[str, Any]:
    """Deserialize a cached response from JSON."""
    return json.loads(data)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that enforces idempotency for POST requests.

    When a request includes an ``Idempotency-Key`` header the middleware:

    1. Checks Redis for a cached result under ``idempotency:{tenant_id}:{key}``.
    2. If found, returns the cached response without re-executing the endpoint.
    3. If not found, processes the request normally and caches the result
       for 24 hours.

    Requests without the header are passed through unchanged.  Non-POST
    methods are always passed through (GET, PUT, DELETE, etc.).

    The tenant ID is read from ``request.state.tenant_id``.  If the tenant
    ID is not set (e.g., unauthenticated requests), the middleware passes
    through without caching.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only apply to POST requests
        if request.method != "POST":
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        # Require tenant context
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is None:
            return await call_next(request)

        tenant_id = str(tenant_id)
        redis_client = get_redis_client()
        if redis_client is None:
            # No Redis available — pass through
            return await call_next(request)

        cache_key = _idempotency_cache_key(tenant_id, idempotency_key)

        # Check for cached result
        try:
            cached = redis_client.get(cache_key)
        except Exception:
            logger.exception("Idempotency cache read failed — processing request")
            cached = None

        if cached is not None:
            data = _deserialize_response(cached)
            return Response(
                content=data["body"],
                status_code=data["status_code"],
                headers=data.get("headers", {}),
            )

        # Process the request
        response = await call_next(request)

        # Read the response body for caching
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            if isinstance(chunk, str):
                body_chunks.append(chunk.encode("utf-8"))
            else:
                body_chunks.append(chunk)
        body = b"".join(body_chunks)

        # Cache the result
        resp_headers = dict(response.headers)
        serialized = _serialize_response(response.status_code, body, resp_headers)
        try:
            redis_client.setex(cache_key, _IDEMPOTENCY_TTL_SECONDS, serialized)
        except Exception:
            logger.exception("Idempotency cache write failed")

        # Return a new response since we consumed the body iterator
        return Response(
            content=body,
            status_code=response.status_code,
            headers=resp_headers,
        )
