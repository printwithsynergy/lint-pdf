"""Health and status endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from grounded.api.schemas import HealthResponse, StatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Basic health check — always returns ok if the service is running."""
    return HealthResponse(status="ok")


def _probe_database() -> str:
    """Check database connectivity."""
    try:
        from sqlalchemy import text

        from grounded.api.database import get_engine

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
        from grounded.api.middleware import get_redis_client

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
        from grounded.queue.health import get_all_queue_depths, get_worker_count

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
