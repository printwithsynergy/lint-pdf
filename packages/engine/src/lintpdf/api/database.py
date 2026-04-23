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
    """Drop the cached engine AND the fork-inherited mutex.

    Called from the Celery ``worker_process_init`` fork hook. Three jobs:

    1. **Replace ``_db_lock``** with a fresh ``threading.Lock()``. The
       lock is module-level: if the parent happened to be holding it at
       ``fork()`` time (even for a microsecond — e.g. first query during
       concurrent boot), the child inherits the lock ALREADY LOCKED
       with no thread owning it. Every ``with _db_lock:`` in the child
       then blocks forever. Since ``get_db_session`` opens with
       ``with _db_lock:``, the FIRST query in the child deadlocks
       silently and the task execution stalls with no logs — exactly
       the "Task received, no further output, missed heartbeat" pattern
       that plagued prod on 2026-04-23.
    2. **Dispose the inherited engine** so each prefork slot builds its
       own TCP sockets rather than corrupting the parent's. ``close=False``
       keeps the parent's sockets intact.
    3. **Clear the session factory** so the next ``get_db_session`` call
       re-inits against the same DATABASE_URL but with a fresh engine
       owned entirely by the child.
    """
    import contextlib
    import threading

    global _db_lock
    # Reset the lock FIRST — it's what makes the rest of this function
    # safe to run in a child process. Before this line, ``with _db_lock:``
    # would deadlock if the parent was holding the lock at fork time.
    _db_lock = threading.Lock()

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
