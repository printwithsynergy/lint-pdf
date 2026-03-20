"""Rate limiting using Redis counters with billable overage support."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from grounded.tenants.models import PLAN_LIMITS, RATE_LIMIT_WARN_THRESHOLD

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
