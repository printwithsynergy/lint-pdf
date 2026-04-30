"""Q-E7 — per-tenant LLM cost-cap enforcement.

The cap is configured via the unified-config ``ai_cost_cap`` toggle
(seeded by PR-B1) at TENANT scope only. Shape of the override value::

    {
        "enabled": bool,           # off by default
        "monthly_cap_cents": int,  # ceiling per calendar month (UTC)
        "alert_threshold_pct": int # informational; 0-100
    }

Enforcement model:

* :func:`check_cap_or_raise` reads the toggle, sums the tenant's
  ``ai_usage_logs.cost_cents`` for the current calendar month, and
  raises :class:`CostCapExceededError` when adding the *projected*
  cost of the upcoming call would push past the cap.
* Off-by-default: when the override is missing, malformed, or
  ``enabled=false`` this function is a no-op so existing
  deployments behave exactly as before until an operator opts in.
* Defensive: any DB error degrades to **fail-open** (the call
  proceeds) rather than blocking customer work on a metering hiccup.
  The cap is a budget guard rail, not an auth check.

Callers wrap every Claude / Anthropic dispatch with
``check_cap_or_raise(db, tenant_id, projected_cost_cents=…)``
*before* the network round trip. The existing ``record_usage`` call
*after* the LLM responds keeps the running total honest for the
next call's check.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

if TYPE_CHECKING:
    import uuid as uuid_mod

    from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)


CAP_TOGGLE_ID = "ai_cost_cap"


class CostCapExceededError(Exception):
    """Raised when an LLM dispatch would push past the tenant's cap.

    Carries the cap + current spend so callers can surface a
    user-readable error or 402.
    """

    def __init__(
        self,
        *,
        tenant_id: uuid_mod.UUID,
        cap_cents: int,
        used_cents: int,
        projected_cents: int,
    ) -> None:
        self.tenant_id = tenant_id
        self.cap_cents = cap_cents
        self.used_cents = used_cents
        self.projected_cents = projected_cents
        super().__init__(
            f"tenant {tenant_id} LLM cost cap exceeded: "
            f"used={used_cents}c + projected={projected_cents}c "
            f"would exceed cap={cap_cents}c"
        )


def _load_cap_config(db: Session, tenant_id: uuid_mod.UUID) -> dict[str, Any] | None:
    """Read the tenant's ``ai_cost_cap`` override; ``None`` if unset.

    Falls back to the toggle's registry default_value so a tenant who
    hasn't ever touched the override sees the system default
    (``enabled=False``). Returns ``None`` only when the registry row
    itself is missing — which means the V-06+B1 seed never ran and
    every caller should treat the cap as off.
    """
    from siftpdf.tenants.toggle_models import (
        Toggle,
        ToggleOverride,
        ToggleScope,
    )

    try:
        # Per-tenant override first.
        override_row = db.execute(
            select(ToggleOverride).where(
                ToggleOverride.toggle_id == CAP_TOGGLE_ID,
                ToggleOverride.scope == ToggleScope.TENANT,
                ToggleOverride.scope_id == str(tenant_id),
            )
        ).scalar_one_or_none()
        if override_row is not None and isinstance(override_row.value, dict):
            return dict(override_row.value)

        # Fall back to the registry default.
        toggle_row = db.get(Toggle, CAP_TOGGLE_ID)
        if toggle_row is not None and isinstance(toggle_row.default_value, dict):
            return dict(toggle_row.default_value)
    except Exception:  # pragma: no cover — fail open (see module docstring)
        logger.exception(
            "ai_cost_cap: failed to read toggle for tenant %s; failing open",
            tenant_id,
        )
        return None
    return None


def is_cap_enabled(db: Session, tenant_id: uuid_mod.UUID) -> bool:
    """Return ``True`` iff the tenant has the cap turned on."""
    config = _load_cap_config(db, tenant_id)
    return bool(config and config.get("enabled"))


def monthly_cap_cents(db: Session, tenant_id: uuid_mod.UUID) -> int | None:
    """Return the monthly cap in cents, or ``None`` when not enabled / unset."""
    config = _load_cap_config(db, tenant_id)
    if not config or not config.get("enabled"):
        return None
    raw = config.get("monthly_cap_cents")
    if not isinstance(raw, int) or raw <= 0:
        return None
    return raw


def alert_threshold_pct(db: Session, tenant_id: uuid_mod.UUID) -> int:
    """Return the informational alert threshold in 0-100. Defaults to 80."""
    config = _load_cap_config(db, tenant_id)
    if not config:
        return 80
    raw = config.get("alert_threshold_pct", 80)
    if not isinstance(raw, int):
        return 80
    return max(0, min(100, raw))


def _month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return ``(start_of_month_utc, start_of_next_month_utc)`` half-open."""
    moment = now or datetime.now(tz=timezone.utc)
    start = moment.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    # First day of next month: bump month, wrap year.
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def monthly_usage_cents(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    now: datetime | None = None,
) -> int:
    """Sum the tenant's ``ai_usage_logs.cost_cents`` for the current month.

    Failures fall back to ``0`` (fail-open: the cap doesn't block
    work when the metering query trips a DB hiccup).
    """
    from siftpdf.api.models import AIUsageLog

    start, end = _month_window(now=now)
    try:
        total = db.execute(
            select(func.coalesce(func.sum(AIUsageLog.cost_cents), 0)).where(
                AIUsageLog.tenant_id == tenant_id,
                AIUsageLog.created_at >= start,
                AIUsageLog.created_at < end,
            )
        ).scalar_one()
    except Exception:  # pragma: no cover — fail open
        logger.exception(
            "ai_cost_cap: failed to query monthly usage for tenant %s",
            tenant_id,
        )
        return 0
    return int(total or 0)


def check_cap_or_raise(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    projected_cost_cents: int = 0,
    now: datetime | None = None,
) -> None:
    """Raise :class:`CostCapExceededError` when this dispatch would exceed the cap.

    Off-by-default: when the cap isn't enabled or the cap value is
    not a positive integer this is a no-op. ``projected_cost_cents``
    is the caller's best estimate of what the upcoming LLM call will
    cost; conservative callers can pass an estimate based on
    ``compute_cost_cents`` with the maximum prompt/output sizes they
    intend to send, or pass ``0`` to gate only on already-spent cost.
    """
    cap = monthly_cap_cents(db, tenant_id)
    if cap is None:
        return
    used = monthly_usage_cents(db, tenant_id, now=now)
    if used + max(0, projected_cost_cents) >= cap:
        raise CostCapExceededError(
            tenant_id=tenant_id,
            cap_cents=cap,
            used_cents=used,
            projected_cents=max(0, projected_cost_cents),
        )


def remaining_cents(
    db: Session,
    tenant_id: uuid_mod.UUID,
    *,
    now: datetime | None = None,
) -> int | None:
    """Return how much budget is left for this month, or None if no cap.

    Negative values indicate "the tenant has already exceeded the cap
    by this many cents" — the caller should treat as 0 for display.
    """
    cap = monthly_cap_cents(db, tenant_id)
    if cap is None:
        return None
    used = monthly_usage_cents(db, tenant_id, now=now)
    return cap - used


__all__ = [
    "CAP_TOGGLE_ID",
    "CostCapExceededError",
    "alert_threshold_pct",
    "check_cap_or_raise",
    "is_cap_enabled",
    "monthly_cap_cents",
    "monthly_usage_cents",
    "remaining_cents",
]
