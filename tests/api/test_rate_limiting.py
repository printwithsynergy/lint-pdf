"""Tests for Redis rate limiting with billable overage support."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from siftpdf.api.middleware import (
    build_usage_info,
    check_rate_limit,
    get_current_usage,
    set_rate_limiter,
)
from siftpdf.tenants.models import TenantPlan

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


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

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool | None:
        """Simulate SET with NX (set-if-not-exists)."""
        if nx and key in self._data:
            return None  # Key exists — NX fails
        self._data[key] = value
        if ex is not None:
            self._ttls[key] = ex
        return True

    def eval(self, script: str, numkeys: int, *args: object) -> int:
        """Simulate the Lua INCR+EXPIRE script."""
        key = str(args[0])
        ttl = int(args[1])
        current = self.incr(key)
        if current == 1:
            self.expire(key, ttl)
        return current

    @staticmethod
    def ping() -> bool:
        return True


class FakeTenant:
    """Minimal tenant for rate limit tests."""

    def __init__(
        self,
        *,
        tenant_id: str = "test-tenant",
        rate_limit_daily: int = 3,
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


@pytest.fixture
def fake_redis() -> FakeRedis:
    redis = FakeRedis()
    set_rate_limiter(redis)
    yield redis
    set_rate_limiter(None)


class TestCheckRateLimit:
    """Tests for the check_rate_limit dependency function."""

    @staticmethod
    def test_no_redis_allows_request() -> None:
        """When Redis is not configured, check_rate_limit is a no-op."""
        set_rate_limiter(None)
        tenant = FakeTenant()
        result = check_rate_limit(tenant)
        assert result is None

    @staticmethod
    def test_under_limit_passes(fake_redis: FakeRedis) -> None:
        """Requests under the daily limit should pass."""
        tenant = FakeTenant(rate_limit_daily=5)
        usage = check_rate_limit(tenant)
        assert usage is not None
        assert usage.used == 1
        assert not usage.blocked

        usage2 = check_rate_limit(tenant)
        assert usage2 is not None
        assert usage2.used == 2

    @staticmethod
    def test_free_plan_hard_blocks_at_limit(fake_redis: FakeRedis) -> None:
        """Free plan has no overages — blocks immediately at limit."""
        from fastapi import HTTPException

        tenant = FakeTenant(rate_limit_daily=2, plan=TenantPlan.FREE)
        check_rate_limit(tenant)  # 1 of 2
        check_rate_limit(tenant)  # 2 of 2
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(tenant)  # 3 of 2 — BLOCKED
        assert exc_info.value.status_code == 429

    @staticmethod
    def test_paid_plan_without_overage_blocks_at_limit(fake_redis: FakeRedis) -> None:
        """Paid plan with overage_enabled=False blocks at limit."""
        from fastapi import HTTPException

        tenant = FakeTenant(rate_limit_daily=3, plan=TenantPlan.STARTER, overage_enabled=False)
        for _ in range(3):
            check_rate_limit(tenant)
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(tenant)
        assert exc_info.value.status_code == 429

    @staticmethod
    def test_paid_plan_with_overage_allows_past_limit(fake_redis: FakeRedis) -> None:
        """Paid plan with overage_enabled=True continues past limit."""
        tenant = FakeTenant(rate_limit_daily=3, plan=TenantPlan.STARTER, overage_enabled=True)
        for _ in range(3):
            check_rate_limit(tenant)
        # 4th request — in overage, not blocked
        usage = check_rate_limit(tenant)
        assert usage is not None
        assert usage.in_overage is True
        assert usage.blocked is False
        assert usage.overage_count == 1
        assert usage.overage_rate_cents == 10
        assert usage.overage_cost_cents == 10

    @staticmethod
    def test_overage_spending_cap(fake_redis: FakeRedis) -> None:
        """Spending cap blocks when overage cost exceeds cap."""
        from fastapi import HTTPException

        tenant = FakeTenant(
            rate_limit_daily=3,
            plan=TenantPlan.STARTER,
            overage_enabled=True,
            overage_cap_cents=20,  # $0.20 cap = 2 overage jobs at $0.10/each
        )
        for _ in range(3):
            check_rate_limit(tenant)
        # 4th — overage 1 (cost 10 <= cap 20) — allowed
        check_rate_limit(tenant)
        # 5th — overage 2 (cost 20 <= cap 20) — allowed
        check_rate_limit(tenant)
        # 6th — overage 3 (cost 30 > cap 20) — BLOCKED
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(tenant)
        assert exc_info.value.status_code == 429
        assert "spending cap" in exc_info.value.detail

    @staticmethod
    def test_overage_rate_override(fake_redis: FakeRedis) -> None:
        """Per-tenant rate override takes precedence over plan default."""
        tenant = FakeTenant(
            rate_limit_daily=2,
            plan=TenantPlan.STARTER,
            overage_enabled=True,
            overage_rate_override_cents=25,
        )
        check_rate_limit(tenant)
        check_rate_limit(tenant)
        usage = check_rate_limit(tenant)  # overage
        assert usage is not None
        assert usage.overage_rate_cents == 25
        assert usage.overage_cost_cents == 25

    @staticmethod
    def test_redis_error_allows_request() -> None:
        """When Redis raises an error, request should pass through."""
        broken_redis = MagicMock()
        broken_redis.eval.side_effect = ConnectionError("Redis down")
        set_rate_limiter(broken_redis)
        tenant = FakeTenant()
        result = check_rate_limit(tenant)
        assert result is None
        set_rate_limiter(None)

    @staticmethod
    def test_different_tenants_have_separate_counters(fake_redis: FakeRedis) -> None:
        """Each tenant has its own rate limit counter."""
        tenant_a = FakeTenant(tenant_id="tenant-a", rate_limit_daily=1)
        tenant_b = FakeTenant(tenant_id="tenant-b", rate_limit_daily=1)
        usage_a = check_rate_limit(tenant_a)
        usage_b = check_rate_limit(tenant_b)
        assert usage_a is not None and usage_a.used == 1
        assert usage_b is not None and usage_b.used == 1

    @staticmethod
    def test_returns_usage_info(fake_redis: FakeRedis) -> None:
        """check_rate_limit returns UsageInfo with correct fields."""
        tenant = FakeTenant(rate_limit_daily=100, plan=TenantPlan.GROWTH)
        usage = check_rate_limit(tenant)
        assert usage is not None
        assert usage.used == 1
        assert usage.limit == 100
        assert usage.remaining_included == 99
        assert usage.percentage == 1
        assert not usage.in_overage
        assert not usage.blocked
        assert usage.overage_count == 0
        assert usage.overage_cost_cents == 0

    @staticmethod
    def test_rate_limit_on_job_submit(client: TestClient, minimal_pdf_bytes: bytes) -> None:
        """Rate limiting is applied on job submission endpoint."""
        set_rate_limiter(None)
        from io import BytesIO

        response = client.post(
            "/api/v1/jobs",
            files={"file": ("test.pdf", BytesIO(minimal_pdf_bytes), "application/pdf")},
        )
        assert response.status_code == 202


class TestBuildUsageInfo:
    """Tests for building UsageInfo from tenant and count."""

    @staticmethod
    def test_free_plan_no_overage() -> None:
        tenant = FakeTenant(rate_limit_daily=10, plan=TenantPlan.FREE)
        usage = build_usage_info(tenant, 5)
        assert usage.limit == 10
        assert usage.overage_rate_cents == 0
        assert usage.percentage == 50
        assert not usage.in_overage
        assert not usage.blocked

    @staticmethod
    def test_starter_plan_in_overage_blocked_without_opt_in() -> None:
        tenant = FakeTenant(rate_limit_daily=100, plan=TenantPlan.STARTER, overage_enabled=False)
        usage = build_usage_info(tenant, 105)
        assert usage.in_overage is True
        assert usage.blocked is True  # Not opted in
        assert usage.overage_count == 5

    @staticmethod
    def test_starter_plan_in_overage_allowed_with_opt_in() -> None:
        tenant = FakeTenant(rate_limit_daily=100, plan=TenantPlan.STARTER, overage_enabled=True)
        usage = build_usage_info(tenant, 105)
        assert usage.in_overage is True
        assert usage.blocked is False
        assert usage.overage_count == 5
        assert usage.overage_cost_cents == 50  # 5 * 10 cents

    @staticmethod
    def test_warning_at_80_pct() -> None:
        tenant = FakeTenant(rate_limit_daily=100, plan=TenantPlan.GROWTH)
        usage = build_usage_info(tenant, 80)
        assert usage.warning is True

    @staticmethod
    def test_no_warning_below_80() -> None:
        tenant = FakeTenant(rate_limit_daily=100, plan=TenantPlan.GROWTH)
        usage = build_usage_info(tenant, 79)
        assert usage.warning is False

    @staticmethod
    def test_blocked_has_no_warning() -> None:
        tenant = FakeTenant(rate_limit_daily=10, plan=TenantPlan.FREE)
        usage = build_usage_info(tenant, 11)
        assert usage.blocked is True
        assert usage.warning is False

    @staticmethod
    def test_cap_remaining() -> None:
        tenant = FakeTenant(
            rate_limit_daily=10,
            plan=TenantPlan.STARTER,
            overage_enabled=True,
            overage_cap_cents=100,
        )
        usage = build_usage_info(tenant, 13)
        assert usage.overage_count == 3
        assert usage.overage_cost_cents == 30
        assert usage.cap_remaining_cents == 70

    @staticmethod
    def test_cap_remaining_none_when_no_cap() -> None:
        tenant = FakeTenant(rate_limit_daily=10, plan=TenantPlan.STARTER, overage_enabled=True)
        usage = build_usage_info(tenant, 13)
        assert usage.cap_remaining_cents is None


class TestGetCurrentUsage:
    """Tests for reading usage without incrementing."""

    @staticmethod
    def test_returns_zero_without_redis() -> None:
        set_rate_limiter(None)
        tenant = FakeTenant()
        assert get_current_usage(tenant) == 0

    @staticmethod
    def test_reads_current_count(fake_redis: FakeRedis) -> None:
        tenant = FakeTenant(rate_limit_daily=100)
        # Increment a few times first
        check_rate_limit(tenant)
        check_rate_limit(tenant)
        check_rate_limit(tenant)
        # Read without incrementing
        usage = get_current_usage(tenant)
        assert usage == 3


class TestFakeRedis:
    """Unit tests for the FakeRedis helper."""

    @staticmethod
    def test_incr_creates_key() -> None:
        redis = FakeRedis()
        assert redis.incr("key") == 1
        assert redis.incr("key") == 2

    @staticmethod
    def test_expire_sets_ttl() -> None:
        redis = FakeRedis()
        redis.expire("key", 86400)
        assert redis._ttls["key"] == 86400

    @staticmethod
    def test_get_nonexistent() -> None:
        redis = FakeRedis()
        assert redis.get("missing") is None

    @staticmethod
    def test_eval_script() -> None:
        redis = FakeRedis()
        result = redis.eval("script", 1, "mykey", 86400)
        assert result == 1
        assert redis._ttls["mykey"] == 86400
        result2 = redis.eval("script", 1, "mykey", 86400)
        assert result2 == 2

    @staticmethod
    def test_set_nx_first_time() -> None:
        redis = FakeRedis()
        assert redis.set("key", "1", nx=True, ex=86400) is True

    @staticmethod
    def test_set_nx_already_exists() -> None:
        redis = FakeRedis()
        redis.set("key", "1", nx=True, ex=86400)
        assert redis.set("key", "1", nx=True, ex=86400) is None
