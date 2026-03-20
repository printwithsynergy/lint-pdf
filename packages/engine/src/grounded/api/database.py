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
        _db_state["engine"] = create_engine(
            database_url, pool_pre_ping=True, pool_size=5, max_overflow=10
        )
        _db_state["session_local"] = sessionmaker(
            bind=_db_state["engine"], autocommit=False, autoflush=False
        )


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
                from grounded.api.config import get_settings

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
