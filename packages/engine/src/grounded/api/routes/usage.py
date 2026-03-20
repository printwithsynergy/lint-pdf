"""Usage and rate limit status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from grounded.api.auth import get_current_tenant
from grounded.api.middleware import build_usage_info, get_current_usage
from grounded.api.models import Tenant  # noqa: TC001 — needed at runtime by FastAPI

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


class UsageResponse(BaseModel):
    """Current daily usage for the authenticated tenant."""

    plan: str
    used: int
    limit: int
    remaining_included: int
    percentage: int
    in_overage: bool
    overage_count: int
    overage_rate_cents: int
    overage_cost_cents: int
    overage_enabled: bool
    overage_cap_cents: int | None
    cap_remaining_cents: int | None
    blocked: bool
    warning: bool


@router.get("", response_model=UsageResponse)
async def get_usage(
    tenant: Tenant = Depends(get_current_tenant),  # noqa: B008
) -> UsageResponse:
    """Get current daily rate limit usage for the authenticated tenant."""
    current = get_current_usage(tenant)
    usage = build_usage_info(tenant, current)

    return UsageResponse(
        plan=tenant.plan.value if hasattr(tenant.plan, "value") else str(tenant.plan),
        used=usage.used,
        limit=usage.limit,
        remaining_included=usage.remaining_included,
        percentage=usage.percentage,
        in_overage=usage.in_overage,
        overage_count=usage.overage_count,
        overage_rate_cents=usage.overage_rate_cents,
        overage_cost_cents=usage.overage_cost_cents,
        overage_enabled=usage.overage_enabled,
        overage_cap_cents=usage.overage_cap_cents,
        cap_remaining_cents=usage.cap_remaining_cents,
        blocked=usage.blocked,
        warning=usage.warning,
    )
