"""Comprehensive tests for health and status route handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /health."""

    @staticmethod
    def test_returns_200(client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    @staticmethod
    def test_response_body(client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert data["service"] == "lintpdf"

    @staticmethod
    def test_no_auth_required(client: TestClient) -> None:
        """Health check must be accessible without any API key."""
        # The conftest already overrides auth, but we explicitly verify
        # no Authorization header is needed.
        response = client.get("/health")
        assert response.status_code == 200


class TestDetailedStatusEndpoint:
    """Tests for GET /api/v1/status."""

    @staticmethod
    def test_returns_200(client: TestClient) -> None:
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    @staticmethod
    def test_response_contains_all_fields(client: TestClient) -> None:
        data = client.get("/api/v1/status").json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "database" in data
        assert "redis" in data
        assert "queue_depth" in data
        assert "worker_count" in data

    @staticmethod
    def test_defaults(client: TestClient) -> None:
        data = client.get("/api/v1/status").json()
        assert data["service"] == "lintpdf"
        assert data["version"] == "0.1.0"

    # -- Probe: database --

    @staticmethod
    def test_database_connected(client: TestClient) -> None:
        mock_engine = MagicMock()
        with patch("lintpdf.api.database.get_engine", return_value=mock_engine):
            data = client.get("/api/v1/status").json()
        assert data["database"] == "connected"

    @staticmethod
    def test_database_not_configured(client: TestClient) -> None:
        with patch("lintpdf.api.database.get_engine", return_value=None):
            data = client.get("/api/v1/status").json()
        assert data["database"] == "not_configured"

    @staticmethod
    def test_database_error_sets_degraded(client: TestClient) -> None:
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("boom")
        with patch("lintpdf.api.database.get_engine", return_value=mock_engine):
            data = client.get("/api/v1/status").json()
        assert data["database"] == "error"
        assert data["status"] == "degraded"

    # -- Probe: redis --

    @staticmethod
    def test_redis_connected(client: TestClient) -> None:
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        with patch("lintpdf.api.middleware.get_redis_client", return_value=mock_redis):
            data = client.get("/api/v1/status").json()
        assert data["redis"] == "connected"

    @staticmethod
    def test_redis_not_configured(client: TestClient) -> None:
        with patch("lintpdf.api.middleware.get_redis_client", return_value=None):
            data = client.get("/api/v1/status").json()
        assert data["redis"] == "not_configured"

    @staticmethod
    def test_redis_error_sets_degraded(client: TestClient) -> None:
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("redis down")
        with patch("lintpdf.api.middleware.get_redis_client", return_value=mock_redis):
            data = client.get("/api/v1/status").json()
        assert data["redis"] == "error"
        assert data["status"] == "degraded"

    # -- Probe: queue --

    @staticmethod
    def test_queue_returns_depth_and_workers(client: TestClient) -> None:
        with (
            patch(
                "lintpdf.queue.health.get_all_queue_depths",
                return_value={"default": 2, "priority": 1, "webhooks": 0},
            ),
            patch("lintpdf.queue.health.get_worker_count", return_value=2),
        ):
            data = client.get("/api/v1/status").json()
        assert data["queue_depth"] == 3
        assert data["worker_count"] == 2
        assert data["queue_depths"] == {"default": 2, "priority": 1, "webhooks": 0}

    @staticmethod
    def test_queue_no_workers(client: TestClient) -> None:
        with (
            patch(
                "lintpdf.queue.health.get_all_queue_depths",
                return_value={"default": 0, "priority": 0, "webhooks": 0},
            ),
            patch("lintpdf.queue.health.get_worker_count", return_value=0),
        ):
            data = client.get("/api/v1/status").json()
        assert data["queue_depth"] == 0
        assert data["worker_count"] == 0

    @staticmethod
    def test_queue_error_returns_zero(client: TestClient) -> None:
        with (
            patch(
                "lintpdf.queue.health.get_all_queue_depths",
                side_effect=Exception("broker down"),
            ),
            patch(
                "lintpdf.queue.health.get_worker_count",
                side_effect=Exception("broker down"),
            ),
        ):
            data = client.get("/api/v1/status").json()
        assert data["queue_depth"] == 0
        assert data["worker_count"] == 0

    # -- Combined probe states --

    @staticmethod
    def test_both_db_and_redis_error(client: TestClient) -> None:
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("db")
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("redis")
        with (
            patch("lintpdf.api.database.get_engine", return_value=mock_engine),
            patch("lintpdf.api.middleware.get_redis_client", return_value=mock_redis),
        ):
            data = client.get("/api/v1/status").json()
        assert data["status"] == "degraded"

    @staticmethod
    def test_ok_when_db_and_redis_not_configured(client: TestClient) -> None:
        """Not-configured services are not errors; overall status should be ok."""
        with (
            patch("lintpdf.api.database.get_engine", return_value=None),
            patch("lintpdf.api.middleware.get_redis_client", return_value=None),
        ):
            data = client.get("/api/v1/status").json()
        assert data["status"] == "ok"
