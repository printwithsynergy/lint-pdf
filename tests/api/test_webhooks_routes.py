"""Comprehensive tests for webhook management route handlers."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _create_webhook(
    client: TestClient,
    url: str = "https://example.com/hook",
    events: list[str] | None = None,
) -> dict:
    payload: dict = {"url": url}
    if events is not None:
        payload["events"] = events
    resp = client.post("/api/v1/webhooks", json=payload)
    assert resp.status_code == 201
    return resp.json()


# -----------------------------------------------------------------------
# POST /api/v1/webhooks  (create)
# -----------------------------------------------------------------------


class TestCreateWebhookRoute:
    @staticmethod
    def test_create_with_explicit_events(client: TestClient) -> None:
        data = _create_webhook(client, events=["job.completed"])
        assert data["url"] == "https://example.com/hook"
        assert data["events"] == ["job.completed"]
        assert data["is_active"] is True
        uuid.UUID(data["id"])  # Valid UUID

    @staticmethod
    def test_create_with_default_events(client: TestClient) -> None:
        data = _create_webhook(client)
        assert "job.completed" in data["events"]
        assert "job.failed" in data["events"]

    @staticmethod
    def test_create_has_created_at(client: TestClient) -> None:
        data = _create_webhook(client)
        assert "created_at" in data

    # -- URL validation --

    @staticmethod
    def test_http_url_rejected(client: TestClient) -> None:
        resp = client.post("/api/v1/webhooks", json={"url": "http://example.com/hook"})
        assert resp.status_code == 422
        assert "HTTPS" in resp.json()["detail"]

    @staticmethod
    def test_localhost_rejected(client: TestClient) -> None:
        resp = client.post("/api/v1/webhooks", json={"url": "https://localhost/hook"})
        assert resp.status_code == 422

    @staticmethod
    def test_127_0_0_1_rejected(client: TestClient) -> None:
        resp = client.post("/api/v1/webhooks", json={"url": "https://127.0.0.1/hook"})
        assert resp.status_code == 422

    @staticmethod
    def test_private_ip_rejected(client: TestClient) -> None:
        resp = client.post("/api/v1/webhooks", json={"url": "https://192.168.1.1/hook"})
        assert resp.status_code == 422

    @staticmethod
    def test_metadata_endpoint_rejected(client: TestClient) -> None:
        resp = client.post(
            "/api/v1/webhooks",
            json={"url": "https://metadata.google.internal/computeMetadata/v1/"},
        )
        assert resp.status_code == 422

    @staticmethod
    def test_ipv6_loopback_rejected(client: TestClient) -> None:
        resp = client.post("/api/v1/webhooks", json={"url": "https://[::1]/hook"})
        assert resp.status_code == 422

    @staticmethod
    def test_valid_public_url_accepted(client: TestClient) -> None:
        resp = client.post(
            "/api/v1/webhooks",
            json={"url": "https://hooks.slack.com/services/T00/B00/xxx"},
        )
        assert resp.status_code == 201


# -----------------------------------------------------------------------
# GET /api/v1/webhooks  (list)
# -----------------------------------------------------------------------


class TestListWebhooksRoute:
    @staticmethod
    def test_list_empty(client: TestClient) -> None:
        data = client.get("/api/v1/webhooks").json()
        assert data["webhooks"] == []

    @staticmethod
    def test_list_multiple(client: TestClient) -> None:
        _create_webhook(client, url="https://one.example.com/hook")
        _create_webhook(client, url="https://two.example.com/hook")
        data = client.get("/api/v1/webhooks").json()
        assert len(data["webhooks"]) == 2

    @staticmethod
    def test_list_contains_required_fields(client: TestClient) -> None:
        _create_webhook(client)
        wh = client.get("/api/v1/webhooks").json()["webhooks"][0]
        for field in ("id", "url", "events", "is_active", "created_at"):
            assert field in wh


# -----------------------------------------------------------------------
# PATCH /api/v1/webhooks/{webhook_id}  (update)
# -----------------------------------------------------------------------


class TestUpdateWebhookRoute:
    @staticmethod
    def test_update_url(client: TestClient) -> None:
        wh = _create_webhook(client)
        resp = client.patch(
            f"/api/v1/webhooks/{wh['id']}",
            json={"url": "https://new.example.com/hook"},
        )
        assert resp.status_code == 200
        assert resp.json()["url"] == "https://new.example.com/hook"

    @staticmethod
    def test_update_events(client: TestClient) -> None:
        wh = _create_webhook(client)
        resp = client.patch(
            f"/api/v1/webhooks/{wh['id']}",
            json={"events": ["job.failed"]},
        )
        assert resp.status_code == 200
        assert resp.json()["events"] == ["job.failed"]

    @staticmethod
    def test_deactivate(client: TestClient) -> None:
        wh = _create_webhook(client)
        resp = client.patch(
            f"/api/v1/webhooks/{wh['id']}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @staticmethod
    def test_reactivate(client: TestClient) -> None:
        wh = _create_webhook(client)
        client.patch(f"/api/v1/webhooks/{wh['id']}", json={"is_active": False})
        resp = client.patch(f"/api/v1/webhooks/{wh['id']}", json={"is_active": True})
        assert resp.json()["is_active"] is True

    @staticmethod
    def test_update_with_invalid_url(client: TestClient) -> None:
        wh = _create_webhook(client)
        resp = client.patch(
            f"/api/v1/webhooks/{wh['id']}",
            json={"url": "http://insecure.example.com/hook"},
        )
        assert resp.status_code == 422

    @staticmethod
    def test_update_with_private_url(client: TestClient) -> None:
        wh = _create_webhook(client)
        resp = client.patch(
            f"/api/v1/webhooks/{wh['id']}",
            json={"url": "https://10.0.0.1/hook"},
        )
        assert resp.status_code == 422

    @staticmethod
    def test_update_nonexistent_404(client: TestClient) -> None:
        fake = "00000000-0000-0000-0000-000000000000"
        resp = client.patch(
            f"/api/v1/webhooks/{fake}",
            json={"url": "https://example.com/x"},
        )
        assert resp.status_code == 404

    @staticmethod
    def test_update_invalid_uuid(client: TestClient) -> None:
        resp = client.patch(
            "/api/v1/webhooks/bad-id",
            json={"url": "https://example.com/x"},
        )
        assert resp.status_code == 422

    @staticmethod
    def test_partial_update_preserves_other_fields(client: TestClient) -> None:
        wh = _create_webhook(client, events=["job.completed", "job.failed"])
        # Only update is_active; events should remain
        resp = client.patch(f"/api/v1/webhooks/{wh['id']}", json={"is_active": False})
        data = resp.json()
        assert data["is_active"] is False
        assert data["events"] == ["job.completed", "job.failed"]
        assert data["url"] == "https://example.com/hook"


# -----------------------------------------------------------------------
# DELETE /api/v1/webhooks/{webhook_id}
# -----------------------------------------------------------------------


class TestDeleteWebhookRoute:
    @staticmethod
    def test_delete_success(client: TestClient) -> None:
        wh = _create_webhook(client)
        resp = client.delete(f"/api/v1/webhooks/{wh['id']}")
        assert resp.status_code == 204

    @staticmethod
    def test_deleted_webhook_gone(client: TestClient) -> None:
        wh = _create_webhook(client)
        client.delete(f"/api/v1/webhooks/{wh['id']}")
        assert len(client.get("/api/v1/webhooks").json()["webhooks"]) == 0

    @staticmethod
    def test_delete_nonexistent_404(client: TestClient) -> None:
        fake = "00000000-0000-0000-0000-000000000000"
        resp = client.delete(f"/api/v1/webhooks/{fake}")
        assert resp.status_code == 404

    @staticmethod
    def test_delete_invalid_uuid(client: TestClient) -> None:
        resp = client.delete("/api/v1/webhooks/bad-uuid")
        assert resp.status_code == 422

    @staticmethod
    def test_delete_one_preserves_others(client: TestClient) -> None:
        wh1 = _create_webhook(client, url="https://one.example.com/hook")
        wh2 = _create_webhook(client, url="https://two.example.com/hook")
        client.delete(f"/api/v1/webhooks/{wh1['id']}")
        remaining = client.get("/api/v1/webhooks").json()["webhooks"]
        assert len(remaining) == 1
        assert remaining[0]["id"] == wh2["id"]
