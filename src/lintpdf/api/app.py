"""FastAPI application factory for LintPDF."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator  # noqa: TC003
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

# V-05: import the decisions package eagerly so its ORM model registers
# with ``Base.metadata`` before ``create_all`` runs in test fixtures and
# any code path queries the table.
from lintpdf import decisions as _decisions  # noqa: F401  (registration import)

# OSS engine routes — every route below ships in lintpdf. SaaS-only
# routes (admin, branding, billing, AI knobs, toggles, workflows,
# trial, approvals, webhooks, file_packs, ai_presets, etc.) were
# physically extracted to ``lintpdf_saas.api.routes`` over W5c-W5m;
# the SaaS shell at ``lintpdf_saas.api.app:create_app`` re-mounts
# them on top of the OSS app this module produces.
from lintpdf.api.routes import (
    ai_explain,
    ai_health,
    annotations,
    batch,
    decisions,
    epm_summary,
    health,
    icc_profiles,
    jobs,
    profiles,
    reports,
    viewer,
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
    import asyncio
    import os as _os
    from concurrent.futures import ThreadPoolExecutor

    from lintpdf.api.config import get_settings
    from lintpdf.api.logging_config import configure_logging

    # Install the structlog JSON renderer before anything else so the
    # migrations + rate-limiter setup log lines are already structured.
    configure_logging()

    # Bump the asyncio default-executor pool from the Python default
    # (min(32, cpu_count+4) ≈ 6 on a 2-vCPU Railway container) to a
    # value sized for the upload-to-R2 hot path. Every call to
    # ``loop.run_in_executor(None, storage.upload_pdf_stream, ...)``
    # borrows a thread from this pool; if it saturates, incoming
    # requests block waiting for a thread and /ready goes dark.
    # Overridable via LINTPDF_ASYNCIO_EXECUTOR_WORKERS.
    executor_workers = int(_os.environ.get("LINTPDF_ASYNCIO_EXECUTOR_WORKERS", "32"))
    asyncio.get_event_loop().set_default_executor(
        ThreadPoolExecutor(
            max_workers=executor_workers,
            thread_name_prefix="lintpdf-io",
        )
    )

    settings = get_settings()

    database_url = os.environ.get(
        "DATABASE_URL",
        os.environ.get("LINTPDF_DATABASE_URL", settings.database_url),
    )
    from lintpdf.api.database import dispose_db, init_db

    if database_url:
        init_db(database_url)
        _run_migrations(database_url)

        # Seed system_profiles from the bundled JSON directory. Runs
        # after migrations so the table always exists. Insert-if-absent
        # semantics mean admin edits + deletes persist across deploys.
        try:
            from lintpdf.api.database import get_db_session
            from lintpdf.profiles.seed import (
                seed_system_profiles_from_bundled,
            )

            _seed_db = get_db_session()
            try:
                seed_system_profiles_from_bundled(_seed_db)
            finally:
                _seed_db.close()
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "seed_system_profiles_from_bundled failed at startup — "
                "the bundled presets will not appear in /api/v1/profiles "
                "until this is resolved.",
            )

        # Phase 0.7 PR-B1 — register the 9 category-level toggle rows
        # that anchor the unified configuration cascade. Idempotent;
        # safe to call on every startup. Failures here don't block the
        # rest of the lifespan because the existing toggles registry
        # (from V-07/V-12 entitlement migration) keeps working without
        # the new categories — only consumers who specifically read the
        # new category rows degrade until the seed succeeds.
        try:
            from lintpdf.api.database import get_db_session
            from lintpdf.tenants.toggle_registry import seed_category_toggles

            _registry_db = get_db_session()
            try:
                created = seed_category_toggles(_registry_db)
                if created:
                    _registry_db.commit()
            finally:
                _registry_db.close()
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "seed_category_toggles failed at startup — unified-config"
                " category rows missing; new ConfigResolver categories"
                " will fall back to system defaults until resolved.",
            )

        # Phase 0.7 PR-B4-final — the v13 legacy-fold hook is gone. The
        # four tables it migrated (custom_profiles / brand_specs /
        # approval_chain_templates / tenant_import_mappings) are dropped
        # in alembic 046; nothing left to fold. ``custom_endpoints``
        # stays until endpoints.py is rewritten on top of Workflow rows
        # in a follow-up.

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

    # Wake-on-need middleware — inspects the incoming path and fires
    # fire-and-forget warm-up probes at scale-to-zero dependencies
    # that this endpoint is about to touch. By the time the handler
    # starts running (e.g. queuing a Celery task + reading from R2),
    # Modal / engine containers are already booting in parallel with
    # the handler's own work.
    from lintpdf.api.middleware_warming import WakeOnNeedMiddleware

    app.add_middleware(WakeOnNeedMiddleware)

    # CORS — allow browser clients on the marketing site (for
    # /swagger → /openapi.tenant.json) and the dashboard SPA to call
    # the tenant API. Added after RequestIdMiddleware so CORS sits
    # outermost in the ASGI stack and can respond to preflight
    # OPTIONS requests without running auth. Origins come from
    # LINTPDF_CORS_ALLOW_ORIGINS (comma-separated); "*" means any
    # origin. The API uses bearer-token auth only, no cookies, so
    # allow_credentials stays False.
    from fastapi.middleware.cors import CORSMiddleware

    from lintpdf.api.config import get_settings

    cors_origins = [
        origin.strip() for origin in get_settings().cors_allow_origins.split(",") if origin.strip()
    ]
    # Hard-fail in production if the operator set "*". A wildcard CORS
    # allowlist defeats the bearer-token-only contract: any browser
    # origin can hit the API. Tests + dev bypass via PYTEST_CURRENT_TEST
    # / pytest-imported / LINTPDF_ENVIRONMENT=development. The default
    # (lintpdf.com / app.lintpdf.com) is safe.
    import sys as _sys

    in_test = bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in _sys.modules
    if (
        "*" in cors_origins
        and not in_test
        and os.environ.get("LINTPDF_ENVIRONMENT", "production").lower() == "production"
    ):
        raise RuntimeError(
            "LINTPDF_CORS_ALLOW_ORIGINS contains '*' (wildcard). Refusing "
            "to start in production with an open CORS policy. Set "
            "LINTPDF_CORS_ALLOW_ORIGINS to an explicit comma-separated "
            "allowlist of origins, or set LINTPDF_ENVIRONMENT=development "
            "to bypass for local work."
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics (bulk-files step 11) — /metrics endpoint +
    # per-request duration/count instrumentation. Mounted unconditionally
    # so the control-plane-only service also exposes metrics.
    from lintpdf.api.metrics import mount_metrics

    mount_metrics(app)

    # Control-plane mode (bulk-files step 8).
    #
    # When LINTPDF_CONTROL_PLANE_ONLY=1 the process serves ONLY a
    # narrow operational router set — /ready, /api/v1/status,
    # /api/v1/admin/*, /api/v1/usage, /docs (schema). Upload/job/report
    # endpoints are not mounted. Point Railway's health check + the
    # operator dashboards at this service so an overloaded main API
    # (during a bulk-files burst, e.g. 100 concurrent uploads) can't
    # drag the operational plane down with it.
    #
    # Default (flag unset or "0"): behavior is unchanged — the single
    # container mounts every router. White-label tenant domains
    # continue to hit the full API with no routing change required.
    import os as _os

    control_plane_only = _os.environ.get("LINTPDF_CONTROL_PLANE_ONLY", "").lower() in (
        "1",
        "true",
        "yes",
    )

    # The OSS lintpdf package no longer ships any SaaS-only routes —
    # admin / billing / branding / trial / webhooks / approvals /
    # toggles / workflows / AI knobs / brand specs / etc. all live in
    # lintpdf_saas now (W5c-W5m physical extraction). The SaaS shell
    # at ``lintpdf_saas.api.app:create_app`` builds this OSS app and
    # then re-mounts the SaaS-only routers on top.
    #
    # ``LINTPDF_SAAS_MODE`` survives only as a no-op env var that
    # downstream tooling may still set. The OSS engine surface is the
    # only thing this app factory produces regardless of its value.

    # Mount routers
    app.include_router(health.router)  # /ready, /health — always mounted
    app.include_router(ai_health.router)  # /api/v1/ai/health — unauthenticated outage probe
    if not control_plane_only:
        app.include_router(jobs.router)
        app.include_router(ai_explain.router)  # Q-C4/C5 AI-Explain endpoint
        app.include_router(epm_summary.router)  # EPM candidacy summary
        app.include_router(decisions.router)  # V-05 decisions audit
        app.include_router(icc_profiles.router)  # substrate ICC profile (EPM-A1)
    app.include_router(profiles.router)
    # webhooks, admin, branding (with their cross-deps) extracted to
    # lintpdf_saas in W5l (PR thinkneverland/lint-pdf-saas#21). usage,
    # admin_health, admin_warming, edge, brand_specs, trial all
    # extracted in earlier W5 PRs.
    if not control_plane_only:
        app.include_router(reports.router)
        app.include_router(viewer.router)
    if not control_plane_only:
        # toggles + workflows + approvals + import_mappings: extracted
        # to lintpdf_saas in W5i (#18) and W5j (#19).
        app.include_router(annotations.router, prefix="/api/v1/viewer")

        # All SaaS-only routes — admin / billing / branding / trial /
        # webhooks / approvals / toggles / workflows / AI knobs /
        # brand_specs / endpoints / usage / file_packs / ai_presets — live
        # in lintpdf_saas now (W5c-W5m). The SaaS wrapper at
        # lintpdf_saas.api.app:create_app owns their registrations.

        # Batch submission — engine surface; available in OSS mode.
        app.include_router(batch.router)

        # endpoints: extracted to lintpdf_saas in W5g
        # (PR thinkneverland/lint-pdf-saas#16). color_config,
        # user_ai_access, downloads were extracted in W5e.

    # Dev auth was extracted to ``lintpdf_saas.api.routes.dev_auth`` in
    # W5c (PR thinkneverland/lint-pdf-saas#12). The SaaS wrapper at
    # ``lintpdf_saas.api.app:create_app`` is responsible for mounting
    # it now, gated on the same ``LINTPDF_DEV_AUTH_ENABLED`` setting.

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
        slim["paths"] = {p: body for p, body in full["paths"].items() if _is_tenant_route(p)}
        slim.setdefault("info", {})
        slim["info"]["title"] = f"{slim['info'].get('title', 'LintPDF')} (Tenant API)"
        slim["info"]["description"] = (
            "Tenant-facing routes only. Admin + trial-submit endpoints are "
            "excluded. See api.lintpdf.com/openapi.json for the complete "
            "spec (admin key required)."
        )
        return slim

    return app
