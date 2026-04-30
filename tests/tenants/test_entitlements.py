"""Unit tests for the AI-feature entitlement resolver."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from siftpdf.tenants.entitlements import (
    AI_FEATURE_FLAGS,
    TenantEntitlements,
    resolve_entitlements,
)
from siftpdf.tenants.models import TenantPlan


def _stub_tenant(**kw):
    defaults = {
        "plan": TenantPlan.SCALE.value,
        "entitlement_overrides": None,
        "ai_features": None,
        "rate_limit_daily": None,
        "max_file_size_mb": None,
        "monthly_ai_credits_override": None,
        "monthly_files_override": None,
    }
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _no_plan_tier(plan):
    return {}


class TestAiFeatures:
    @staticmethod
    def test_scale_plan_baseline_grants_packaging_stack() -> None:
        tenant = _stub_tenant(plan=TenantPlan.SCALE.value)
        with patch(
            "siftpdf.tenants.entitlements._plan_tier_overrides",
            side_effect=_no_plan_tier,
        ):
            ent = resolve_entitlements(tenant)
        assert "audit" in ent.ai_features
        assert "ocr" in ent.ai_features
        assert "dieline" in ent.ai_features
        assert "art_size" in ent.ai_features
        assert "legend" in ent.ai_features
        # Not in Scale:
        assert "similarity" not in ent.ai_features

    @staticmethod
    def test_growth_plan_grants_audit_only() -> None:
        tenant = _stub_tenant(plan=TenantPlan.GROWTH.value)
        with patch(
            "siftpdf.tenants.entitlements._plan_tier_overrides",
            side_effect=_no_plan_tier,
        ):
            ent = resolve_entitlements(tenant)
        assert ent.ai_features == frozenset({"audit"})

    @staticmethod
    def test_starter_gets_no_ai_features() -> None:
        tenant = _stub_tenant(plan=TenantPlan.STARTER.value)
        with patch(
            "siftpdf.tenants.entitlements._plan_tier_overrides",
            side_effect=_no_plan_tier,
        ):
            ent = resolve_entitlements(tenant)
        assert ent.ai_features == frozenset()

    @staticmethod
    def test_per_tenant_grant_is_unioned_with_plan_baseline() -> None:
        """A per-tenant grant adds to the plan baseline, never replaces it."""
        tenant = _stub_tenant(
            plan=TenantPlan.SCALE.value,
            ai_features=["similarity"],  # not in SCALE baseline
        )
        with patch(
            "siftpdf.tenants.entitlements._plan_tier_overrides",
            side_effect=_no_plan_tier,
        ):
            ent = resolve_entitlements(tenant)
        assert "similarity" in ent.ai_features
        # Plan baseline still present:
        assert "audit" in ent.ai_features
        assert "dieline" in ent.ai_features

    @staticmethod
    def test_unknown_flag_is_silently_dropped_from_tenant_column() -> None:
        """Garbage in the JSONB column should never land in effective set."""
        tenant = _stub_tenant(
            plan=TenantPlan.SCALE.value,
            ai_features=["bogus_flag", "audit"],
        )
        with patch(
            "siftpdf.tenants.entitlements._plan_tier_overrides",
            side_effect=_no_plan_tier,
        ):
            ent = resolve_entitlements(tenant)
        assert "bogus_flag" not in ent.ai_features
        assert "audit" in ent.ai_features

    @staticmethod
    def test_entitlement_overrides_json_ai_features_is_merged() -> None:
        tenant = _stub_tenant(
            plan=TenantPlan.GROWTH.value,
            entitlement_overrides={"ai_features": ["ocr"]},
        )
        with patch(
            "siftpdf.tenants.entitlements._plan_tier_overrides",
            side_effect=_no_plan_tier,
        ):
            ent = resolve_entitlements(tenant)
        # Growth baseline + per-tenant override.
        assert ent.ai_features == frozenset({"audit", "ocr"})

    @staticmethod
    def test_plan_tier_override_is_unioned() -> None:
        tenant = _stub_tenant(plan=TenantPlan.GROWTH.value)

        def fake_plan_tier(plan):
            return {"ai_features": ["dieline"]}

        with patch(
            "siftpdf.tenants.entitlements._plan_tier_overrides",
            side_effect=fake_plan_tier,
        ):
            ent = resolve_entitlements(tenant)
        assert ent.ai_features == frozenset({"audit", "dieline"})


class TestCanUse:
    @staticmethod
    def _ent(**kw):
        defaults = {
            "rate_limit_daily": 0,
            "max_file_size_mb": 0,
            "max_custom_profiles": 0,
            "overage_rate_cents": 0,
            "report_storage_mb": 0,
            "report_default_expiry_days": 0,
            "allowed_report_formats": [],
            "allowed_preflight_sources": [],
            "capability_fillin_enabled": False,
            "annotations_enabled": False,
            "webhooks_enabled": False,
            "whitelabel_enabled": False,
            "priority_processing": False,
            "custom_integrations": False,
            "custom_profiles": False,
            "max_webhooks": 0,
            "ai_enabled": True,
            "ai_features": frozenset(),
        }
        defaults.update(kw)
        return TenantEntitlements(**defaults)

    @staticmethod
    def test_master_switch_off_blocks_everything() -> None:
        ent = TestCanUse._ent(ai_enabled=False, ai_features=frozenset(AI_FEATURE_FLAGS))
        for flag in AI_FEATURE_FLAGS:
            assert ent.can_use(flag) is False, flag

    @staticmethod
    def test_grant_without_master_switch_still_blocked() -> None:
        ent = TestCanUse._ent(ai_enabled=False, ai_features=frozenset({"audit"}))
        assert ent.can_use("audit") is False

    @staticmethod
    def test_master_switch_on_without_grant_still_blocked() -> None:
        ent = TestCanUse._ent(ai_enabled=True, ai_features=frozenset())
        assert ent.can_use("audit") is False

    @staticmethod
    def test_both_on_allows() -> None:
        ent = TestCanUse._ent(ai_enabled=True, ai_features=frozenset({"audit", "ocr"}))
        assert ent.can_use("audit") is True
        assert ent.can_use("ocr") is True
        assert ent.can_use("dieline") is False

    @staticmethod
    def test_unknown_feature_always_false() -> None:
        ent = TestCanUse._ent(ai_enabled=True, ai_features=frozenset({"audit"}))
        assert ent.can_use("not_a_real_flag") is False
