"""The legacy /api/v1/endpoints* surface returns 410 Gone (PR 26).

The dashboard endpoint page + ORM + custom_endpoints table were
hard-removed. The route module survives only as a 410-Gone shim
that points callers at /api/v1/workflows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_legacy_endpoints_list_returns_410(client: TestClient) -> None:
    resp = client.get("/api/v1/endpoints")
    assert resp.status_code == 410
    body = resp.json()
    assert "workflows" in body["detail"].lower()
    assert body["replacement"] == "/api/v1/workflows"
    assert "/api/v1/workflows" in resp.headers.get("Link", "")


def test_legacy_endpoints_create_returns_410(client: TestClient) -> None:
    resp = client.post("/api/v1/endpoints", json={"slug": "x", "profile_id": "y"})
    assert resp.status_code == 410


def test_legacy_endpoint_slug_path_returns_410(client: TestClient) -> None:
    """Catch-all path (any nested route under /endpoints/) returns 410
    so legacy submit URLs surface a structured error not 404."""
    resp = client.post("/api/v1/endpoints/some-slug/submit", json={})
    assert resp.status_code == 410


def test_legacy_endpoint_get_by_id_returns_410(client: TestClient) -> None:
    resp = client.get("/api/v1/endpoints/abc")
    assert resp.status_code == 410


def test_legacy_endpoint_delete_returns_410(client: TestClient) -> None:
    resp = client.delete("/api/v1/endpoints/abc")
    assert resp.status_code == 410
