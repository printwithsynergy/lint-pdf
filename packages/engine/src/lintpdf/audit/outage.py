"""Reactive sliding-window Claude outage detector.

Pushes a per-call success/fail marker into a capped Redis list; when
more than half of the last N (default 20) calls failed, surfaces a
`degraded` state that the app shell + viewer poll via
``GET /api/v1/ai/health``. The window is time-bounded via a
short TTL on the outage flag itself so recovery auto-clears.

Design notes:

* Fail-open — any Redis error is logged and treated as "ok".
  Losing the outage banner is preferable to bouncing every AI call
  because Redis flaked.
* The sliding window lives in one Redis list (``lintpdf:ai_outcomes``)
  so every worker contributes to the same signal. Per-process state
  would miss half the data when calls are spread across Worker +
  Worker-AI.
* ``record_outcome(success)`` + ``is_outage()`` are idempotent +
  cheap — one ``LPUSH`` + ``LTRIM`` on write, one ``LRANGE`` on read.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_WINDOW_SIZE = 20
_FAILURE_THRESHOLD = 11  # > 50% of the window
_OUTAGE_TTL_S = 300  # Auto-clear the outage flag after 5 min
_OUTCOMES_KEY = "lintpdf:ai_outcomes"
_OUTAGE_KEY = "lintpdf:ai_outage"


def _redis_client() -> object | None:
    """Return a shared Redis client or ``None`` if Redis is unreachable.

    Reads ``LINTPDF_REDIS_URL`` (the Celery broker URL) or falls back
    to ``REDIS_URL``. The helper caches the client on the module so
    we don't reopen the socket per call.
    """
    if _redis_client._cached is not None:  # type: ignore[attr-defined]
        return _redis_client._cached  # type: ignore[attr-defined]
    try:
        import redis

        url = (
            os.environ.get("LINTPDF_REDIS_URL")
            or os.environ.get("REDIS_URL")
            or ""
        )
        if not url:
            return None
        client = redis.Redis.from_url(url, decode_responses=True)
        _redis_client._cached = client  # type: ignore[attr-defined]
        return client
    except Exception:
        logger.warning("outage: redis client init failed; fail-open")
        return None


_redis_client._cached = None  # type: ignore[attr-defined]


def record_outcome(success: bool) -> None:
    """Record one Claude call result into the sliding window.

    Never raises. Called from ``ClaudeAuditor._audit_batch`` (WS-B
    wiring) and from any future AI-feature Claude call site.
    """
    client = _redis_client()
    if client is None:
        return
    try:
        marker = "1" if success else "0"
        pipe = client.pipeline()
        pipe.lpush(_OUTCOMES_KEY, marker)
        pipe.ltrim(_OUTCOMES_KEY, 0, _WINDOW_SIZE - 1)
        pipe.execute()
        # Recompute the outage flag from the fresh window — cheap
        # and keeps the flag self-healing as good calls push bad
        # ones off the tail.
        _refresh_flag(client)
    except Exception:
        logger.warning("outage: record_outcome failed; fail-open", exc_info=True)


def _refresh_flag(client: object) -> None:
    try:
        entries = client.lrange(_OUTCOMES_KEY, 0, _WINDOW_SIZE - 1)  # type: ignore[attr-defined]
        if len(entries) < _WINDOW_SIZE:
            # Not enough signal yet; clear any stale flag.
            client.delete(_OUTAGE_KEY)  # type: ignore[attr-defined]
            return
        failures = sum(1 for e in entries if e == "0")
        if failures >= _FAILURE_THRESHOLD:
            client.set(_OUTAGE_KEY, "1", ex=_OUTAGE_TTL_S)  # type: ignore[attr-defined]
        else:
            client.delete(_OUTAGE_KEY)  # type: ignore[attr-defined]
    except Exception:
        logger.warning("outage: _refresh_flag failed; fail-open", exc_info=True)


def is_outage() -> bool:
    """Return True when the AI health signal is in degraded state.

    Fail-open: any Redis error → False. The outage flag auto-expires
    after 5 min so a blip followed by a quiet period clears cleanly.
    """
    client = _redis_client()
    if client is None:
        return False
    try:
        return bool(client.get(_OUTAGE_KEY))  # type: ignore[attr-defined]
    except Exception:
        logger.warning("outage: is_outage failed; fail-open", exc_info=True)
        return False


def override(state: bool | None) -> None:
    """Admin-only forced override used by the health toolbox (WS-H).

    ``True`` pins the outage flag on for the TTL (5 min); ``False``
    clears it; ``None`` is a no-op (reverts to reactive detection).
    """
    client = _redis_client()
    if client is None:
        return
    try:
        if state is True:
            client.set(_OUTAGE_KEY, "1", ex=_OUTAGE_TTL_S)  # type: ignore[attr-defined]
        elif state is False:
            client.delete(_OUTAGE_KEY)  # type: ignore[attr-defined]
    except Exception:
        logger.warning("outage: override failed", exc_info=True)
