"""Celery application configuration for LintPDF worker."""

from __future__ import annotations

from celery import Celery


def create_celery_app(broker_url: str) -> Celery:
    """Create and configure the Celery application.

    Args:
        broker_url: Redis broker URL.

    Returns:
        Configured Celery application instance.
    """
    app = Celery("lintpdf", broker=broker_url)

    app.conf.update(
        result_backend=broker_url,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=600,  # 10 minute hard limit (supports 1GB files + report gen)
        task_soft_time_limit=540,  # 9 minute soft limit
        worker_prefetch_multiplier=1,  # One task at a time per worker
        task_acks_late=True,  # Acknowledge after completion
        worker_max_tasks_per_child=25,  # Restart worker after 25 tasks (lower for larger files)
        task_routes={
            "lintpdf.webhook.dispatch": {"queue": "webhooks"},
            "lintpdf.queue.tasks.cleanup_expired_reports": {"queue": "default"},
        },
        beat_schedule={
            "cleanup-expired-reports": {
                "task": "lintpdf.queue.tasks.cleanup_expired_reports",
                "schedule": 86400.0,  # Daily (24 hours)
            },
        },
    )

    # Auto-discover tasks in the queue package
    app.autodiscover_tasks(["lintpdf.queue"])

    return app


# Default app instance — read broker URL from environment.
# Falls back to memory:// (Celery's in-process transport) when no broker
# is configured, which allows test collection and local dev without Redis.
import os as _os  # noqa: E402

_broker = _os.environ.get("LINTPDF_REDIS_URL") or _os.environ.get("REDIS_URL") or "memory://"
celery_app = create_celery_app(broker_url=_broker)
