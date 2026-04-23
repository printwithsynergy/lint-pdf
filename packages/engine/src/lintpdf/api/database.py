"""Database session management for FastAPI."""

from __future__ import annotations

import threading
from collections.abc import Generator  # noqa: TC003
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Module-level container — initialized on first call to init_db()
_db_state: dict[str, Any] = {
    "engine": None,
    "session_local": None,
}
_db_lock = threading.Lock()


def init_db(database_url: str) -> None:
    """Initialize the database engine and session factory.

    Args:
        database_url: PostgreSQL connection string.
    """
    with _db_lock:
        if _db_state["engine"] is not None:
            return
        # ``pool_pre_ping`` catches dropped connections (Postgres restarts,
        # PgBouncer reassignments) and issues ``SELECT 1`` before every
        # checkout, avoiding the ``OperationalError: server closed the
        # connection unexpectedly`` that otherwise cascades into
        # SQLAlchemy ``InvalidRequestError: Can't reconnect until invalid
        # transaction is rolled back`` (sqlalche.me/e/20/e3q8). We saw
        # this in prod after the 2026-04-22 Postgres restart wiped every
        # server session, leaving worker pools full of dead sockets that
        # only manifested under load as silent Celery task stalls.
        #
        # ``pool_recycle=300`` proactively drops idle connections so
        # PgBouncer transaction-pool reassignments don't hand back a
        # stale 5-minute-old socket. Aligns with PgBouncer's default
        # ``server_idle_timeout`` and the worker's 25-task child recycle.
        _db_state["engine"] = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=5,
            max_overflow=10,
        )
        _db_state["session_local"] = sessionmaker(
            bind=_db_state["engine"], autocommit=False, autoflush=False
        )


def reset_db_state() -> None:
    """Drop the cached engine so the next call to ``init_db`` rebuilds it.

    Celery ``prefork`` workers inherit the parent process's engine across
    ``fork()``. The child then holds references to TCP sockets that the
    parent is also using, which psycopg2 detects as corrupted connections
    the moment the child tries to execute a query — manifesting as silent
    worker deaths (``missed heartbeat from celery@...``) with no
    Soft/Hard TimeLimit warnings because the task never gets far enough
    to progress. Disposing + resetting in the child's
    ``worker_process_init`` signal handler forces each prefork slot to
    build its own engine with its own socket pool.

    ``dispose(close=False)`` releases the engine's pool WITHOUT calling
    ``close()`` on the inherited sockets — closing them in the child
    would also shut them down for the parent, breaking the parent's
    beat/scheduler pool. ``close=False`` lets each process manage only
    its own copy.
    """
    import contextlib

    with _db_lock:
        engine = _db_state["engine"]
        if engine is not None:
            with contextlib.suppress(Exception):
                engine.dispose(close=False)
        _db_state["engine"] = None
        _db_state["session_local"] = None


def get_engine() -> Any:
    """Return the current database engine."""
    return _db_state["engine"]


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Usage:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    if _db_state["session_local"] is None:
        msg = "Database not initialized. Call init_db() first."
        raise RuntimeError(msg)

    db = _db_state["session_local"]()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a standalone database session (for use outside FastAPI, e.g. Celery tasks).

    Caller is responsible for closing the session.

    Returns:
        SQLAlchemy Session instance.

    Raises:
        RuntimeError: If the database has not been initialized.
    """
    if _db_state["session_local"] is None:
        with _db_lock:
            if _db_state["session_local"] is None:
                # Auto-initialize from settings if not yet done
                from lintpdf.api.config import get_settings

                settings = get_settings()
                init_db(settings.database_url)

    if _db_state["session_local"] is None:
        msg = "Database not initialized. Call init_db() first."
        raise RuntimeError(msg)

    return _db_state["session_local"]()


def dispose_db() -> None:
    """Dispose the database engine (for shutdown)."""
    if _db_state["engine"] is not None:
        _db_state["engine"].dispose()
        _db_state["engine"] = None
        _db_state["session_local"] = None
