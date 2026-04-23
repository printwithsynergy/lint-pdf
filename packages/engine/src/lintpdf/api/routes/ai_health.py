"""Public AI health probe for the app shell + viewer outage banner.

Returns ``{"status": "ok"}`` or ``{"status": "degraded"}`` based on
the reactive sliding-window detector in :mod:`lintpdf.audit.outage`.
Unauthenticated — the viewer polls from third-party origins with
just a report token. Safe: the response carries no tenant info.
"""

from __future__ import annotations

from fastapi import APIRouter

from lintpdf.audit.outage import is_outage

router = APIRouter(prefix="/api/v1/ai", tags=["ai-health"])


@router.get("/health")
def ai_health() -> dict[str, str]:
    """Return the live Claude health signal.

    ``status`` is one of:

    * ``ok`` — fewer than half of the last 20 Claude calls failed.
    * ``degraded`` — the outage flag is set (admin override or the
      reactive detector); the viewer should surface its banner.
    """
    return {"status": "degraded" if is_outage() else "ok"}
