"""Tests for /api/v1/icc-profiles/active routes."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _valid_icc_bytes() -> bytes:
    """Build a 256-byte payload that satisfies the ICC magic check.

    Real ICC profiles have a 128-byte header with 'acsp' at offset 36;
    the rest of the bytes don't matter for the upload validator.
    """
    buf = bytearray(256)
    buf[36:40] = b"acsp"
    return bytes(buf)


def test_post_active_rejects_empty_file(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/icc-profiles/active",
        files={"file": ("empty.icc", io.BytesIO(b""), "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert "empty" in resp.json()["detail"].lower()


def test_post_active_rejects_non_icc_bytes(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/icc-profiles/active",
        files={
            "file": (
                "garbage.icc",
                io.BytesIO(b"not an icc profile at all" * 10),
                "application/octet-stream",
            )
        },
    )
    assert resp.status_code == 422
    assert "acsp" in resp.json()["detail"].lower()


def test_post_active_accepts_valid_icc(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/icc-profiles/active",
        files={"file": ("test.icc", io.BytesIO(_valid_icc_bytes()), "application/octet-stream")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["size_bytes"] == 256
    assert body["storage_key"].endswith("/active.icc")


def test_get_active_returns_null_when_unset(client: TestClient) -> None:
    resp = client.get("/api/v1/icc-profiles/active")
    # Either 200 with null body or whatever the storage returns; the
    # contract: storage download miss → returns null.
    assert resp.status_code == 200
    assert resp.json() is None


def test_get_active_returns_metadata_after_upload(client: TestClient) -> None:
    client.post(
        "/api/v1/icc-profiles/active",
        files={"file": ("test.icc", io.BytesIO(_valid_icc_bytes()), "application/octet-stream")},
    )
    resp = client.get("/api/v1/icc-profiles/active")
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["size_bytes"] == 256


def test_delete_active_clears_slot(client: TestClient) -> None:
    client.post(
        "/api/v1/icc-profiles/active",
        files={"file": ("test.icc", io.BytesIO(_valid_icc_bytes()), "application/octet-stream")},
    )
    resp = client.delete("/api/v1/icc-profiles/active")
    assert resp.status_code == 204
    # Round-trip: now empty.
    assert client.get("/api/v1/icc-profiles/active").json() is None


def test_delete_active_idempotent_when_already_clear(client: TestClient) -> None:
    """Deleting when no profile is set should be a no-op, not 404."""
    resp = client.delete("/api/v1/icc-profiles/active")
    assert resp.status_code == 204


def test_post_active_rejects_oversized(client: TestClient) -> None:
    """16 MB cap + 1 byte should 413."""
    big = bytearray(16 * 1024 * 1024 + 1)
    big[36:40] = b"acsp"
    resp = client.post(
        "/api/v1/icc-profiles/active",
        files={
            "file": ("big.icc", io.BytesIO(bytes(big)), "application/octet-stream"),
        },
    )
    assert resp.status_code == 413
