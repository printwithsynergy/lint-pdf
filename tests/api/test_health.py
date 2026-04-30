"""Tests for health and status endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestHealth:
    @staticmethod
    def test_health_check(client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "siftpdf"

    @staticmethod
    def test_detailed_status(client: TestClient) -> None:
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "siftpdf"
        assert data["version"] == "0.1.0"
        assert "database" in data
        assert "redis" in data
        assert "queue_depth" in data
        assert "worker_count" in data

    @staticmethod
    def test_status_all_healthy(client: TestClient) -> None:
        """When all probes succeed, status is ok."""
        mock_engine = MagicMock()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with (
            patch("siftpdf.api.database.get_engine", return_value=mock_engine),
            patch("siftpdf.api.middleware.get_redis_client", return_value=mock_redis),
        ):
            response = client.get("/api/v1/status")
            data = response.json()
            assert data["database"] == "connected"
            assert data["redis"] == "connected"
            assert data["status"] == "ok"

    @staticmethod
    def test_status_no_db_configured(client: TestClient) -> None:
        """When no DB engine exists, database shows not_configured."""
        with patch("siftpdf.api.database.get_engine", return_value=None):
            response = client.get("/api/v1/status")
            data = response.json()
            assert data["database"] == "not_configured"

    @staticmethod
    def test_status_no_redis_configured(client: TestClient) -> None:
        """When no Redis client exists, redis shows not_configured."""
        with patch("siftpdf.api.middleware.get_redis_client", return_value=None):
            response = client.get("/api/v1/status")
            data = response.json()
            assert data["redis"] == "not_configured"

    @staticmethod
    def test_status_db_error(client: TestClient) -> None:
        """When DB probe fails, status is degraded."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection refused")

        with patch("siftpdf.api.database.get_engine", return_value=mock_engine):
            response = client.get("/api/v1/status")
            data = response.json()
            assert data["database"] == "error"
            assert data["status"] == "degraded"

    @staticmethod
    def test_status_redis_error(client: TestClient) -> None:
        """When Redis probe fails, status is degraded."""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Redis down")

        with patch("siftpdf.api.middleware.get_redis_client", return_value=mock_redis):
            response = client.get("/api/v1/status")
            data = response.json()
            assert data["redis"] == "error"
            assert data["status"] == "degraded"
