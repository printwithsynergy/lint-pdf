"""Tests for worker health monitoring."""

from __future__ import annotations

from lintpdf.queue.health import get_health_status


class TestHealthStatus:
    @staticmethod
    def test_health_status_returns_dict() -> None:
        # Without a running broker, should return degraded
        status = get_health_status()
        assert isinstance(status, dict)
        assert "status" in status
        assert "queue_depth" in status
        assert "worker_count" in status

    @staticmethod
    def test_health_status_no_broker() -> None:
        status = get_health_status()
        # Without Redis running, expect degraded (no workers)
        assert status["status"] == "degraded"
        assert status["worker_count"] == 0
