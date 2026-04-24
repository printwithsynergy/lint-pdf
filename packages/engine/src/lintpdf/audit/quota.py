"""Monthly AI-spend quota check (WS-G).

Sums ``ai_usage_logs.cost_cents`` for the current calendar month
and compares against ``entitlements.monthly_ai_credits`` (also
int cents). The result drives two separate code paths:

* Pre-preflight gate in ``queue/tasks.py`` — when over, emits one
  ``LPDF_AI_QUOTA_EXCEEDED`` finding and skips every AI feature
  for the job. Non-AI preflight still runs.
* Retry-time gate in ``queue/audit_tasks.py`` — each async audit
  retry re-reads quota state; if the tenant has since gone over,
  the task abandons and the findings get
  ``audit_status='quota_exceeded'``.

Fail-open on DB errors — losing quota enforcement is preferable
to bouncing every AI call because Postgres flaked.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def current_month_usage_cents(db: Any, tenant_id: Any) -> int:
    """Sum of ``cost_cents`` for the current calendar month.

    Uses ``COALESCE`` on ``cost_cents`` so pre-037 rows (which
    stored ``cost`` as USD Numeric) count as zero rather than
    breaking the aggregation.
    """
    try:
        from sqlalchemy import func

        from lintpdf.api.models import AIUsageLog

        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total = (
            db.query(func.coalesce(func.sum(AIUsageLog.cost_cents), 0))
            .filter(
                AIUsageLog.tenant_id == tenant_id,
                AIUsageLog.created_at >= month_start,
            )
            .scalar()
        )
        return int(total or 0)
    except Exception:
        logger.warning(
            "quota: current_month_usage_cents failed for tenant=%s — fail-open",
            tenant_id,
            exc_info=True,
        )
        return 0


def is_over_quota(entitlements: Any, used_cents: int) -> bool:
    """Return True when ``used_cents`` has met or exceeded the cap.

    Zero cap means "no AI budget, period" — every call is over
    quota. Caps only apply when both ``ai_enabled`` and at least
    one ``ai_features`` entry are set, otherwise the tenant has
    no AI path to spend on.
    """
    cap = int(getattr(entitlements, "monthly_ai_credits", 0) or 0)
    return cap > 0 and used_cents >= cap
