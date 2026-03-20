"""Tests for profile management endpoints."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestListProfiles:
    def test_list_profiles(self, client: TestClient) -> None:
        response = client.get("/api/v1/profiles")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert len(data["profiles"]) >= 9  # 9 builtins

    def test_list_profiles_has_expected_builtins(self, client: TestClient) -> None:
        response = client.get("/api/v1/profiles")
        data = response.json()
        profile_ids = [p["profile_id"] for p in data["profiles"]]
        assert "grounded-default" in profile_ids
        assert "grounded-strict" in profile_ids
        assert "gwg-2022-coated-offset" in profile_ids

    def test_profile_has_required_fields(self, client: TestClient) -> None:
        response = client.get("/api/v1/profiles")
        data = response.json()
        profile = data["profiles"][0]
        assert "profile_id" in profile
        assert "name" in profile
        assert "conformance" in profile
        assert "workflow" in profile


class TestGetProfile:
    def test_get_builtin_profile(self, client: TestClient) -> None:
        response = client.get("/api/v1/profiles/grounded-default")
        assert response.status_code == 200
        data = response.json()
        assert data["profile_id"] == "grounded-default"
        assert data["name"] == "LintPDF Default"
        assert "thresholds" in data
        assert "checks" in data

    def test_get_strict_profile(self, client: TestClient) -> None:
        response = client.get("/api/v1/profiles/grounded-strict")
        assert response.status_code == 200
        data = response.json()
        assert data["conformance"] == "pdfx4"
        assert data["thresholds"]["min_dpi"] == 300.0

    def test_get_missing_profile_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/profiles/nonexistent-profile")
        assert response.status_code == 404


class TestCreateProfile:
    def test_create_custom_profile(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-test-profile",
                "voyage_plan": {
                    "name": "My Custom Profile",
                    "workflow": "CMYK",
                    "thresholds": {"min_dpi": 200.0},
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["profile_id"] == "custom-test-profile"

    def test_created_profile_is_accessible(self, client: TestClient) -> None:
        client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-accessible",
                "voyage_plan": {"name": "Accessible"},
            },
        )
        response = client.get("/api/v1/profiles/custom-accessible")
        assert response.status_code == 200
        assert response.json()["name"] == "Accessible"

    def test_create_invalid_voyage_plan(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-bad",
                "voyage_plan": {"not_a_valid": "field"},
            },
        )
        assert response.status_code == 422

    def test_create_invalid_profile_id(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "INVALID ID WITH SPACES",
                "voyage_plan": {"name": "Bad ID"},
            },
        )
        assert response.status_code == 422


class TestDeleteProfile:
    def test_delete_custom_profile(self, client: TestClient) -> None:
        # Create first
        client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-to-delete",
                "voyage_plan": {"name": "Deletable"},
            },
        )
        response = client.delete("/api/v1/profiles/custom-to-delete")
        assert response.status_code == 204

    def test_delete_builtin_forbidden(self, client: TestClient) -> None:
        response = client.delete("/api/v1/profiles/grounded-default")
        assert response.status_code == 403

    def test_delete_nonexistent_404(self, client: TestClient) -> None:
        response = client.delete("/api/v1/profiles/nonexistent-profile")
        assert response.status_code == 404
