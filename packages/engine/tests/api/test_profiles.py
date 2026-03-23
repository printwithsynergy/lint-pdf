"""Tests for profile management endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestListProfiles:
    @staticmethod
    def test_list_profiles(client: TestClient) -> None:
        response = client.get("/api/v1/profiles")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert len(data["profiles"]) >= 9  # 9 builtins

    @staticmethod
    def test_list_profiles_has_expected_builtins(client: TestClient) -> None:
        response = client.get("/api/v1/profiles")
        data = response.json()
        profile_ids = [p["profile_id"] for p in data["profiles"]]
        assert "lintpdf-default" in profile_ids
        assert "lintpdf-strict" in profile_ids
        assert "gwg-2022-coated-offset" in profile_ids

    @staticmethod
    def test_profile_has_required_fields(client: TestClient) -> None:
        response = client.get("/api/v1/profiles")
        data = response.json()
        profile = data["profiles"][0]
        assert "profile_id" in profile
        assert "name" in profile
        assert "conformance" in profile
        assert "workflow" in profile


class TestGetProfile:
    @staticmethod
    def test_get_builtin_profile(client: TestClient) -> None:
        response = client.get("/api/v1/profiles/lintpdf-default")
        assert response.status_code == 200
        data = response.json()
        assert data["profile_id"] == "lintpdf-default"
        assert data["name"] == "LintPDF Default"
        assert "thresholds" in data
        assert "checks" in data

    @staticmethod
    def test_get_strict_profile(client: TestClient) -> None:
        response = client.get("/api/v1/profiles/lintpdf-strict")
        assert response.status_code == 200
        data = response.json()
        assert data["conformance"] == "pdfx4"
        assert data["thresholds"]["min_dpi"] == 300.0

    @staticmethod
    def test_get_missing_profile_404(client: TestClient) -> None:
        response = client.get("/api/v1/profiles/nonexistent-profile")
        assert response.status_code == 404


class TestCreateProfile:
    @staticmethod
    def test_create_custom_profile(client: TestClient) -> None:
        response = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-test-profile",
                "preflight_profile": {
                    "name": "My Custom Profile",
                    "workflow": "CMYK",
                    "thresholds": {"min_dpi": 200.0},
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["profile_id"] == "custom-test-profile"

    @staticmethod
    def test_created_profile_is_accessible(client: TestClient) -> None:
        client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-accessible",
                "preflight_profile": {"name": "Accessible"},
            },
        )
        response = client.get("/api/v1/profiles/custom-accessible")
        assert response.status_code == 200
        assert response.json()["name"] == "Accessible"

    @staticmethod
    def test_create_invalid_preflight_profile(client: TestClient) -> None:
        response = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-bad",
                "preflight_profile": {"not_a_valid": "field"},
            },
        )
        assert response.status_code == 422

    @staticmethod
    def test_create_invalid_profile_id(client: TestClient) -> None:
        response = client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "INVALID ID WITH SPACES",
                "preflight_profile": {"name": "Bad ID"},
            },
        )
        assert response.status_code == 422


class TestDeleteProfile:
    @staticmethod
    def test_delete_custom_profile(client: TestClient) -> None:
        # Create first
        client.post(
            "/api/v1/profiles",
            json={
                "profile_id": "custom-to-delete",
                "preflight_profile": {"name": "Deletable"},
            },
        )
        response = client.delete("/api/v1/profiles/custom-to-delete")
        assert response.status_code == 204

    @staticmethod
    def test_delete_builtin_forbidden(client: TestClient) -> None:
        response = client.delete("/api/v1/profiles/lintpdf-default")
        assert response.status_code == 403

    @staticmethod
    def test_delete_nonexistent_404(client: TestClient) -> None:
        response = client.delete("/api/v1/profiles/nonexistent-profile")
        assert response.status_code == 404
