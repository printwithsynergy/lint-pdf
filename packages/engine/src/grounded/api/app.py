"""FastAPI application factory for Grounded."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator  # noqa: TC003
from contextlib import asynccontextmanager

from fastapi import FastAPI

from grounded.api.routes import (
    admin,
    ai_config,
    ai_credits,
    ai_generate,
    ai_interpret,
    ai_presets,
    ai_usage,
    health,
    jobs,
    profiles,
    reports,
    usage,
    webhooks,
)

logger = logging.getLogger(__name__)


def _run_migrations(database_url: str) -> None:
    """Run Alembic migrations to head on startup."""
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception:
        logger.exception("Failed to run database migrations — falling back to create_all.")
        from grounded.api.database import get_engine
        from grounded.api.models import Base

        Base.metadata.create_all(get_engine())


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize and tear down resources."""
    from grounded.api.config import get_settings

    settings = get_settings()

    database_url = os.environ.get(
        "DATABASE_URL",
        os.environ.get("GROUNDED_DATABASE_URL", settings.database_url),
    )
    from grounded.api.database import dispose_db, init_db

    if database_url:
        init_db(database_url)
        _run_migrations(database_url)

    # Initialize rate limiter with Redis
    redis_url = os.environ.get("GROUNDED_REDIS_URL", settings.redis_url)
    if redis_url:
        from grounded.api.middleware import configure_rate_limiter

        configure_rate_limiter(redis_url)

    yield

    if database_url:
        dispose_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Grounded",
        description="Detection-only PDF preflight engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=_lifespan,
    )

    # Mount routers
    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(profiles.router)
    app.include_router(webhooks.router)
    app.include_router(usage.router)
    app.include_router(reports.router)
    app.include_router(admin.router)

    # AI feature routers
    app.include_router(ai_config.router)
    app.include_router(ai_credits.router)
    app.include_router(ai_usage.router)
    app.include_router(ai_presets.router)
    app.include_router(ai_generate.router)
    app.include_router(ai_interpret.router)

    # Dev auth (impersonation) — only when explicitly enabled
    from grounded.api.config import get_settings

    if get_settings().dev_auth_enabled:
        from grounded.api.routes import dev_auth

        app.include_router(dev_auth.router)
        logger.warning("DEV AUTH ENABLED — /api/v1/dev/* routes are active.")

    return app
