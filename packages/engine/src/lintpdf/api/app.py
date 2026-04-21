"""FastAPI application factory for LintPDF."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator  # noqa: TC003
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from lintpdf.api.routes import (
    admin,
    admin_warming,
    ai_config,
    ai_credits,
    ai_generate,
    ai_interpret,
    ai_presets,
    ai_usage,
    annotations,
    approvals,
    batch,
    branding,
    color_config,
    downloads,
    edge,
    endpoints,
    file_packs,
    health,
    import_mappings,
    jobs,
    profiles,
    reports,
    stripe_webhooks,
    trial,
    usage,
    user_ai_access,
    viewer,
    webhooks,
)

logger = logging.getLogger(__name__)


def _run_migrations(database_url: str) -> None:
    """Run Alembic migrations to head on startup, falling back to create_all."""
    from lintpdf.api.database import get_engine
    from lintpdf.api.models import Base

    engine = get_engine()

    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception:
        logger.exception("Failed to run Alembic migrations — falling back to create_all.")
        try:
            Base.metadata.create_all(engine)
            logger.info("Database tables created via create_all.")
            # Stamp alembic_version to head so future Alembic runs don't
            # try to re-run all migrations from scratch.
            try:
                from alembic import command
                from alembic.config import Config

                alembic_cfg = Config()
                alembic_cfg.set_main_option("script_location", "alembic")
                alembic_cfg.set_main_option("sqlalchemy.url", database_url)
                command.stamp(alembic_cfg, "head")
                logger.info("Alembic version stamped to head.")
            except Exception:
                logger.warning(
                    "Could not stamp alembic_version — future migrations may need manual intervention."
                )
        except Exception:
            logger.exception("create_all also failed.")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize and tear down resources."""
    from lintpdf.api.config import get_settings
    from lintpdf.api.logging_config import configure_logging

    # Install the structlog JSON renderer before anything else so the
    # migrations + rate-limiter setup log lines are already structured.
    configure_logging()

    settings = get_settings()

    database_url = os.environ.get(
        "DATABASE_URL",
        os.environ.get("LINTPDF_DATABASE_URL", settings.database_url),
    )
    from lintpdf.api.database import dispose_db, init_db

    if database_url:
        init_db(database_url)
        _run_migrations(database_url)

    # Initialize rate limiter with Redis
    redis_url = os.environ.get("LINTPDF_REDIS_URL", settings.redis_url)
    if redis_url:
        from lintpdf.api.middleware import configure_rate_limiter

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
        title="LintPDF",
        description="Detection-only PDF preflight engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=_lifespan,
    )

    # Request-ID middleware must run outside auth/idempotency so the
    # bound ``request_id`` contextvar is available to every downstream
    # logger. Adding via ``add_middleware`` puts it at the *outside* of
    # the ASGI stack (inner middleware wraps the user handler).
    from lintpdf.api.middleware import RequestIdMiddleware

    app.add_middleware(RequestIdMiddleware)

    # Mount routers
    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(profiles.router)
    app.include_router(webhooks.router)
    app.include_router(usage.router)
    app.include_router(reports.router)
    app.include_router(admin.router)
    app.include_router(admin_warming.router)
    app.include_router(trial.router)
    app.include_router(edge.router)
    app.include_router(viewer.router)
    app.include_router(branding.router)
    app.include_router(approvals.router)
    app.include_router(annotations.router, prefix="/api/v1/viewer")
    app.include_router(import_mappings.router)

    # AI feature routers
    app.include_router(ai_config.router)
    app.include_router(ai_credits.router)
    app.include_router(ai_usage.router)
    app.include_router(ai_presets.router)
    app.include_router(ai_generate.router)
    app.include_router(ai_interpret.router)
    # Legacy /api/v1/captains-log/* prefix kept as a deprecated alias so
    # existing integrations keep working after the rebrand. Hidden from
    # the public OpenAPI schema.
    app.include_router(ai_interpret.legacy_router)
    # Metered-resource counterparts to the AI credit endpoints.
    app.include_router(file_packs.router)
    # Stripe webhook endpoint handles metered-resource fulfillment
    # (checkout.session.completed) and plan-monthly grants (invoice.paid).
    app.include_router(stripe_webhooks.router)

    # Batch submission
    app.include_router(batch.router)

    # Custom endpoints, color config & user AI access routers
    app.include_router(endpoints.router)
    app.include_router(color_config.router, prefix="/api/v1")
    app.include_router(user_ai_access.router, prefix="/api/v1")

    # Desktop app downloads (R2-backed)
    app.include_router(downloads.router)

    # Dev auth (impersonation) — only when explicitly enabled
    from lintpdf.api.config import get_settings

    if get_settings().dev_auth_enabled:
        from lintpdf.api.routes import dev_auth

        app.include_router(dev_auth.router)
        logger.warning("DEV AUTH ENABLED — /api/v1/dev/* routes are active.")

    # Tenant-scoped OpenAPI slice. The full ``/openapi.json`` includes
    # /admin/* and /api/v1/trial/* -- routes customers can't call and
    # shouldn't see in their Swagger UI or Postman collection. This
    # endpoint returns the spec with those paths stripped so the
    # marketing-site Swagger + the tenant Postman collection stay
    # clean.
    def _is_tenant_route(path: str) -> bool:
        # Exclude admin surface, trial-submit plumbing, and the
        # intentionally-hidden Stripe webhook receiver (customers don't
        # invoke that -- Stripe does).
        blocked_prefixes = (
            "/api/v1/admin/",
            "/api/v1/trial/",
            "/api/v1/stripe/webhook",
            "/api/v1/dev/",
        )
        return not any(path.startswith(p) for p in blocked_prefixes)

    @app.get("/openapi.tenant.json", include_in_schema=False)
    def _tenant_openapi() -> dict[str, Any]:  # type: ignore[name-defined]
        from copy import deepcopy

        full = app.openapi()
        slim = deepcopy(full)
        slim["paths"] = {
            p: body for p, body in full["paths"].items() if _is_tenant_route(p)
        }
        slim.setdefault("info", {})
        slim["info"]["title"] = f"{slim['info'].get('title', 'LintPDF')} (Tenant API)"
        slim["info"]["description"] = (
            "Tenant-facing routes only. Admin + trial-submit endpoints are "
            "excluded. See api.lintpdf.com/openapi.json for the complete "
            "spec (admin key required)."
        )
        return slim

    return app
