"""Tests for tenant domain models."""

from __future__ import annotations

from lintpdf.tenants.models import PLAN_LIMITS, TenantInfo, TenantPlan


class TestTenantPlan:
    @staticmethod
    def test_free_plan() -> None:
        assert TenantPlan.FREE.value == "free"

    @staticmethod
    def test_enterprise_plan() -> None:
        assert TenantPlan.ENTERPRISE.value == "enterprise"

    @staticmethod
    def test_all_plans_have_limits() -> None:
        for plan in TenantPlan:
            assert plan in PLAN_LIMITS
            limits = PLAN_LIMITS[plan]
            assert "rate_limit_daily" in limits
            assert "max_file_size_mb" in limits

    @staticmethod
    def test_enterprise_has_highest_limits() -> None:
        free_limits = PLAN_LIMITS[TenantPlan.FREE]
        enterprise_limits = PLAN_LIMITS[TenantPlan.ENTERPRISE]
        assert enterprise_limits["rate_limit_daily"] > free_limits["rate_limit_daily"]
        assert enterprise_limits["max_file_size_mb"] > free_limits["max_file_size_mb"]

    @staticmethod
    def test_viewer_tier_forbids_engine_and_fillin_and_annotations_and_downloads() -> None:
        limits = PLAN_LIMITS[TenantPlan.VIEWER]
        assert "engine" not in limits["allowed_preflight_sources"]
        assert "minimal" in limits["allowed_preflight_sources"]
        assert "external" in limits["allowed_preflight_sources"]
        assert limits["capability_fillin_enabled"] is False
        assert limits["annotations_enabled"] is False
        assert limits["allowed_report_formats"] == []
        assert limits["webhooks_enabled"] is False

    @staticmethod
    def test_non_viewer_plans_retain_full_access() -> None:
        for plan in (
            TenantPlan.FREE,
            TenantPlan.STARTER,
            TenantPlan.GROWTH,
            TenantPlan.SCALE,
            TenantPlan.ENTERPRISE,
        ):
            limits = PLAN_LIMITS[plan]
            assert "engine" in limits["allowed_preflight_sources"]
            assert limits["capability_fillin_enabled"] is True
            assert limits["annotations_enabled"] is True
            assert len(limits["allowed_report_formats"]) > 0


class TestTenantInfo:
    @staticmethod
    def test_create_tenant_info() -> None:
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

    @staticmethod
    def test_default_active() -> None:
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
