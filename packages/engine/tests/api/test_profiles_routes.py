"""Comprehensive tests for profile management route handlers."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from grounded.api.models import CustomProfile

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

from tests.api.conftest import PLACEHOLDER_TENANT_ID

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _seed_custom_profile(
    db: Session,
    profile_id: str = "custom-seeded",
    name: str = "Seeded Profile",
) -> CustomProfile:
    row = CustomProfile(
        id=uuid.uuid4(),
        tenant_id=PLACEHOLDER_TENANT_ID,
        profile_id=profile_id,
        voyage_plan_json={"name": name, "workflow": "CMYK"},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# -----------------------------------------------------------------------
# GET /api/v1/profiles  (list)
# -----------------------------------------------------------------------


class TestListProfilesRoute:
    @staticmethod
    def test_returns_200(client: TestClient) -> None:
        assert client.get("/api/v1/profiles").status_code == 200

    @staticmethod
    def test_contains_builtins(client: TestClient) -> None:
        data = client.get("/api/v1/profiles").json()
        ids = [p["profile_id"] for p in data["profiles"]]
        assert "grounded-default" in ids
        assert "grounded-strict" in ids

    @staticmethod
    def test_builtins_marked_as_builtin(client: TestClient) -> None:
        data = client.get("/api/v1/profiles").json()
        for p in data["profiles"]:
            if p["profile_id"].startswith("grounded-"):
                assert p["is_builtin"] is True

    @staticmethod
    def test_includes_custom_profiles(client: TestClient, db_session: Session) -> None:
        _seed_custom_profile(db_session, "custom-listed")
        data = client.get("/api/v1/profiles").json()
        ids = [p["profile_id"] for p in data["profiles"]]
        assert "custom-listed" in ids

    @staticmethod
    def test_custom_profiles_not_builtin(client: TestClient, db_session: Session) -> None:
        _seed_custom_profile(db_session, "custom-flag")
        data = client.get("/api/v1/profiles").json()
        custom = [p for p in data["profiles"] if p["profile_id"] == "custom-flag"]
        assert custom[0]["is_builtin"] is False

    def test_malformed_custom_profile_skipped(
        self, client: TestClient, db_session: Session
    ) -> None:
        """A custom profile with invalid voyage_plan_json should be silently skipped."""
        row = CustomProfile(
            id=uuid.uuid4(),
            tenant_id=PLACEHOLDER_TENANT_ID,
            profile_id="custom-broken",
            voyage_plan_json={"invalid_field_only": True},
        )
        db_session.add(row)
        db_session.commit()
        data = client.get("/api/v1/profiles").json()
        ids = [p["profile_id"] for p in data["profiles"]]
        # Should still succeed, but broken profile is skipped
        assert "custom-broken" not in ids

    @staticmethod
    def test_profile_summary_fields(client: TestClient) -> None:
        data = client.get("/api/v1/profiles").json()
        p = data["profiles"][0]
        for field in ("profile_id", "name", "workflow", "is_builtin"):
            assert field in p


# -----------------------------------------------------------------------
# GET /api/v1/profiles/{profile_id}  (detail)
# -----------------------------------------------------------------------


class TestGetProfileRoute:
    @staticmethod
    def test_builtin_profile_detail(client: TestClient) -> None:
        resp = client.get("/api/v1/profiles/grounded-default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile_id"] == "grounded-default"
        assert data["is_builtin"] is True
        assert "checks" in data
        assert "thresholds" in data

    @staticmethod
    def test_custom_profile_detail(client: TestClient, db_session: Session) -> None:
        _seed_custom_profile(db_session, "custom-detail", name="Detail Profile")
        data = client.get("/api/v1/profiles/custom-detail").json()
        assert data["profile_id"] == "custom-detail"
        assert data["name"] == "Detail Profile"
        assert data["is_builtin"] is False

    @staticmethod
    def test_not_found_404(client: TestClient) -> None:
        resp = client.get("/api/v1/profiles/nonexistent-xyz")
        assert resp.status_code == 404

    @staticmethod
    def test_strict_profile_has_conformance(client: TestClient) -> None:
        data = client.get("/api/v1/profiles/grounded-strict").json()
        assert data["conformance"] == "pdfx4"


# -----------------------------------------------------------------------
# POST /api/v1/profiles  (create)
# -----------------------------------------------------------------------


class TestCreateProfileRoute:
    @staticmethod
    def test_create_success(client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-new-one",
                "voyage_plan": {"name": "New One", "workflow": "CMYK"},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["profile_id"] == "custom-new-one"

    @staticmethod
    def test_created_profile_retrievable(client: TestClient) -> None:
        client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-get-check",
                "voyage_plan": {"name": "Get Check"},
            },
        )
        resp = client.get("/api/v1/profiles/custom-get-check")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Check"

    @staticmethod
    def test_overwrite_existing_custom(client: TestClient) -> None:
        """Re-posting the same profile_id should update, not conflict."""
        client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-overwrite",
                "voyage_plan": {"name": "V1"},
            },
        )
        resp = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-overwrite",
                "voyage_plan": {"name": "V2"},
            },
        )
        assert resp.status_code == 201
        data = client.get("/api/v1/profiles/custom-overwrite").json()
        assert data["name"] == "V2"

    @staticmethod
    def test_cannot_overwrite_builtin_409(client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "grounded-default",
                "voyage_plan": {"name": "Hijack"},
            },
        )
        assert resp.status_code == 409
        assert "built-in" in resp.json()["detail"].lower()

    @staticmethod
    def test_invalid_profile_id_format(client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "HAS SPACES",
                "voyage_plan": {"name": "Bad ID"},
            },
        )
        assert resp.status_code == 422

    @staticmethod
    def test_invalid_voyage_plan(client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-bad-plan",
                "voyage_plan": {"no_valid_field": True},
            },
        )
        assert resp.status_code == 422

    @staticmethod
    def test_single_char_profile_id_rejected(client: TestClient) -> None:
        """Profile ID pattern requires at least two characters."""
        resp = client.post(
            "/api/v1/profiles",
            json={"profile_id": "x", "voyage_plan": {"name": "Short"}},
        )
        assert resp.status_code == 422


# -----------------------------------------------------------------------
# DELETE /api/v1/profiles/{profile_id}
# -----------------------------------------------------------------------


class TestDeleteProfileRoute:
    @staticmethod
    def test_delete_custom_profile(client: TestClient, db_session: Session) -> None:
        _seed_custom_profile(db_session, "custom-del-me")
        resp = client.delete("/api/v1/profiles/custom-del-me")
        assert resp.status_code == 204
        # Verify gone
        assert client.get("/api/v1/profiles/custom-del-me").status_code == 404

    @staticmethod
    def test_delete_builtin_forbidden(client: TestClient) -> None:
        resp = client.delete("/api/v1/profiles/grounded-default")
        assert resp.status_code == 403
        assert "built-in" in resp.json()["detail"].lower()

    @staticmethod
    def test_delete_nonexistent_404(client: TestClient) -> None:
        resp = client.delete("/api/v1/profiles/no-such-profile")
        assert resp.status_code == 404

    @staticmethod
    def test_delete_then_recreate(client: TestClient, db_session: Session) -> None:
        _seed_custom_profile(db_session, "custom-reuse")
        client.delete("/api/v1/profiles/custom-reuse")
        resp = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-reuse",
                "voyage_plan": {"name": "Reused"},
            },
        )
        assert resp.status_code == 201
