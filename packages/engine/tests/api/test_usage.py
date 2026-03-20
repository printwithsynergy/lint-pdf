"""Tests for the /api/v1/usage endpoint."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import TYPE_CHECKING

import pytest

from grounded.api.middleware import set_rate_limiter

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


class FakeRedis:
    """Minimal fake Redis for usage tests."""

    def __init__(self) -> None:
        self._data: dict[str, int | str] = {}
        self._ttls: dict[str, int] = {}

    def get(self, key: str) -> int | str | None:
        return self._data.get(key)

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self._data:
            return None
        self._data[key] = value
        if ex is not None:
            self._ttls[key] = ex
        return True

    def incr(self, key: str) -> int:
        self._data[key] = int(self._data.get(key, 0)) + 1
        return int(self._data[key])

    def expire(self, key: str, ttl: int) -> None:
        self._ttls[key] = ttl

    def eval(self, script: str, numkeys: int, *args: object) -> int:
        key = str(args[0])
        ttl = int(args[1])
        current = self.incr(key)
        if current == 1:
            self.expire(key, ttl)
        return current


@pytest.fixture
def fake_redis() -> FakeRedis:
    redis = FakeRedis()
    set_rate_limiter(redis)
    yield redis
    set_rate_limiter(None)


class TestUsageEndpoint:
    def test_returns_usage_without_redis(self, client: TestClient) -> None:
        set_rate_limiter(None)
        response = client.get("/api/v1/usage")
        assert response.status_code == 200
        data = response.json()
        assert data["used"] == 0
        assert data["plan"] == "growth"
        assert "limit" in data
        assert "remaining_included" in data
        assert "percentage" in data
        assert "in_overage" in data
        assert "overage_count" in data
        assert "overage_rate_cents" in data
        assert "overage_cost_cents" in data
        assert "overage_enabled" in data
        assert "blocked" in data
        assert "warning" in data

    def test_returns_usage_with_redis(self, client: TestClient, fake_redis: FakeRedis) -> None:
        response = client.get("/api/v1/usage")
        assert response.status_code == 200
        data = response.json()
        assert data["used"] == 0
        assert data["remaining_included"] == data["limit"]
        assert data["overage_cost_cents"] == 0
