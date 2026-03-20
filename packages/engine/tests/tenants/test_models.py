"""Tests for tenant domain models."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.tenants.models import PLAN_LIMITS, TenantInfo, TenantPlan


class TestTenantPlan:
    def test_free_plan(self) -> None:
        assert TenantPlan.FREE.value == "free"

    def test_enterprise_plan(self) -> None:
        assert TenantPlan.ENTERPRISE.value == "enterprise"

    def test_all_plans_have_limits(self) -> None:
        for plan in TenantPlan:
            assert plan in PLAN_LIMITS
            limits = PLAN_LIMITS[plan]
            assert "rate_limit_daily" in limits
            assert "max_file_size_mb" in limits

    def test_enterprise_has_highest_limits(self) -> None:
        free_limits = PLAN_LIMITS[TenantPlan.FREE]
        enterprise_limits = PLAN_LIMITS[TenantPlan.ENTERPRISE]
        assert enterprise_limits["rate_limit_daily"] > free_limits["rate_limit_daily"]
        assert enterprise_limits["max_file_size_mb"] > free_limits["max_file_size_mb"]


class TestTenantInfo:
    def test_create_tenant_info(self) -> None:
        tenant = TenantInfo(
            id="test-id",
            name="Test Tenant",
            plan=TenantPlan.FREE,
            api_key_hash="hash123",
            rate_limit_daily=10,
            max_file_size_mb=10,
        )
        assert tenant.id == "test-id"
        assert tenant.name == "Test Tenant"
        assert tenant.plan == TenantPlan.FREE
        assert tenant.is_active is True

    def test_default_active(self) -> None:
        tenant = TenantInfo(
            id="t1",
            name="T",
            plan=TenantPlan.FREE,
            api_key_hash="h",
            rate_limit_daily=10,
            max_file_size_mb=10,
        )
        assert tenant.is_active is True
        assert tenant.custom_profile_ids == []
