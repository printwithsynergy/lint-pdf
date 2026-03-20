"""Tests for tenant service (DB-backed)."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:
    from collections.abc import Generator

from grounded.api.models import Base
from grounded.tenants.models import TenantPlan
from grounded.tenants.service import TenantService


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
    def test_create_returns_tenant_and_key(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, api_key = service.create_tenant("Test Corp")
        assert tenant.name == "Test Corp"
        assert tenant.plan == TenantPlan.FREE
        assert api_key.startswith("lpdf_")

    def test_create_with_plan(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Growth Corp", plan=TenantPlan.GROWTH)
        assert tenant.plan == TenantPlan.GROWTH
        assert tenant.rate_limit_daily == 5000
        assert tenant.max_file_size_mb == 500

    def test_created_tenant_is_active(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Active Corp")
        assert tenant.is_active is True


class TestAuthenticate:
    def test_authenticate_valid_key(self, db_session: Session) -> None:
        service = TenantService(db_session)
        _, api_key = service.create_tenant("Auth Corp")
        tenant = service.authenticate(api_key)
        assert tenant is not None
        assert tenant.name == "Auth Corp"

    def test_authenticate_invalid_key(self, db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.authenticate("lpdf_invalid_key") is None

    def test_authenticate_inactive_tenant(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, api_key = service.create_tenant("Inactive Corp")
        service.deactivate_tenant(tenant.id)
        assert service.authenticate(api_key) is None


class TestGetTenant:
    def test_get_existing(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Get Corp")
        fetched = service.get_tenant(tenant.id)
        assert fetched is not None
        assert fetched.name == "Get Corp"

    def test_get_nonexistent(self, db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.get_tenant("00000000-0000-0000-0000-000000000001") is None

    def test_get_invalid_uuid(self, db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.get_tenant("not-a-uuid") is None


class TestDeactivate:
    def test_deactivate_existing(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Deactivate Corp")
        assert service.deactivate_tenant(tenant.id) is True
        assert service.get_tenant(tenant.id).is_active is False  # type: ignore[union-attr]

    def test_deactivate_nonexistent(self, db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.deactivate_tenant("00000000-0000-0000-0000-000000000001") is False

    def test_deactivate_invalid_uuid(self, db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.deactivate_tenant("not-a-uuid") is False


class TestRateLimits:
    def test_within_limit(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Rate Corp")
        assert service.check_rate_limit(tenant, 5) is True

    def test_at_limit(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Rate Corp")
        assert service.check_rate_limit(tenant, tenant.rate_limit_daily) is False

    def test_over_limit(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Rate Corp")
        assert service.check_rate_limit(tenant, tenant.rate_limit_daily + 1) is False


class TestFileSizeLimits:
    def test_within_limit(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Size Corp")
        assert service.check_file_size(tenant, 1024) is True

    def test_at_limit(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Size Corp")
        max_bytes = tenant.max_file_size_mb * 1024 * 1024
        assert service.check_file_size(tenant, max_bytes) is True

    def test_over_limit(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Size Corp")
        max_bytes = tenant.max_file_size_mb * 1024 * 1024
        assert service.check_file_size(tenant, max_bytes + 1) is False


class TestUpdatePlan:
    def test_upgrade_plan(self, db_session: Session) -> None:
        service = TenantService(db_session)
        tenant, _ = service.create_tenant("Upgrade Corp")
        assert service.update_plan(tenant.id, TenantPlan.GROWTH) is True
        updated = service.get_tenant(tenant.id)
        assert updated is not None
        assert updated.plan == TenantPlan.GROWTH
        assert updated.rate_limit_daily == 5000

    def test_update_nonexistent(self, db_session: Session) -> None:
        service = TenantService(db_session)
        assert (
            service.update_plan("00000000-0000-0000-0000-000000000001", TenantPlan.GROWTH) is False
        )

    def test_update_invalid_uuid(self, db_session: Session) -> None:
        service = TenantService(db_session)
        assert service.update_plan("not-a-uuid", TenantPlan.GROWTH) is False
