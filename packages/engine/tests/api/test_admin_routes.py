"""Comprehensive tests for admin API route handlers."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from grounded.api.app import create_app
from grounded.api.database import get_db
from grounded.api.models import Base, Job, JobStatus, Tenant, TenantPlan

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


ADMIN_KEY = "test-admin-key-routes"
TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_ID_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture(autouse=True)
def _set_admin_env(monkeypatch):
    monkeypatch.setenv("GROUNDED_ADMIN_API_KEY", ADMIN_KEY)


@pytest.fixture
def admin_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _):
        c = dbapi_conn.cursor()
        c.execute("PRAGMA foreign_keys=ON")
        c.close()

    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = sf()

    tenant = Tenant(
        id=TENANT_ID,
        name="Org One",
        api_key_hash="hash1",
        plan=TenantPlan.FREE,
        rate_limit_daily=10,
        max_file_size_mb=25,
    )
    session.add(tenant)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def admin_client(admin_db: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def _db() -> Generator[Session, None, None]:
        try:
            yield admin_db
        finally:
            pass

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as tc:
        yield tc


def _headers():
    return {"X-Admin-Key": ADMIN_KEY}


# -----------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------


class TestAdminAuth:
    @staticmethod
    def test_no_key_returns_401(admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/admin/tenants")
        assert resp.status_code == 401

    @staticmethod
    def test_wrong_key_returns_401(admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/admin/tenants", headers={"X-Admin-Key": "wrong"})
        assert resp.status_code == 401

    @staticmethod
    def test_correct_key_passes(admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/admin/tenants", headers=_headers())
        assert resp.status_code == 200

    @staticmethod
    def test_admin_not_configured_503(admin_client: TestClient, monkeypatch) -> None:
        monkeypatch.setenv("GROUNDED_ADMIN_API_KEY", "")
        resp = admin_client.get("/api/v1/admin/tenants", headers={"X-Admin-Key": "something"})
        assert resp.status_code == 503


# -----------------------------------------------------------------------
# PATCH /api/v1/admin/tenants/{id}/plan
# -----------------------------------------------------------------------


class TestUpdatePlanRoute:
    @staticmethod
    def test_update_to_pro(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/plan",
            json={"plan": "growth"},
            headers=_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] is True
        assert data["plan"] == "growth"

    @staticmethod
    def test_update_to_enterprise(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/plan",
            json={"plan": "enterprise"},
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["plan"] == "enterprise"

    @staticmethod
    def test_invalid_plan_422(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/plan",
            json={"plan": "nonexistent"},
            headers=_headers(),
        )
        assert resp.status_code == 422

    @staticmethod
    def test_tenant_not_found_404(admin_client: TestClient) -> None:
        fake = "99999999-9999-9999-9999-999999999999"
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{fake}/plan",
            json={"plan": "growth"},
            headers=_headers(),
        )
        assert resp.status_code == 404

    @staticmethod
    def test_overage_settings_updated(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/plan",
            json={
                "plan": "growth",
                "overage_enabled": True,
                "overage_cap_cents": 5000,
            },
            headers=_headers(),
        )
        assert resp.status_code == 200

    @staticmethod
    def test_invalid_uuid_422(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/v1/admin/tenants/bad-uuid/plan",
            json={"plan": "growth"},
            headers=_headers(),
        )
        assert resp.status_code == 422


# -----------------------------------------------------------------------
# PATCH /api/v1/admin/tenants/{id}/stripe
# -----------------------------------------------------------------------


class TestUpdateStripeRoute:
    @staticmethod
    def test_set_stripe_ids(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/stripe",
            json={
                "stripe_customer_id": "cus_abc",
                "stripe_subscription_item_id": "si_def",
            },
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    @staticmethod
    def test_partial_update(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/stripe",
            json={"stripe_customer_id": "cus_only"},
            headers=_headers(),
        )
        assert resp.status_code == 200

    @staticmethod
    def test_tenant_not_found(admin_client: TestClient) -> None:
        fake = "99999999-9999-9999-9999-999999999999"
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{fake}/stripe",
            json={"stripe_customer_id": "cus_x"},
            headers=_headers(),
        )
        assert resp.status_code == 404


# -----------------------------------------------------------------------
# GET /api/v1/admin/tenants  (list)
# -----------------------------------------------------------------------


class TestListTenantsRoute:
    @staticmethod
    def test_list_tenants(admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/admin/tenants", headers=_headers()).json()
        assert data["total"] >= 1
        assert len(data["tenants"]) >= 1

    @staticmethod
    def test_tenant_detail_fields(admin_client: TestClient) -> None:
        t = admin_client.get("/api/v1/admin/tenants", headers=_headers()).json()["tenants"][0]
        for field in (
            "id",
            "name",
            "plan",
            "rate_limit_daily",
            "max_file_size_mb",
            "overage_enabled",
            "is_active",
            "created_at",
        ):
            assert field in t

    @staticmethod
    def test_pagination(admin_client: TestClient, admin_db: Session) -> None:
        # Add a second tenant
        t2 = Tenant(
            id=TENANT_ID_2,
            name="Org Two",
            api_key_hash="hash2",
            plan=TenantPlan.STARTER,
        )
        admin_db.add(t2)
        admin_db.commit()

        data = admin_client.get(
            "/api/v1/admin/tenants",
            params={"page": 1, "page_size": 1},
            headers=_headers(),
        ).json()
        assert data["total"] == 2
        assert len(data["tenants"]) == 1


# -----------------------------------------------------------------------
# GET /api/v1/admin/tenants/{id}  (detail)
# -----------------------------------------------------------------------


class TestGetTenantRoute:
    @staticmethod
    def test_get_detail(admin_client: TestClient) -> None:
        data = admin_client.get(f"/api/v1/admin/tenants/{TENANT_ID}", headers=_headers()).json()
        assert data["id"] == str(TENANT_ID)
        assert data["name"] == "Org One"

    @staticmethod
    def test_not_found(admin_client: TestClient) -> None:
        fake = "99999999-9999-9999-9999-999999999999"
        resp = admin_client.get(f"/api/v1/admin/tenants/{fake}", headers=_headers())
        assert resp.status_code == 404


# -----------------------------------------------------------------------
# PATCH /api/v1/admin/tenants/{id}/status
# -----------------------------------------------------------------------


class TestUpdateTenantStatusRoute:
    @staticmethod
    def test_deactivate(admin_client: TestClient) -> None:
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/status",
            json={"is_active": False},
            headers=_headers(),
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] is True

    @staticmethod
    def test_reactivate(admin_client: TestClient) -> None:
        admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/status",
            json={"is_active": False},
            headers=_headers(),
        )
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{TENANT_ID}/status",
            json={"is_active": True},
            headers=_headers(),
        )
        assert resp.status_code == 200

    @staticmethod
    def test_not_found(admin_client: TestClient) -> None:
        fake = "99999999-9999-9999-9999-999999999999"
        resp = admin_client.patch(
            f"/api/v1/admin/tenants/{fake}/status",
            json={"is_active": False},
            headers=_headers(),
        )
        assert resp.status_code == 404


# -----------------------------------------------------------------------
# API Key management
# -----------------------------------------------------------------------


class TestListApiKeysRoute:
    @staticmethod
    def test_list_empty(admin_client: TestClient) -> None:
        data = admin_client.get(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys", headers=_headers()
        ).json()
        assert data["keys"] == []

    @staticmethod
    def test_list_after_create(admin_client: TestClient) -> None:
        admin_client.post(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys",
            json={"label": "Key A"},
            headers=_headers(),
        )
        data = admin_client.get(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys", headers=_headers()
        ).json()
        assert len(data["keys"]) == 1
        assert data["keys"][0]["label"] == "Key A"


class TestCreateApiKeyRoute:
    @staticmethod
    def test_create_key(admin_client: TestClient) -> None:
        resp = admin_client.post(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys",
            json={"label": "My Key"},
            headers=_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("lpdf_")
        assert data["label"] == "My Key"
        assert "key_prefix" in data

    @staticmethod
    def test_create_key_default_label(admin_client: TestClient) -> None:
        resp = admin_client.post(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys",
            json={},
            headers=_headers(),
        )
        assert resp.status_code == 201
        assert resp.json()["label"] == "Default"

    @staticmethod
    def test_create_key_for_nonexistent_tenant(admin_client: TestClient) -> None:
        fake = "99999999-9999-9999-9999-999999999999"
        resp = admin_client.post(
            f"/api/v1/admin/tenants/{fake}/keys",
            json={"label": "No Tenant"},
            headers=_headers(),
        )
        assert resp.status_code == 404

    @staticmethod
    def test_raw_key_only_returned_once(admin_client: TestClient) -> None:
        """The raw key is in the create response but not in the list response."""
        create = admin_client.post(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys",
            json={"label": "Once"},
            headers=_headers(),
        )
        assert "raw_key" in create.json()

        listed = admin_client.get(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys", headers=_headers()
        ).json()["keys"][0]
        assert "raw_key" not in listed


class TestRevokeApiKeyRoute:
    @staticmethod
    def test_revoke_key(admin_client: TestClient, admin_db: Session) -> None:
        create = admin_client.post(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys",
            json={"label": "Revokable"},
            headers=_headers(),
        )
        key_id = create.json()["id"]
        resp = admin_client.delete(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys/{key_id}",
            headers=_headers(),
        )
        assert resp.status_code == 204

        # Key should no longer appear in active list
        listed = admin_client.get(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys", headers=_headers()
        ).json()
        assert len(listed["keys"]) == 0

    @staticmethod
    def test_revoke_nonexistent_404(admin_client: TestClient) -> None:
        fake_key = "99999999-9999-9999-9999-999999999999"
        resp = admin_client.delete(
            f"/api/v1/admin/tenants/{TENANT_ID}/keys/{fake_key}",
            headers=_headers(),
        )
        assert resp.status_code == 404


# -----------------------------------------------------------------------
# GET /api/v1/admin/jobs  (cross-tenant job list)
# -----------------------------------------------------------------------


class TestAdminListJobsRoute:
    @staticmethod
    def test_list_empty(admin_client: TestClient) -> None:
        data = admin_client.get("/api/v1/admin/jobs", headers=_headers()).json()
        assert data["total"] == 0
        assert data["jobs"] == []

    @staticmethod
    def test_list_with_jobs(admin_client: TestClient, admin_db: Session) -> None:
        from datetime import UTC, datetime

        job = Job(
            id=uuid.uuid4(),
            tenant_id=TENANT_ID,
            status=JobStatus.PENDING,
            profile_id="grounded-default",
            file_key="admin/test.pdf",
            file_name="admin-test.pdf",
            file_size=100,
            created_at=datetime.now(UTC),
        )
        admin_db.add(job)
        admin_db.commit()

        data = admin_client.get("/api/v1/admin/jobs", headers=_headers()).json()
        assert data["total"] == 1
        assert data["jobs"][0]["tenant_name"] == "Org One"

    @staticmethod
    def test_pagination(admin_client: TestClient, admin_db: Session) -> None:
        from datetime import UTC, datetime

        for i in range(5):
            admin_db.add(
                Job(
                    id=uuid.uuid4(),
                    tenant_id=TENANT_ID,
                    status=JobStatus.PENDING,
                    profile_id="grounded-default",
                    file_key=f"admin/test{i}.pdf",
                    file_name=f"test{i}.pdf",
                    file_size=100,
                    created_at=datetime.now(UTC),
                )
            )
        admin_db.commit()

        data = admin_client.get(
            "/api/v1/admin/jobs",
            params={"page": 1, "page_size": 2},
            headers=_headers(),
        ).json()
        assert data["total"] == 5
        assert len(data["jobs"]) == 2

    @staticmethod
    def test_job_summary_fields(admin_client: TestClient, admin_db: Session) -> None:
        from datetime import UTC, datetime

        admin_db.add(
            Job(
                id=uuid.uuid4(),
                tenant_id=TENANT_ID,
                status=JobStatus.COMPLETE,
                profile_id="grounded-strict",
                file_key="admin/fields.pdf",
                file_name="fields.pdf",
                file_size=999,
                created_at=datetime.now(UTC),
            )
        )
        admin_db.commit()

        j = admin_client.get("/api/v1/admin/jobs", headers=_headers()).json()["jobs"][0]
        for field in (
            "id",
            "tenant_id",
            "tenant_name",
            "status",
            "profile_id",
            "file_name",
            "created_at",
        ):
            assert field in j
