"""Tests for tenant service (DB-backed)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:
    from collections.abc import Generator

from lintpdf.api.models import Base
from lintpdf.tenants.models import TenantPlan
from lintpdf.tenants.service import TenantService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """In-memory SQLite session for tenant service tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


class TestCreateTenant:
    @staticmethod
    def test_create_returns_tenant_and_key(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, api_key = service.create_tenant("Test Corp")
        assert tenant.name == "Test Corp"
        assert tenant.plan == TenantPlan.FREE
        assert api_key.startswith("lpdf_")

    @staticmethod
    def test_create_with_plan(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Growth Corp", plan=TenantPlan.GROWTH)
        assert tenant.plan == TenantPlan.GROWTH
        assert tenant.rate_limit_daily == 5000
        assert tenant.max_file_size_mb == 500

    @staticmethod
    def test_created_tenant_is_active(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Active Corp")
        assert tenant.is_active is True


class TestAuthenticate:
    @staticmethod
    def test_authenticate_valid_key(db_session: Session) -> None:
        service = TenantService(db_session)
        _, api_key = service.create_tenant("Auth Corp")
        tenant = service.authenticate(api_key)
        assert tenant is not None
        assert tenant.name == "Auth Corp"

    @staticmethod
    def test_authenticate_invalid_key(db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.authenticate("lpdf_invalid_key") is None

    @staticmethod
    def test_authenticate_inactive_tenant(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, api_key = service.create_tenant("Inactive Corp")
        service.deactivate_tenant(tenant.id)
        assert service.authenticate(api_key) is None


class TestGetTenant:
    @staticmethod
    def test_get_existing(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Get Corp")
        fetched = service.get_tenant(tenant.id)
        assert fetched is not None
        assert fetched.name == "Get Corp"

    @staticmethod
    def test_get_nonexistent(db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.get_tenant("00000000-0000-0000-0000-000000000001") is None

    @staticmethod
    def test_get_invalid_uuid(db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.get_tenant("not-a-uuid") is None


class TestDeactivate:
    @staticmethod
    def test_deactivate_existing(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Deactivate Corp")
        assert service.deactivate_tenant(tenant.id) is True
        assert service.get_tenant(tenant.id).is_active is False  # type: ignore[union-attr]

    @staticmethod
    def test_deactivate_nonexistent(db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.deactivate_tenant("00000000-0000-0000-0000-000000000001") is False

    @staticmethod
    def test_deactivate_invalid_uuid(db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.deactivate_tenant("not-a-uuid") is False


class TestRateLimits:
    @staticmethod
    def test_within_limit(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Rate Corp")
        assert service.check_rate_limit(tenant, 5) is True

    @staticmethod
    def test_at_limit(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Rate Corp")
        assert service.check_rate_limit(tenant, tenant.rate_limit_daily) is False

    @staticmethod
    def test_over_limit(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Rate Corp")
        assert service.check_rate_limit(tenant, tenant.rate_limit_daily + 1) is False


class TestFileSizeLimits:
    @staticmethod
    def test_within_limit(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Size Corp")
        assert service.check_file_size(tenant, 1024) is True

    @staticmethod
    def test_at_limit(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Size Corp")
        max_bytes = tenant.max_file_size_mb * 1024 * 1024
        assert service.check_file_size(tenant, max_bytes) is True

    @staticmethod
    def test_over_limit(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Size Corp")
        max_bytes = tenant.max_file_size_mb * 1024 * 1024
        assert service.check_file_size(tenant, max_bytes + 1) is False


class TestUpdatePlan:
    @staticmethod
    def test_upgrade_plan(db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Upgrade Corp")
        assert service.update_plan(tenant.id, TenantPlan.GROWTH) is True
        updated = service.get_tenant(tenant.id)
        assert updated is not None
        assert updated.plan == TenantPlan.GROWTH
        assert updated.rate_limit_daily == 5000

    @staticmethod
    def test_update_nonexistent(db_session: Session) -> None:
        service = TenantService(db_session)
        assert (
            service.update_plan("00000000-0000-0000-0000-000000000001", TenantPlan.GROWTH) is False
        )

    @staticmethod
    def test_update_invalid_uuid(db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.update_plan("not-a-uuid", TenantPlan.GROWTH) is False
