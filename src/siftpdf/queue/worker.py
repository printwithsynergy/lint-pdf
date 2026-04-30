"""Celery worker entry point.

Usage:
    celery -A siftpdf.queue.worker worker --loglevel=info --concurrency=2

This module initializes the database and storage before the worker starts
processing tasks, then re-exports the celery app for the CLI.
"""

from __future__ import annotations

import os

from celery.signals import worker_init

from siftpdf.queue.app import celery_app


@worker_init.connect  # type: ignore[untyped-decorator]
def _on_worker_init(**_kwargs: object) -> None:
    """Initialize database and storage when the worker starts."""
    from siftpdf.api.database import init_db

    database_url = os.environ.get("LINTPDF_DATABASE_URL")
    if not database_url:
        raise RuntimeError("LINTPDF_DATABASE_URL environment variable is required")
    init_db(database_url)


# Re-export for `celery -A siftpdf.queue.worker`
app = celery_app
