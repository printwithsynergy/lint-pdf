"""Per-Claude-call spend metering (WS-G).

Every successful Anthropic ``messages.create`` writes one row to
``ai_usage_logs`` via :func:`record_usage`. Cost is stored in
**integer cents** (never Decimal, never float). Sub-cent calls —
common for cached Haiku turns — round *up* to 1 cent on insert so
quota maths never lose a call to rounding.

Pricing table is hardcoded from published Anthropic rates (Apr 2026).
Keep the values in lock-step with ``docs/ai-pricing.md`` — the
admin spend dashboard reads both and screams on disagreement.
"""

from __future__ import annotations

import contextlib
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


# Per-million-token prices in **thousandths of a cent** (so
# a $0.80 / 1M input price becomes 80_000 thousandths, stored as
# int to avoid float drift). Converted to cents by dividing
# by 1000 after the multiply.
#
# Source: Anthropic public pricing page, verified 2026-04-22.
# Cache-read is 10% of base input; cache-write is 125% of base input.
_PRICES_THOUSANDTH_CENT_PER_MTOK: dict[str, dict[str, int]] = {
    "claude-haiku-4-5": {
        "input": 80_000,  # $0.80  / 1M input  tokens
        "output": 400_000,  # $4.00  / 1M output tokens
        "cache_read": 8_000,  # 10% of input
        "cache_write": 100_000,  # 125% of input
    },
    "claude-sonnet-4-6": {
        "input": 300_000,  # $3.00  / 1M input
        "output": 1_500_000,  # $15.00 / 1M output
        "cache_read": 30_000,
        "cache_write": 375_000,
    },
    "claude-opus-4-7": {
        "input": 1_500_000,  # $15.00 / 1M input
        "output": 7_500_000,  # $75.00 / 1M output
        "cache_read": 150_000,
        "cache_write": 1_875_000,
    },
}


def _price_for(model: str) -> dict[str, int]:
    """Pricing row for a model name. Falls back to Haiku if unknown."""
    return _PRICES_THOUSANDTH_CENT_PER_MTOK.get(
        model, _PRICES_THOUSANDTH_CENT_PER_MTOK["claude-haiku-4-5"]
    )


def compute_cost_cents(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> int:
    """Compute integer-cent cost from a token breakdown.

    Sub-cent results (common for cached turns) round UP to ``1``
    so quota maths stay truthful even for tiny calls.
    """
    p = _price_for(model)
    # total thousandth-cents = sum(tokens * price_per_Mtok / 1_000_000)
    # Arithmetic in int thousandth-cents throughout; divide by 1000
    # at the end to get cents. ceil() so sub-cent rounds up.
    total_milli_cents = (
        input_tokens * p["input"]
        + output_tokens * p["output"]
        + cache_read_tokens * p["cache_read"]
        + cache_write_tokens * p["cache_write"]
    ) // 1_000_000
    cents = math.ceil(total_milli_cents / 1000)
    any_tokens = (input_tokens + output_tokens + cache_read_tokens + cache_write_tokens) > 0
    return max(1, cents) if any_tokens else 0


def record_usage(
    *,
    tenant_id: Any,
    job_id: Any | None,
    feature: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> int:
    """Insert one ``ai_usage_logs`` row; return the cost in cents.

    Never raises — metering failures log and return ``0`` so a
    stats flake never fails a preflight. The actual quota gate in
    :mod:`lintpdf.audit.quota` reads these rows on subsequent
    passes, so a dropped row means "this call was free" which is
    the most conservative fail-open outcome.
    """
    cost = compute_cost_cents(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        cache_write_tokens=cache_write_tokens,
    )
    try:
        from lintpdf.api.database import get_db_session
        from lintpdf.api.models import AIUsageLog
    except Exception:
        return cost

    session = None
    try:
        session = get_db_session()
        # Also populate the pre-existing credit-packages columns so
        # the legacy admin dashboards stay truthful. ``credits_consumed``
        # is the cents-as-credit-unit; ``cost`` is the USD dollar
        # equivalent (Numeric(8,4)) used by the credit-pack billing.
        session.add(
            AIUsageLog(
                tenant_id=tenant_id,
                job_id=job_id,
                category="ai_audit" if feature == "audit" else feature,
                feature=feature,
                credits_consumed=cost,
                cost=cost / 100.0,  # USD
                processing_time_ms=0,
                result_summary=None,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_write_tokens=cache_write_tokens,
                cost_cents=cost,
            )
        )
        session.commit()
    except Exception:
        logger.warning(
            "metering: failed to record usage for tenant=%s feature=%s — fail-open",
            tenant_id,
            feature,
            exc_info=True,
        )
    finally:
        if session is not None:
            with contextlib.suppress(Exception):
                session.close()
    return cost
