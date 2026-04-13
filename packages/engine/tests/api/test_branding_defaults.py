"""Tests for the tenant-level default output branding endpoint."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from lintpdf.api.models import BrandProfile, BrandProfileType, Tenant

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID

ROUTE = "/api/v1/tenant/branding-defaults"


class TestGetBrandingDefaults:
    @staticmethod
    def test_fresh_tenant_reports_lintpdf_mode(client: TestClient) -> None:
        resp = client.get(ROUTE)
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "lintpdf"
        assert body["unbranded_by_default"] is False
        assert body["default_brand_profile_id"] is None

    @staticmethod
    def test_anonymous_tenant_reports_anonymous_mode(
        client: TestClient, db_session: Session
    ) -> None:
        t = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert t is not None
        t.unbranded_by_default = True
        db_session.commit()

        resp = client.get(ROUTE)
        assert resp.status_code == 200
        assert resp.json()["mode"] == "anonymous"


class TestPatchBrandingDefaults:
    @staticmethod
    def test_switch_to_anonymous_flips_tenant_flag(client: TestClient, db_session: Session) -> None:
        resp = client.patch(ROUTE, json={"mode": "anonymous"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mode"] == "anonymous"
        assert body["unbranded_by_default"] is True
        assert body["default_brand_profile_id"] is None

        db_session.expire_all()
        t = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert t is not None
        assert t.unbranded_by_default is True
        assert t.default_brand_profile_id is None

    @staticmethod
    def test_switch_to_lintpdf_clears_both(client: TestClient, db_session: Session) -> None:
        # Seed an anonymous default first.
        t = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert t is not None
        t.unbranded_by_default = True
        db_session.commit()

        resp = client.patch(ROUTE, json={"mode": "lintpdf"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "lintpdf"
        assert body["unbranded_by_default"] is False
        assert body["default_brand_profile_id"] is None

    @staticmethod
    def test_switch_to_profile_sets_default_brand_profile(
        client: TestClient, db_session: Session
    ) -> None:
        profile = BrandProfile(
            id=uuid.uuid4(),
            tenant_id=PLACEHOLDER_TENANT_ID,
            name="House Style",
            profile_type=BrandProfileType.CUSTOM,
            brand_name="House",
        )
        db_session.add(profile)
        db_session.commit()

        resp = client.patch(
            ROUTE,
            json={"mode": "profile", "brand_profile_id": str(profile.id)},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mode"] == "profile"
        assert body["unbranded_by_default"] is False
        assert body["default_brand_profile_id"] == str(profile.id)

        db_session.expire_all()
        t = db_session.query(Tenant).filter(Tenant.id == PLACEHOLDER_TENANT_ID).first()
        assert t is not None
        assert t.default_brand_profile_id == profile.id
        assert t.unbranded_by_default is False

    @staticmethod
    def test_profile_mode_without_id_rejected(client: TestClient) -> None:
        resp = client.patch(ROUTE, json={"mode": "profile"})
        assert resp.status_code == 422
        assert "brand_profile_id" in resp.json()["detail"]

    @staticmethod
    def test_profile_mode_with_bad_uuid_rejected(client: TestClient) -> None:
        resp = client.patch(ROUTE, json={"mode": "profile", "brand_profile_id": "nope"})
        assert resp.status_code == 422

    @staticmethod
    def test_profile_mode_with_foreign_profile_rejected(client: TestClient) -> None:
        # A random UUID — not owned by the placeholder tenant.
        resp = client.patch(
            ROUTE,
            json={"mode": "profile", "brand_profile_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    @staticmethod
    def test_unknown_mode_rejected(client: TestClient) -> None:
        resp = client.patch(ROUTE, json={"mode": "bogus"})
        assert resp.status_code == 422
