"""Tests for admin API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lintpdf.api.app import create_app
from lintpdf.api.database import get_db
from lintpdf.api.models import Base, Tenant, TenantPlan

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def _set_admin_key(monkeypatch):
    monkeypatch.setenv("LINTPDF_ADMIN_API_KEY", "test-admin-key")


@pytest.fixture
def admin_client() -> Generator[TestClient, None, None]:
    """Test client with admin endpoints (no tenant auth bypass)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()

    # Seed tenant
    import uuid

    tenant = Tenant(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="Test Org",
        api_key_hash="fakehash",
        plan=TenantPlan.FREE,
        rate_limit_daily=10,
        max_file_size_mb=25,
    )
    session.add(tenant)
    session.commit()

    app = create_app()

    def _override_get_db() -> Generator[Session, None, None]:
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as tc:
        yield tc

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


class TestAdminPlanUpdate:
    @staticmethod
    def test_requires_admin_key(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/v1/admin/tenants/11111111-1111-1111-1111-111111111111/plan",
            json={"plan": "growth"},
        )
        assert resp.status_code == 401

    @staticmethod
    def test_wrong_key(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/v1/admin/tenants/11111111-1111-1111-1111-111111111111/plan",
            json={"plan": "growth"},
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    @staticmethod
    def test_success(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/v1/admin/tenants/11111111-1111-1111-1111-111111111111/plan",
            json={"plan": "growth"},
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] is True
        assert data["plan"] == "growth"

    @staticmethod
    def test_invalid_plan(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/v1/admin/tenants/11111111-1111-1111-1111-111111111111/plan",
            json={"plan": "invalid"},
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert resp.status_code == 422

    @staticmethod
    def test_not_found(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/v1/admin/tenants/99999999-9999-9999-9999-999999999999/plan",
            json={"plan": "growth"},
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert resp.status_code == 404


class TestAdminStripeUpdate:
    @staticmethod
    def test_set_stripe_ids(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/v1/admin/tenants/11111111-1111-1111-1111-111111111111/stripe",
            json={
                "stripe_customer_id": "cus_abc123",
                "stripe_subscription_item_id": "si_def456",
            },
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True
