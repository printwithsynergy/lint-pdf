"""Structured logging setup for the engine.

The engine historically used ``logging.getLogger(__name__)`` with the
default format. That worked but dropped context: every
``logger.info("failed for tenant %s", tenant_id)`` call came out as an
unstructured string the log aggregator could only match with regex.

This module initialises ``structlog`` in "additive" mode: stdlib logger
calls remain untouched (``logger.exception("…")``, ``logger.warning``
etc. still work and don't need to change) but every record is rendered
as a single JSON object with:

* ISO timestamp
* log level
* event (the message)
* any contextvars bound for the current request / task
  (``request_id``, ``task_id``, ``task_name`` — set by middleware / Celery
   signals; see :mod:`siftpdf.api.middleware` and
   :mod:`siftpdf.queue.app`)
* exception info, formatted for Railway's log panel

The call is idempotent — ``configure_logging()`` can be invoked from
both the FastAPI lifespan and the Celery worker bootstrap without
double-installing handlers.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog

_configured = False


def _shared_processors(*, include_contextvars: bool) -> list[Any]:
    procs: list[Any] = []
    if include_contextvars:
        # Pull in request_id / task_id bound via bind_contextvars().
        procs.append(structlog.contextvars.merge_contextvars)
    procs.extend(
        [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
    )
    return procs


def configure_logging(*, force: bool = False) -> None:
    """Install the structlog JSON renderer on top of stdlib logging.

    Call once from the FastAPI lifespan startup hook and once from the
    Celery ``worker_process_init`` signal. Subsequent calls are a no-op
    unless ``force=True``.
    """
    global _configured
    if _configured and not force:
        return

    level_name = os.environ.get("LINTPDF_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    shared = _shared_processors(include_contextvars=True)

    # Stdlib formatter delegates to structlog's JSON renderer so
    # ``logging.getLogger(__name__).info("…")`` calls emit the same JSON
    # as ``structlog.get_logger().info(…)``.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Replace existing handlers so uvicorn's default plain-text handler
    # doesn't double-log. Uvicorn's own access logs still flow through
    # because they are stdlib loggers that bubble up to root.
    root.handlers = [handler]
    root.setLevel(level)

    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configured = True
