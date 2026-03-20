"""Database session management for FastAPI."""

from __future__ import annotations

import threading
from collections.abc import Generator  # noqa: TC003
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Module-level engine and session factory — initialized on first call to init_db()
_engine: Any = None
_SessionLocal: sessionmaker[Session] | None = None
_db_lock = threading.Lock()


def init_db(database_url: str) -> None:
    """Initialize the database engine and session factory.

    Args:
        database_url: PostgreSQL connection string.
    """
    global _engine, _SessionLocal  # skipcq: PYL-W0603
    with _db_lock:
        if _engine is not None:
            return
        _engine = create_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine() -> Any:
    """Return the current database engine."""
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Usage:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    if _SessionLocal is None:
        msg = "Database not initialized. Call init_db() first."
        raise RuntimeError(msg)

    db = _SessionLocal()
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
    if _SessionLocal is None:
        with _db_lock:
            if _SessionLocal is None:
                # Auto-initialize from settings if not yet done
                from grounded.api.config import get_settings

                settings = get_settings()
                init_db(settings.database_url)

    if _SessionLocal is None:
        msg = "Database not initialized. Call init_db() first."
        raise RuntimeError(msg)

    return _SessionLocal()


def dispose_db() -> None:
    """Dispose the database engine (for shutdown)."""
    global _engine, _SessionLocal  # skipcq: PYL-W0603
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
