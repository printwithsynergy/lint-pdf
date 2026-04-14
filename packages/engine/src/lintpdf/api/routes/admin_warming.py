"""Super-admin tile warming observability: recent events + aggregates.

Events are written to capped Redis lists from ``warm_viewer_tiles`` so
this router only has to LRANGE and aggregate. When Redis is not
configured every endpoint returns a ``status="no_redis"`` response
(HTTP 200) so the dashboard can render an informational banner instead
of an error.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from lintpdf.api.auth import verify_admin_key
from lintpdf.api.middleware import get_redis_client
from lintpdf.queue.tasks import (
    _tile_warm_events_all_key,
    _tile_warm_events_key,
    _tile_warm_status_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/tile-warming", tags=["admin", "warming"])


# ── Models ────────────────────────────────────────────────────────────


class WarmEvent(BaseModel):
    """One recorded warming event — either ``tile_warm.complete`` or ``.failure``."""

    event: str = Field(..., description='"tile_warm.complete" or "tile_warm.failure"')
    job_id: str
    tenant_id: str | None = None
    page_count: int | None = None
    dpi: int | None = None
    thumbnails: bool | None = None
    duration_s: float | None = None
    error: str | None = None
    recorded_at: str


class WarmEventsResponse(BaseModel):
    events: list[WarmEvent]
    status: str = "ok"


class TenantWarmSummary(BaseModel):
    tenant_id: str
    completes: int
    failures: int
    pages_total: int
    p50_duration_s: float | None
    p95_duration_s: float | None
    last_event_at: str | None


class WarmSummaryResponse(BaseModel):
    window_hours: int
    total_events: int
    total_completes: int
    total_failures: int
    success_rate: float | None = Field(
        None, description="completes / (completes + failures); None when no events"
    )
    p50_duration_s: float | None
    p95_duration_s: float | None
    p99_duration_s: float | None
    top_tenants: list[TenantWarmSummary]
    top_errors: list[dict[str, Any]]
    per_tenant: list[TenantWarmSummary]
    status: str = "ok"


class WarmJobResponse(BaseModel):
    job_id: str
    status_hash: dict[str, str] | None
    recent_events: list[WarmEvent]
    status: str = "ok"


# ── Helpers ───────────────────────────────────────────────────────────


def _decode_events(raw: list[Any]) -> list[WarmEvent]:
    """JSON-decode a list of LRANGE items, dropping any that fail to parse."""
    out: list[WarmEvent] = []
    for item in raw:
        try:
            if isinstance(item, bytes):
                item = item.decode("utf-8")
            payload = json.loads(item)
            out.append(WarmEvent(**payload))
        except Exception:
            logger.warning("tile_warm: dropped malformed event", exc_info=True)
            continue
    return out


def _percentile(values: list[float], p: float) -> float | None:
    """Simple nearest-rank percentile. Returns ``None`` for empty inputs."""
    if not values:
        return None
    sorted_vals = sorted(values)
    # Clamp the index to the last element so p=1.0 still resolves.
    idx = min(len(sorted_vals) - 1, round(p * (len(sorted_vals) - 1)))
    return round(sorted_vals[idx], 3)


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/events", response_model=WarmEventsResponse)
def list_events(
    tenant_id: str | None = Query(
        None, description="Filter by tenant_id; omit for the global feed."
    ),
    limit: int = Query(100, ge=1, le=500),
    _key: str = Depends(verify_admin_key),
) -> WarmEventsResponse:
    """Return the most recent N warming events, newest first."""
    redis = get_redis_client()
    if redis is None:
        return WarmEventsResponse(events=[], status="no_redis")

    key = _tile_warm_events_key(tenant_id) if tenant_id else _tile_warm_events_all_key()
    try:
        raw = redis.lrange(key, 0, limit - 1) or []
    except Exception:
        logger.exception("admin_warming: lrange failed")
        raw = []
    return WarmEventsResponse(events=_decode_events(list(raw)))


@router.get("/summary", response_model=WarmSummaryResponse)
def summary(
    since_hours: int = Query(24, ge=1, le=168, description="Aggregation window in hours (1..168)."),
    _key: str = Depends(verify_admin_key),
) -> WarmSummaryResponse:
    """Aggregate the global event list over the last ``since_hours`` hours."""
    redis = get_redis_client()
    if redis is None:
        return WarmSummaryResponse(
            window_hours=since_hours,
            total_events=0,
            total_completes=0,
            total_failures=0,
            success_rate=None,
            p50_duration_s=None,
            p95_duration_s=None,
            p99_duration_s=None,
            top_tenants=[],
            top_errors=[],
            per_tenant=[],
            status="no_redis",
        )

    try:
        raw = redis.lrange(_tile_warm_events_all_key(), 0, -1) or []
    except Exception:
        logger.exception("admin_warming: lrange _all failed")
        raw = []

    events = _decode_events(list(raw))

    cutoff = _dt.datetime.now(_dt.UTC) - _dt.timedelta(hours=since_hours)

    def _in_window(ev: WarmEvent) -> bool:
        try:
            ts = _dt.datetime.fromisoformat(ev.recorded_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=_dt.UTC)
        except Exception:
            return False
        return ts >= cutoff

    windowed = [ev for ev in events if _in_window(ev)]

    by_tenant: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "completes": 0,
            "failures": 0,
            "pages_total": 0,
            "durations": [],
            "last_event_at": None,
        }
    )
    all_durations: list[float] = []
    error_counts: dict[str, int] = defaultdict(int)
    completes = 0
    failures = 0

    for ev in windowed:
        tenant_key = ev.tenant_id or "_unknown"
        bucket = by_tenant[tenant_key]
        if ev.event == "tile_warm.complete":
            completes += 1
            bucket["completes"] += 1
            if ev.page_count:
                bucket["pages_total"] += int(ev.page_count)
            if ev.duration_s is not None and ev.duration_s >= 0:
                bucket["durations"].append(float(ev.duration_s))
                all_durations.append(float(ev.duration_s))
        elif ev.event == "tile_warm.failure":
            failures += 1
            bucket["failures"] += 1
            if ev.error:
                error_counts[ev.error[:200]] += 1

        prev_last = bucket["last_event_at"]
        if prev_last is None or ev.recorded_at > prev_last:
            bucket["last_event_at"] = ev.recorded_at

    per_tenant = [
        TenantWarmSummary(
            tenant_id=tid,
            completes=b["completes"],
            failures=b["failures"],
            pages_total=b["pages_total"],
            p50_duration_s=_percentile(b["durations"], 0.50),
            p95_duration_s=_percentile(b["durations"], 0.95),
            last_event_at=b["last_event_at"],
        )
        for tid, b in by_tenant.items()
    ]
    per_tenant.sort(key=lambda s: s.completes + s.failures, reverse=True)
    top_tenants = per_tenant[:5]

    top_errors = [
        {"error": msg, "count": cnt}
        for msg, cnt in sorted(error_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    ]

    total = completes + failures
    success_rate = (completes / total) if total else None

    return WarmSummaryResponse(
        window_hours=since_hours,
        total_events=len(windowed),
        total_completes=completes,
        total_failures=failures,
        success_rate=round(success_rate, 4) if success_rate is not None else None,
        p50_duration_s=_percentile(all_durations, 0.50),
        p95_duration_s=_percentile(all_durations, 0.95),
        p99_duration_s=_percentile(all_durations, 0.99),
        top_tenants=top_tenants,
        top_errors=top_errors,
        per_tenant=per_tenant,
    )


@router.get("/jobs/{job_id}", response_model=WarmJobResponse)
def job_detail(
    job_id: str,
    _key: str = Depends(verify_admin_key),
) -> WarmJobResponse:
    """Current warming status + recent events filtered to a single job."""
    redis = get_redis_client()
    if redis is None:
        return WarmJobResponse(
            job_id=job_id,
            status_hash=None,
            recent_events=[],
            status="no_redis",
        )

    status_hash: dict[str, str] | None = None
    try:
        raw_hash = redis.hgetall(_tile_warm_status_key(job_id)) or {}
        status_hash = {
            (k.decode() if isinstance(k, bytes) else str(k)): (
                v.decode() if isinstance(v, bytes) else str(v)
            )
            for k, v in raw_hash.items()
        }
        if not status_hash:
            status_hash = None
    except Exception:
        logger.exception("admin_warming: hgetall failed")
        status_hash = None

    try:
        raw_events = redis.lrange(_tile_warm_events_all_key(), 0, -1) or []
    except Exception:
        logger.exception("admin_warming: lrange _all failed")
        raw_events = []

    all_events = _decode_events(list(raw_events))
    matched = [ev for ev in all_events if ev.job_id == job_id]

    return WarmJobResponse(
        job_id=job_id,
        status_hash=status_hash,
        recent_events=matched,
    )
