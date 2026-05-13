"""Celery worker entry point.

Usage (single-process, subscribes to every routable queue):
    celery -A lintpdf.queue.worker worker --loglevel=info --concurrency=2

The flag-less command above is the recommended quickstart. The
Celery app declares ``task_queues`` for every queue the engine
routes to (``default``, ``priority``, ``ai_heavy``, ``webhooks``,
``reports``, ``tiles``) in ``lintpdf.queue.app``, so a worker
started without ``-Q`` auto-subscribes to all of them.

For multi-pool deployments that need queue isolation (the
production layout on lintpdf.com uses one process per queue),
override with ``-Q``:

    celery -A lintpdf.queue.worker worker -Q ai_heavy --pool=threads
    celery -A lintpdf.queue.worker worker -Q webhooks
    celery -A lintpdf.queue.worker worker -Q default,priority

This module initializes the database and storage before the worker
starts processing tasks, then re-exports the celery app for the CLI.
"""

from __future__ import annotations

import os

from celery.signals import worker_init

from lintpdf.queue.app import celery_app


@worker_init.connect  # type: ignore[untyped-decorator]
def _on_worker_init(**_kwargs: object) -> None:
    """Initialize database and storage when the worker starts."""
    from lintpdf.api.database import init_db

    database_url = os.environ.get("LINTPDF_DATABASE_URL")
    if not database_url:
        raise RuntimeError("LINTPDF_DATABASE_URL environment variable is required")
    init_db(database_url)


# Re-export for `celery -A lintpdf.queue.worker`
app = celery_app
