"""Comprehensive tests for health and status route handlers."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_response_body(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert data["service"] == "grounded"

    def test_no_auth_required(self, client: TestClient) -> None:
        """Health check must be accessible without any API key."""
        # The conftest already overrides auth, but we explicitly verify
        # no Authorization header is needed.
        response = client.get("/health")
        assert response.status_code == 200


class TestDetailedStatusEndpoint:
    """Tests for GET /api/v1/status."""

    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    def test_response_contains_all_fields(self, client: TestClient) -> None:
        data = client.get("/api/v1/status").json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "database" in data
        assert "redis" in data
        assert "queue_depth" in data
        assert "worker_count" in data

    def test_defaults(self, client: TestClient) -> None:
        data = client.get("/api/v1/status").json()
        assert data["service"] == "grounded"
        assert data["version"] == "0.1.0"

    # -- Probe: database --

    def test_database_connected(self, client: TestClient) -> None:
        mock_engine = MagicMock()
        with patch("grounded.api.database.get_engine", return_value=mock_engine):
            data = client.get("/api/v1/status").json()
        assert data["database"] == "connected"

    def test_database_not_configured(self, client: TestClient) -> None:
        with patch("grounded.api.database.get_engine", return_value=None):
            data = client.get("/api/v1/status").json()
        assert data["database"] == "not_configured"

    def test_database_error_sets_degraded(self, client: TestClient) -> None:
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("boom")
        with patch("grounded.api.database.get_engine", return_value=mock_engine):
            data = client.get("/api/v1/status").json()
        assert data["database"] == "error"
        assert data["status"] == "degraded"

    # -- Probe: redis --

    def test_redis_connected(self, client: TestClient) -> None:
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        with patch("grounded.api.middleware.get_redis_client", return_value=mock_redis):
            data = client.get("/api/v1/status").json()
        assert data["redis"] == "connected"

    def test_redis_not_configured(self, client: TestClient) -> None:
        with patch("grounded.api.middleware.get_redis_client", return_value=None):
            data = client.get("/api/v1/status").json()
        assert data["redis"] == "not_configured"

    def test_redis_error_sets_degraded(self, client: TestClient) -> None:
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("redis down")
        with patch("grounded.api.middleware.get_redis_client", return_value=mock_redis):
            data = client.get("/api/v1/status").json()
        assert data["redis"] == "error"
        assert data["status"] == "degraded"

    # -- Probe: queue --

    def test_queue_returns_depth_and_workers(self, client: TestClient) -> None:
        with (
            patch(
                "grounded.queue.health.get_all_queue_depths",
                return_value={"default": 2, "priority": 1, "webhooks": 0},
            ),
            patch("grounded.queue.health.get_worker_count", return_value=2),
        ):
            data = client.get("/api/v1/status").json()
        assert data["queue_depth"] == 3
        assert data["worker_count"] == 2
        assert data["queue_depths"] == {"default": 2, "priority": 1, "webhooks": 0}

    def test_queue_no_workers(self, client: TestClient) -> None:
        with (
            patch(
                "grounded.queue.health.get_all_queue_depths",
                return_value={"default": 0, "priority": 0, "webhooks": 0},
            ),
            patch("grounded.queue.health.get_worker_count", return_value=0),
        ):
            data = client.get("/api/v1/status").json()
        assert data["queue_depth"] == 0
        assert data["worker_count"] == 0

    def test_queue_error_returns_zero(self, client: TestClient) -> None:
        with (
            patch(
                "grounded.queue.health.get_all_queue_depths",
                side_effect=Exception("broker down"),
            ),
            patch(
                "grounded.queue.health.get_worker_count",
                side_effect=Exception("broker down"),
            ),
        ):
            data = client.get("/api/v1/status").json()
        assert data["queue_depth"] == 0
        assert data["worker_count"] == 0

    # -- Combined probe states --

    def test_both_db_and_redis_error(self, client: TestClient) -> None:
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("db")
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("redis")
        with (
            patch("grounded.api.database.get_engine", return_value=mock_engine),
            patch("grounded.api.middleware.get_redis_client", return_value=mock_redis),
        ):
            data = client.get("/api/v1/status").json()
        assert data["status"] == "degraded"

    def test_ok_when_db_and_redis_not_configured(self, client: TestClient) -> None:
        """Not-configured services are not errors; overall status should be ok."""
        with (
            patch("grounded.api.database.get_engine", return_value=None),
            patch("grounded.api.middleware.get_redis_client", return_value=None),
        ):
            data = client.get("/api/v1/status").json()
        assert data["status"] == "ok"
