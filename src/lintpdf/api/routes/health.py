"""Health and status endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse

from lintpdf.api.schemas import HealthResponse, StatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    """Redirect browser visits to the marketing site."""
    return RedirectResponse("https://lintpdf.com", status_code=302)


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Liveness probe — returns ``ok`` as long as the process is running.

    Use ``/ready`` for readiness checks that actually exercise dependencies.
    """
    return HealthResponse(status="ok")


@router.get("/ready", tags=["health"])
async def readiness_check() -> JSONResponse:
    """Readiness probe — 200 iff all hard dependencies respond.

    Railway (and any k8s-style orchestrator) should point its healthcheck
    at this endpoint instead of ``/health``. When the DB or Redis goes
    away we return 503 so the load balancer drains traffic to a healthy
    instance instead of serving 500s at the edge.
    """
    db_status = _probe_database()
    redis_status = _probe_redis()

    payload = {"status": "ok", "database": db_status, "redis": redis_status}
    # ``not_configured`` is treated as "fine" — e.g. during local dev when
    # Redis isn't wired up. Only hard ``error`` states fail the check.
    if db_status == "error" or redis_status == "error":
        payload["status"] = "unavailable"
        return JSONResponse(status_code=503, content=payload)
    return JSONResponse(status_code=200, content=payload)


def _probe_database() -> str:
    """Check database connectivity."""
    try:
        from sqlalchemy import text

        from lintpdf.api.database import get_engine

        engine = get_engine()
        if engine is None:
            return "not_configured"
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        logger.exception("Database health probe failed")
        return "error"


def _probe_redis() -> str:
    """Check Redis connectivity."""
    try:
        from lintpdf.api.middleware import get_redis_client

        client = get_redis_client()
        if client is None:
            return "not_configured"
        client.ping()
        return "connected"
    except Exception:
        logger.exception("Redis health probe failed")
        return "error"


def _probe_queue() -> tuple[int, int, dict[str, int]]:
    """Check Celery queue depth and worker count.

    Returns:
        Tuple of (total_queue_depth, worker_count, per_queue_depths).
    """
    try:
        from lintpdf.queue.health import get_all_queue_depths, get_worker_count

        queue_depths = get_all_queue_depths()
        worker_count = get_worker_count()
        total = sum(max(0, d) for d in queue_depths.values())
        return total, worker_count, queue_depths
    except Exception:
        logger.exception("Queue health probe failed")
        return 0, 0, {}


@router.get("/api/v1/status", response_model=StatusResponse, tags=["health"])
async def detailed_status() -> StatusResponse:
    """Detailed service status including database, Redis, and queue info."""
    db_status = _probe_database()
    redis_status = _probe_redis()
    queue_depth, worker_count, queue_depths = _probe_queue()

    overall = "ok"
    if db_status == "error" or redis_status == "error":
        overall = "degraded"

    return StatusResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        queue_depth=queue_depth,
        worker_count=worker_count,
        queue_depths=queue_depths,
    )
