"""Tests for webhook management endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestCreateWebhook:
    @staticmethod
    def test_create_webhook(client: TestClient) -> None:
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/webhook",
                "events": ["job.completed"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com/webhook"
        assert data["events"] == ["job.completed"]
        assert data["is_active"] is True
        assert "id" in data

    @staticmethod
    def test_create_webhook_default_events(client: TestClient) -> None:
        response = client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/hook"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "job.completed" in data["events"]
        assert "job.failed" in data["events"]


class TestListWebhooks:
    @staticmethod
    def test_list_empty(client: TestClient) -> None:
        response = client.get("/api/v1/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert data["webhooks"] == []

    @staticmethod
    def test_list_after_create(client: TestClient) -> None:
        client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/hook1"},
        )
        client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/hook2"},
        )
        response = client.get("/api/v1/webhooks")
        data = response.json()
        assert len(data["webhooks"]) == 2


class TestUpdateWebhook:
    @staticmethod
    def test_update_url(client: TestClient) -> None:
        create = client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/old"},
        )
        webhook_id = create.json()["id"]
        response = client.patch(
            f"/api/v1/webhooks/{webhook_id}",
            json={"url": "https://example.com/new"},
        )
        assert response.status_code == 200
        assert response.json()["url"] == "https://example.com/new"

    @staticmethod
    def test_update_events(client: TestClient) -> None:
        create = client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/hook"},
        )
        webhook_id = create.json()["id"]
        response = client.patch(
            f"/api/v1/webhooks/{webhook_id}",
            json={"events": ["job.completed"]},
        )
        assert response.status_code == 200
        assert response.json()["events"] == ["job.completed"]

    @staticmethod
    def test_update_deactivate(client: TestClient) -> None:
        create = client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/hook"},
        )
        webhook_id = create.json()["id"]
        response = client.patch(
            f"/api/v1/webhooks/{webhook_id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    @staticmethod
    def test_update_nonexistent_404(client: TestClient) -> None:
        response = client.patch(
            "/api/v1/webhooks/00000000-0000-0000-0000-000000000000",
            json={"url": "https://example.com/new"},
        )
        assert response.status_code == 404

    @staticmethod
    def test_update_invalid_url_rejected(client: TestClient) -> None:
        create = client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/hook"},
        )
        webhook_id = create.json()["id"]
        response = client.patch(
            f"/api/v1/webhooks/{webhook_id}",
            json={"url": "http://example.com/insecure"},
        )
        assert response.status_code == 422


class TestDeleteWebhook:
    @staticmethod
    def test_delete_webhook(client: TestClient) -> None:
        create = client.post(
            "/api/v1/webhooks",
            json={"url": "https://example.com/hook"},
        )
        webhook_id = create.json()["id"]
        response = client.delete(f"/api/v1/webhooks/{webhook_id}")
        assert response.status_code == 204

        # Verify gone
        list_resp = client.get("/api/v1/webhooks")
        assert len(list_resp.json()["webhooks"]) == 0

    @staticmethod
    def test_delete_nonexistent(client: TestClient) -> None:
        response = client.delete("/api/v1/webhooks/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
