"""Worker health monitoring and queue inspection."""

from __future__ import annotations

from typing import Any

from lintpdf.queue.app import celery_app

QUEUE_NAMES = ("default", "priority", "webhooks")


def get_queue_depth(queue_name: str = "default") -> int:
    """Get the number of pending tasks in a queue.

    Args:
        queue_name: Name of the Celery queue to inspect.

    Returns:
        Number of pending messages in the queue.
    """
    try:
        with celery_app.connection_or_acquire() as conn:
            count: int = conn.default_channel.queue_declare(
                queue=queue_name, passive=True
            ).message_count
            return count
    except Exception:
        return 0


def get_all_queue_depths() -> dict[str, int]:
    """Get pending task counts for all known queues.

    Returns:
        Dict mapping queue name to pending message count.
    """
    return {name: get_queue_depth(name) for name in QUEUE_NAMES}


def get_active_workers() -> dict[str, Any]:
    """Get information about active workers.

    Returns:
        Dict mapping worker names to their status info.
    """
    inspector = celery_app.control.inspect()
    try:
        active = inspector.active() or {}
        stats = inspector.stats() or {}
    except Exception:
        return {}

    workers: dict[str, Any] = {}
    for name, tasks in active.items():
        workers[name] = {
            "active_tasks": len(tasks),
            "stats": stats.get(name, {}),
        }

    return workers


def get_worker_count() -> int:
    """Get the number of active workers.

    Returns:
        Number of workers currently connected.
    """
    try:
        ping = celery_app.control.ping(timeout=2.0)
        return len(ping) if ping else 0
    except Exception:
        return 0


def get_health_status() -> dict[str, Any]:
    """Get overall queue health status.

    Returns:
        Dict with per-queue depths, worker count, and overall status.
    """
    queue_depths = get_all_queue_depths()
    worker_count = get_worker_count()

    status = "healthy"
    if worker_count == 0:
        status = "degraded"

    return {
        "status": status,
        "queue_depths": queue_depths,
        "queue_depth": sum(queue_depths.values()),
        "worker_count": worker_count,
    }
