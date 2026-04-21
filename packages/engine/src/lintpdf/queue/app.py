"""Celery application configuration for LintPDF worker."""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.signals import task_postrun, task_prerun, worker_process_init


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
        # Job status is the source of truth in Postgres; Celery results are
        # only ever polled indirectly (never via AsyncResult.get). Keeping
        # the meta rows beyond an hour just bloats Redis — this caps them at
        # one hour (3600s) to match the worst-case hard task_time_limit with
        # headroom for a single retry window.
        result_expires=3600,
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
        # When a worker is killed mid-task (redeploy, OOM, SIGKILL), the
        # broker requeues the task to another worker instead of dropping
        # it. Without this, a redeploy abandons in-flight jobs and their
        # ``Job`` rows stay in ``processing`` forever.
        task_reject_on_worker_lost=True,
        worker_max_tasks_per_child=25,  # Restart worker after 25 tasks (lower for larger files)
        # All beat-scheduled tasks must route to a queue the worker actually
        # listens on (``default`` / ``priority``) — Celery's default queue is
        # ``celery``, which no service consumes, so an unrouted scheduled task
        # sits in Redis forever and the corresponding safety net never fires.
        task_routes={
            "lintpdf.webhook.dispatch": {"queue": "webhooks"},
            "lintpdf.queue.tasks.cleanup_expired_reports": {"queue": "default"},
            "lintpdf.queue.tasks.probe_pending_custom_domains": {"queue": "default"},
            "lintpdf.queue.tasks.process_approval_timeouts": {"queue": "default"},
            "lintpdf.queue.tasks.reap_stale_jobs": {"queue": "default"},
            "lintpdf.queue.tasks.sweep_webhook_deliveries": {"queue": "default"},
        },
        beat_schedule={
            "cleanup-expired-reports": {
                "task": "lintpdf.queue.tasks.cleanup_expired_reports",
                "schedule": 86400.0,  # Daily (24 hours)
            },
            "probe-pending-custom-domains": {
                "task": "lintpdf.queue.tasks.probe_pending_custom_domains",
                "schedule": 300.0,  # Every 5 minutes
            },
            "process-approval-timeouts": {
                "task": "lintpdf.queue.tasks.process_approval_timeouts",
                "schedule": 600.0,  # Every 10 minutes
            },
            "reap-stale-jobs": {
                "task": "lintpdf.queue.tasks.reap_stale_jobs",
                "schedule": 300.0,  # Every 5 minutes — safety net
            },
            "sweep-webhook-deliveries": {
                "task": "lintpdf.queue.tasks.sweep_webhook_deliveries",
                "schedule": 86400.0,  # Daily
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


# ---------------------------------------------------------------------------
# Structured logging context for workers
# ---------------------------------------------------------------------------


@worker_process_init.connect  # type: ignore[misc]
def _configure_worker_logging(**_: Any) -> None:
    """Install the structlog JSON renderer inside every worker process."""
    from lintpdf.api.logging_config import configure_logging

    configure_logging()


@task_prerun.connect  # type: ignore[misc]
def _bind_task_context(task_id: str | None = None, task: Any = None, **_: Any) -> None:
    """Bind ``task_id`` / ``task_name`` into structlog contextvars for the task."""
    from structlog.contextvars import bind_contextvars

    bind_contextvars(
        task_id=task_id,
        task_name=getattr(task, "name", None) if task is not None else None,
    )


@task_postrun.connect  # type: ignore[misc]
def _unbind_task_context(**_: Any) -> None:
    """Clear task-scoped contextvars so the next task starts clean."""
    from structlog.contextvars import unbind_contextvars

    unbind_contextvars("task_id", "task_name")
