"""Tests for worker health monitoring."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.queue.health import get_health_status


class TestHealthStatus:
    def test_health_status_returns_dict(self) -> None:
        # Without a running broker, should return degraded/unhealthy
        status = get_health_status()
        assert isinstance(status, dict)
        assert "status" in status
        assert "queue_depth" in status
        assert "worker_count" in status

    def test_health_status_no_broker(self) -> None:
        status = get_health_status()
        # Without Redis running, expect degraded or unhealthy
        assert status["status"] in ("degraded", "unhealthy")
        assert status["worker_count"] == 0
