"""Tests for ``GET /api/v1/ai/health``.

Verifies the endpoint's sole responsibility: translate
``lintpdf.audit.outage.is_outage()`` into a JSON status the viewer
can poll without authentication.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestAiHealth:
    @staticmethod
    def test_ok_when_outage_flag_clear(client: TestClient) -> None:
        with patch("lintpdf.api.routes.ai_health.is_outage", return_value=False):
            resp = client.get("/api/v1/ai/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}

    @staticmethod
    def test_degraded_when_outage_flag_set(client: TestClient) -> None:
        with patch("lintpdf.api.routes.ai_health.is_outage", return_value=True):
            resp = client.get("/api/v1/ai/health")
            assert resp.status_code == 200
            assert resp.json() == {"status": "degraded"}

    @staticmethod
    def test_unauthenticated(client: TestClient) -> None:
        """No API key required — the viewer polls from third-party origins."""
        with patch("lintpdf.api.routes.ai_health.is_outage", return_value=False):
            # Deliberately no X-Api-Key header.
            resp = client.get("/api/v1/ai/health")
            assert resp.status_code == 200
