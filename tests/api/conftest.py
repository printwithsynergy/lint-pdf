"""Shared fixtures for API tests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.app import create_app
from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import Base, Tenant, TenantPlan
from lintpdf.api.storage import InMemoryStorage, set_storage

if TYPE_CHECKING:
    from collections.abc import Generator

    from fastapi import FastAPI
    from sqlalchemy.orm import Session

PLACEHOLDER_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """In-memory SQLite session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable FK enforcement for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    # Seed placeholder tenant for job FK.
    # Use GROWTH plan so CRUD tests for profiles/webhooks/reports pass.
    # Tier-gating enforcement is tested separately.
    tenant = Tenant(
        id=PLACEHOLDER_TENANT_ID,
        name="Test Tenant",
        api_key_hash="testhash_placeholder",
        plan=TenantPlan.GROWTH,
        rate_limit_daily=5000,
        max_file_size_mb=500,
    )
    session.add(tenant)
    session.commit()

    # Phase 0.7 PR-B1+ — seed the 9 unified-config category Toggle rows
    # so route tests that write ToggleOverride rows don't fail the
    # ``toggle_overrides.toggle_id`` FK. Mirrors the production startup
    # lifespan ``seed_category_toggles`` hook.
    from lintpdf.tenants.toggle_registry import seed_category_toggles

    seed_category_toggles(session)
    session.commit()

    # Phase 0.7 PR-B4 — seed a minimal ``lintpdf-default`` system
    # profile so route tests that submit jobs / create endpoints with
    # ``profile_id='lintpdf-default'`` (the canonical production
    # default) pass the ``profile_exists_for_tenant`` check. The
    # ``seed_system_profiles_from_bundled`` startup hook only runs
    # when ``DATABASE_URL`` is set, which conftest disables; this
    # mirrors production by inserting the row directly. Other test
    # files that exercise additional system profiles seed them
    # themselves.
    from lintpdf.profiles.seed import seed_system_profiles_from_bundled

    seed_system_profiles_from_bundled(session)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def _disable_lifespan_services(monkeypatch):
    """Prevent the app lifespan from connecting to real Postgres/Redis."""
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("LINTPDF_DATABASE_URL", "")
    monkeypatch.setenv("LINTPDF_REDIS_URL", "")
    # Provide a ClamAV URL so scan_for_malware doesn't fail-closed in tests.
    # Individual tests that want to exercise ClamAV behavior override _clamd_mod.
    monkeypatch.setenv("LINTPDF_CLAMAV_URL", "mockclamav:3310")


# Audit-fix #3c -- the OSS engine no longer carries SaaS plan-tier
# baselines; the autouse fixture lives in ``tests/conftest.py`` so
# every test dir gets the canonical per-tier defaults via stub.


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Clear the ``get_settings`` lru_cache between tests.

    The singleton speeds up production hot paths but creates cross-test
    bleed: a test that ``monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", …)``
    would otherwise see the stale value baked by a prior test that
    imported the module first.
    """
    from lintpdf.api.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _mock_clamav_clean(monkeypatch, request):
    """Return a 'clean' ClamAV result by default so upload tests pass.

    Tests in ``test_upload_security.py`` assert real scan_for_malware behavior;
    they patch ``_clamd_mod`` themselves and override this default.
    """
    if "test_upload_security" in request.node.nodeid:
        return  # let the real tests exercise their own patches
    from unittest.mock import MagicMock

    mock_scanner = MagicMock()
    mock_scanner.instream.return_value = {"stream": ("OK", None)}
    mock_clamd = MagicMock()
    mock_clamd.ClamdNetworkSocket.return_value = mock_scanner
    monkeypatch.setattr("lintpdf.api.upload_security._clamd_mod", mock_clamd)


@pytest.fixture(autouse=True)
def _use_in_memory_storage():
    """Use InMemoryStorage for all API tests."""
    set_storage(InMemoryStorage())
    yield
    set_storage(InMemoryStorage())


@pytest.fixture(autouse=True)
def _mock_celery_delay(monkeypatch):
    """Prevent Celery tasks from actually dispatching during API tests."""
    from unittest.mock import MagicMock

    from lintpdf.queue import tasks

    monkeypatch.setattr(tasks.run_preflight, "delay", MagicMock())
    monkeypatch.setattr(tasks.run_preflight, "apply_async", MagicMock())


@pytest.fixture
def app(db_session: Session) -> FastAPI:
    """Create a fresh FastAPI app with test DB session."""
    from lintpdf.services.tenant_context import (
        TenantContext,
        set_tenant_context_service,
    )

    application = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    application.dependency_overrides[get_db] = _override_get_db

    # Materialise a fresh ``TenantContext`` from the seeded ORM row on
    # every call so test fixtures that mutate ``Tenant.plan`` etc.
    # (e.g. test_plan_gates.viewer_tenant) propagate through the
    # auth dep + service lookups within the same test.
    def _build_context_from_row(row) -> TenantContext:  # type: ignore[no-untyped-def]
        return TenantContext(
            id=row.id,
            name=row.name or "",
            is_active=bool(row.is_active),
            plan=str(row.plan),
            rate_limit_daily=int(row.rate_limit_daily or 0),
            max_file_size_mb=int(row.max_file_size_mb or 0),
            ai_features=list(row.ai_features or []),
            entitlement_overrides=row.entitlement_overrides,
            contact_email=row.contact_email,
            brand_name=row.brand_name,
            brand_custom_domain=row.brand_custom_domain,
            brand_custom_domain_verified=bool(row.brand_custom_domain_verified),
            app_custom_domain=row.app_custom_domain,
            app_custom_domain_verified=bool(row.app_custom_domain_verified),
            default_brand_profile_id=row.default_brand_profile_id,
            default_profile_id=row.default_profile_id,
            unbranded_by_default=bool(row.unbranded_by_default),
            share_email_required=bool(row.share_email_required),
            webhook_signing_secret=row.webhook_signing_secret,
        )

    def _load_seeded_tenant() -> TenantContext | None:
        row = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        return _build_context_from_row(row) if row is not None else None

    def _override_get_current_tenant() -> TenantContext | None:
        return _load_seeded_tenant()

    application.dependency_overrides[get_current_tenant] = _override_get_current_tenant

    # Install a TenantContextService that re-reads the ORM each call so
    # mid-test mutations (plan downgrades etc.) propagate through every
    # downstream code path that goes through the service.
    class _ConftestTenantContextService:
        def load(self, tenant_id, db):  # type: ignore[no-untyped-def]
            row = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
            return _build_context_from_row(row) if row is not None else None

        def load_by_api_key_hash(self, api_key_hash, db):  # type: ignore[no-untyped-def]
            return _load_seeded_tenant()

    set_tenant_context_service(_ConftestTenantContextService())
    return application


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """HTTP test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n206\n%%EOF\n"
    )
