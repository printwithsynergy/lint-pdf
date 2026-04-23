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
        # Restart every prefork child after exactly ONE task. Diagnostic
        # workaround for the 2026-04-23 silent preflight hang — the
        # hypothesis is that the prefork child inherits some corrupt
        # post-fork state (a locked mutex somewhere in SQLAlchemy,
        # logging, or Celery's own state) that makes task execution
        # deadlock before any user code runs. Forcing a fresh child
        # per task means each preflight runs in a process whose only
        # fork happened seconds before and whose parent was idle.
        # Slower than a long-lived pool but unblocks preflight.
        worker_max_tasks_per_child=1,
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
            "lintpdf.queue.audit_tasks.drain_ai_audit_rerun_queue": {"queue": "default"},
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
            "drain-ai-audit-rerun-queue": {
                "task": "lintpdf.queue.audit_tasks.drain_ai_audit_rerun_queue",
                "schedule": 600.0,  # Every 10 minutes
            },
        },
    )

    # Auto-discover tasks in the queue package. (Eager import of
    # ``audit_tasks`` happens below after ``celery_app`` is assigned
    # at module scope — doing it inside this function hits a circular
    # import because audit_tasks does ``from lintpdf.queue.app import
    # celery_app`` before this function has returned.)
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
def _configure_worker_process(**_: Any) -> None:
    """Set up each forked Celery worker process.

    Two jobs:

    1. Install the structlog JSON renderer so worker logs match the
       FastAPI process's format.
    2. **Drop the DB engine the child inherited from the parent** via
       ``fork()``. Without this, every prefork worker shares the
       parent's psycopg2 sockets — the first query in the child corrupts
       the underlying TCP state (the kernel sees two processes reading
       the same fd), Postgres terminates the connection, and SQLAlchemy
       surfaces the classic ``OperationalError: server closed the
       connection unexpectedly``. The task then silently abandons
       without firing a Soft/Hard TimeLimit warning, which is exactly
       the heartbeat-miss / ``task received ... (no further logs)``
       pattern we caught on Worker-AI on 2026-04-22.

    The API process calls ``init_db()`` on startup; the first task to
    land on this worker will re-init against the same DATABASE_URL but
    with a fresh engine owned entirely by the child.

    NB: ``_drain_rerun_queue`` was previously called from here (WS-H).
    It was moved to a Celery beat-scheduled task
    (:func:`drain_ai_audit_rerun_queue`) to avoid blocking prefork
    child boot on a DB query — the silent-death symptom we hit
    on 2026-04-23 after #156 + #158 + #159.
    """
    from lintpdf.api.database import reset_db_state
    from lintpdf.api.logging_config import configure_logging

    # ``force=True`` is mandatory in a forked child — the module-level
    # ``_configured`` flag is inherited True from the parent, which
    # would skip handler re-installation. The child would then log
    # through the parent's StreamHandler, whose internal RLock may
    # have been inherited held-without-owner if the parent was mid-log
    # at fork, deadlocking every child-side log call silently.
    # No log output → silent task hang (the 2026-04-23 outage).
    configure_logging(force=True)
    reset_db_state()


def _drain_rerun_queue() -> None:
    """Enqueue ``audit_findings_async`` for every row in the queue table.

    Called by the beat-scheduled ``drain_ai_audit_rerun_queue`` task
    (every 10 minutes), NOT from ``worker_process_init``. Blocking
    the fork hook on a DB query turned out to be fatal — when PgBouncer
    is busy or the query stalls, the child never reaches Celery's
    task-pickup loop and every subsequent preflight sits in
    ``received`` forever with no traceback.
    """
    from sqlalchemy import text

    from lintpdf.api.database import get_db_session

    try:
        from lintpdf.queue.audit_tasks import audit_findings_async
    except Exception:
        # audit_tasks pulls in Celery; if for some reason it's not
        # wired, skip silently — the task is harmless to skip.
        return

    session = get_db_session()
    try:
        exists = session.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'ai_audit_rerun_queue'"
            )
        ).first()
        if not exists:
            return

        rows = session.execute(
            text("SELECT job_id::text FROM ai_audit_rerun_queue")
        ).fetchall()
        for (jid,) in rows:
            try:
                audit_findings_async.delay(jid)
                session.execute(
                    text(
                        "DELETE FROM ai_audit_rerun_queue "
                        "WHERE job_id = :jid"
                    ),
                    {"jid": jid},
                )
                session.commit()
            except Exception:
                session.rollback()
                # Leave the row so a later drain attempt retries.
    finally:
        import contextlib

        with contextlib.suppress(Exception):
            session.close()


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


# Eager-import the task modules that ``autodiscover_tasks`` misses
# (it only looks for ``tasks.py``). Placed at the bottom of the module
# so ``celery_app`` is fully assigned before audit_tasks does its
# ``from lintpdf.queue.app import celery_app`` — avoids the circular
# import that the first attempt triggered.
#
# Without these eager imports a forked child that does
# ``from lintpdf.queue.audit_tasks import audit_findings_async`` would
# register tasks mid-flight and the worker receive-loop deadlocks
# ("Task received, no further logs" — the 2026-04-23 outage).
from lintpdf.queue import audit_tasks as _eager_audit_tasks  # noqa: E402, F401
