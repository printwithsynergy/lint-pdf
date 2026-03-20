"""Tests for rate limiting middleware (additional coverage beyond test_rate_limiting.py).

This module tests configure_rate_limiter, edge cases in UsageInfo properties,
and Redis client lifecycle management.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from grounded.api.middleware import (
    UsageInfo,
    build_usage_info,
    check_rate_limit,
    configure_rate_limiter,
    get_current_usage,
    get_redis_client,
    set_rate_limiter,
)
from grounded.tenants.models import TenantPlan


class FakeRedis:
    """Minimal fake Redis for rate limiting tests."""

    def __init__(self) -> None:
        self._data: dict[str, int | str] = {}
        self._ttls: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self._data[key] = int(self._data.get(key, 0)) + 1
        return int(self._data[key])

    def expire(self, key: str, ttl: int) -> None:
        self._ttls[key] = ttl

    def get(self, key: str) -> int | str | None:
        return self._data.get(key)

    def eval(self, script: str, numkeys: int, *args: object) -> int:
        key = str(args[0])
        ttl = int(args[1])
        current = self.incr(key)
        if current == 1:
            self.expire(key, ttl)
        return current


class FakeTenant:
    """Minimal tenant for rate limit tests."""

    def __init__(
        self,
        *,
        tenant_id: str = "test-tenant",
        rate_limit_daily: int = 10,
        plan: TenantPlan = TenantPlan.FREE,
        overage_enabled: bool = False,
        overage_cap_cents: int | None = None,
        overage_rate_override_cents: int | None = None,
    ) -> None:
        self.id = tenant_id
        self.rate_limit_daily = rate_limit_daily
        self.plan = plan
        self.overage_enabled = overage_enabled
        self.overage_cap_cents = overage_cap_cents
        self.overage_rate_override_cents = overage_rate_override_cents


@pytest.fixture(autouse=True)
def _reset_redis():
    """Reset Redis client before and after each test."""
    set_rate_limiter(None)
    yield
    set_rate_limiter(None)


@pytest.fixture
def fake_redis() -> FakeRedis:
    redis = FakeRedis()
    set_rate_limiter(redis)
    return redis


class TestConfigureRateLimiter:
    """Tests for configure_rate_limiter initialization."""

    @staticmethod
    def test_configure_sets_client() -> None:
        mock_redis_instance = MagicMock()
        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis.from_url.return_value = mock_redis_instance
        with patch.dict("sys.modules", {"redis": mock_redis_mod}):
            configure_rate_limiter("redis://localhost:6379/0")
            assert get_redis_client() is mock_redis_instance

    @staticmethod
    def test_configure_only_runs_once() -> None:
        """configure_rate_limiter is idempotent once a client is set."""
        existing = MagicMock()
        set_rate_limiter(existing)
        configure_rate_limiter("redis://localhost:6379/1")
        assert get_redis_client() is existing

    @staticmethod
    def test_set_and_get() -> None:
        client = MagicMock()
        set_rate_limiter(client)
        assert get_redis_client() is client

    @staticmethod
    def test_set_none_clears() -> None:
        set_rate_limiter(MagicMock())
        set_rate_limiter(None)
        assert get_redis_client() is None


class TestUsageInfoProperties:
    """Tests for UsageInfo computed properties."""

    @staticmethod
    def test_remaining_included_under_limit() -> None:
        usage = UsageInfo(
            used=3,
            limit=10,
            percentage=30,
            in_overage=False,
            overage_count=0,
            overage_rate_cents=0,
            overage_cost_cents=0,
            overage_enabled=False,
            overage_cap_cents=None,
            blocked=False,
        )
        assert usage.remaining_included == 7

    @staticmethod
    def test_remaining_included_at_limit() -> None:
        usage = UsageInfo(
            used=10,
            limit=10,
            percentage=100,
            in_overage=False,
            overage_count=0,
            overage_rate_cents=0,
            overage_cost_cents=0,
            overage_enabled=False,
            overage_cap_cents=None,
            blocked=False,
        )
        assert usage.remaining_included == 0

    @staticmethod
    def test_remaining_included_over_limit() -> None:
        usage = UsageInfo(
            used=15,
            limit=10,
            percentage=150,
            in_overage=True,
            overage_count=5,
            overage_rate_cents=10,
            overage_cost_cents=50,
            overage_enabled=True,
            overage_cap_cents=None,
            blocked=False,
        )
        assert usage.remaining_included == 0

    @staticmethod
    def test_cap_remaining_with_cap() -> None:
        usage = UsageInfo(
            used=15,
            limit=10,
            percentage=150,
            in_overage=True,
            overage_count=5,
            overage_rate_cents=10,
            overage_cost_cents=50,
            overage_enabled=True,
            overage_cap_cents=100,
            blocked=False,
        )
        assert usage.cap_remaining_cents == 50

    @staticmethod
    def test_cap_remaining_no_cap() -> None:
        usage = UsageInfo(
            used=15,
            limit=10,
            percentage=150,
            in_overage=True,
            overage_count=5,
            overage_rate_cents=10,
            overage_cost_cents=50,
            overage_enabled=True,
            overage_cap_cents=None,
            blocked=False,
        )
        assert usage.cap_remaining_cents is None

    @staticmethod
    def test_cap_remaining_exhausted() -> None:
        usage = UsageInfo(
            used=15,
            limit=10,
            percentage=150,
            in_overage=True,
            overage_count=5,
            overage_rate_cents=10,
            overage_cost_cents=100,
            overage_enabled=True,
            overage_cap_cents=100,
            blocked=True,
        )
        assert usage.cap_remaining_cents == 0

    @staticmethod
    def test_warning_at_threshold() -> None:
        usage = UsageInfo(
            used=80,
            limit=100,
            percentage=80,
            in_overage=False,
            overage_count=0,
            overage_rate_cents=0,
            overage_cost_cents=0,
            overage_enabled=False,
            overage_cap_cents=None,
            blocked=False,
        )
        assert usage.warning is True

    @staticmethod
    def test_no_warning_below_threshold() -> None:
        usage = UsageInfo(
            used=79,
            limit=100,
            percentage=79,
            in_overage=False,
            overage_count=0,
            overage_rate_cents=0,
            overage_cost_cents=0,
            overage_enabled=False,
            overage_cap_cents=None,
            blocked=False,
        )
        assert usage.warning is False

    @staticmethod
    def test_blocked_no_warning() -> None:
        """When blocked, warning should be False."""
        usage = UsageInfo(
            used=110,
            limit=100,
            percentage=110,
            in_overage=True,
            overage_count=10,
            overage_rate_cents=0,
            overage_cost_cents=0,
            overage_enabled=False,
            overage_cap_cents=None,
            blocked=True,
        )
        assert usage.warning is False


class TestBuildUsageInfo:
    """Tests for build_usage_info."""

    @staticmethod
    def test_under_limit() -> None:
        tenant = FakeTenant(rate_limit_daily=100, plan=TenantPlan.STARTER)
        usage = build_usage_info(tenant, 50)
        assert usage.used == 50
        assert usage.limit == 100
        assert usage.percentage == 50
        assert usage.in_overage is False
        assert usage.blocked is False

    @staticmethod
    def test_exactly_at_limit() -> None:
        tenant = FakeTenant(rate_limit_daily=100, plan=TenantPlan.FREE)
        usage = build_usage_info(tenant, 100)
        assert usage.percentage == 100
        assert usage.in_overage is False
        assert usage.blocked is False

    @staticmethod
    def test_over_limit_free_plan() -> None:
        tenant = FakeTenant(rate_limit_daily=10, plan=TenantPlan.FREE)
        usage = build_usage_info(tenant, 11)
        assert usage.in_overage is True
        assert usage.blocked is True
        assert usage.overage_rate_cents == 0

    @staticmethod
    def test_over_limit_paid_with_overage() -> None:
        tenant = FakeTenant(
            rate_limit_daily=10,
            plan=TenantPlan.GROWTH,
            overage_enabled=True,
        )
        usage = build_usage_info(tenant, 15)
        assert usage.in_overage is True
        assert usage.blocked is False
        assert usage.overage_count == 5
        assert usage.overage_rate_cents == 10
        assert usage.overage_cost_cents == 50

    @staticmethod
    def test_spending_cap_exceeded() -> None:
        tenant = FakeTenant(
            rate_limit_daily=10,
            plan=TenantPlan.STARTER,
            overage_enabled=True,
            overage_cap_cents=30,
        )
        # 14 used = 4 overage * 10 cents = 40 > 30 cap
        usage = build_usage_info(tenant, 14)
        assert usage.blocked is True
        assert usage.overage_cost_cents == 40

    @staticmethod
    def test_spending_cap_not_exceeded() -> None:
        tenant = FakeTenant(
            rate_limit_daily=10,
            plan=TenantPlan.STARTER,
            overage_enabled=True,
            overage_cap_cents=50,
        )
        # 13 used = 3 overage * 10 cents = 30 <= 50 cap
        usage = build_usage_info(tenant, 13)
        assert usage.blocked is False

    @staticmethod
    def test_overage_rate_override() -> None:
        tenant = FakeTenant(
            rate_limit_daily=10,
            plan=TenantPlan.STARTER,
            overage_enabled=True,
            overage_rate_override_cents=25,
        )
        usage = build_usage_info(tenant, 12)
        assert usage.overage_rate_cents == 25
        assert usage.overage_cost_cents == 50  # 2 * 25

    @staticmethod
    def test_zero_limit() -> None:
        tenant = FakeTenant(rate_limit_daily=0, plan=TenantPlan.FREE)
        usage = build_usage_info(tenant, 0)
        assert usage.percentage == 100


class TestCheckRateLimit:
    """Tests for check_rate_limit."""

    @staticmethod
    def test_no_redis_returns_none() -> None:
        tenant = FakeTenant()
        result = check_rate_limit(tenant)
        assert result is None

    @staticmethod
    def test_increments_counter(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(rate_limit_daily=100)
        usage1 = check_rate_limit(tenant)
        usage2 = check_rate_limit(tenant)
        assert usage1 is not None
        assert usage1.used == 1
        assert usage2 is not None
        assert usage2.used == 2

    @staticmethod
    def test_blocks_at_limit_free(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(rate_limit_daily=1, plan=TenantPlan.FREE)
        check_rate_limit(tenant)  # 1 of 1
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(tenant)  # 2 of 1 -> blocked
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    @staticmethod
    def test_429_headers(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(rate_limit_daily=1, plan=TenantPlan.FREE)
        check_rate_limit(tenant)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(tenant)
        headers = exc_info.value.headers
        assert headers["X-RateLimit-Limit"] == "1"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["X-RateLimit-Used"] == "2"
        assert headers["Retry-After"] == "86400"

    @staticmethod
    def test_spending_cap_detail_message(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(
            rate_limit_daily=2,
            plan=TenantPlan.STARTER,
            overage_enabled=True,
            overage_cap_cents=15,
        )
        check_rate_limit(tenant)  # 1 of 2
        check_rate_limit(tenant)  # 2 of 2
        check_rate_limit(tenant)  # 3 — overage 1, cost 10 <= cap 15
        # 4th call: overage 2, cost 20 > cap 15 -> blocked
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(tenant)
        assert "spending cap" in exc_info.value.detail

    @staticmethod
    def test_redis_error_allows_through() -> None:
        broken = MagicMock()
        broken.eval.side_effect = ConnectionError("down")
        set_rate_limiter(broken)
        tenant = FakeTenant()
        result = check_rate_limit(tenant)
        assert result is None

    @staticmethod
    def test_overage_returns_usage(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(
            rate_limit_daily=1,
            plan=TenantPlan.GROWTH,
            overage_enabled=True,
        )
        check_rate_limit(tenant)  # 1 of 1
        usage = check_rate_limit(tenant)  # 2 — in overage
        assert usage is not None
        assert usage.in_overage is True
        assert usage.blocked is False

    @staticmethod
    def test_separate_tenant_counters(fake_redis: FakeRedis) -> None:
        a = FakeTenant(tenant_id="a", rate_limit_daily=5)
        b = FakeTenant(tenant_id="b", rate_limit_daily=5)
        check_rate_limit(a)
        check_rate_limit(a)
        usage_b = check_rate_limit(b)
        assert usage_b is not None
        assert usage_b.used == 1  # independent counter


class TestGetCurrentUsage:
    """Tests for reading current usage count."""

    @staticmethod
    def test_no_redis_returns_zero() -> None:
        tenant = FakeTenant()
        assert get_current_usage(tenant) == 0

    @staticmethod
    def test_reads_without_incrementing(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(rate_limit_daily=100)
        check_rate_limit(tenant)
        check_rate_limit(tenant)
        # read-only
        count = get_current_usage(tenant)
        assert count == 2
        # Should still be 2 (no increment)
        count2 = get_current_usage(tenant)
        assert count2 == 2

    @staticmethod
    def test_redis_error_returns_zero() -> None:
        broken = MagicMock()
        broken.get.side_effect = ConnectionError("down")
        set_rate_limiter(broken)
        tenant = FakeTenant()
        assert get_current_usage(tenant) == 0

    @staticmethod
    def test_returns_zero_for_missing_key(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(tenant_id="no-activity")
        assert get_current_usage(tenant) == 0
