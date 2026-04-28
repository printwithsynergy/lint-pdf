"""Tests for the ``is_admin_only`` profile visibility filter (PR B Slot 2B).

The ``lintpdf-system-test`` profile force-enables every analyzer + every
AI category and is used by the audit harness. Tenants must NOT be able
to resolve it via the regular Bearer-token submit path; only the admin
override (X-Admin-Key) can.
"""

from __future__ import annotations

from dataclasses import dataclass

from lintpdf.profiles.registry import ProfileRegistry
from lintpdf.profiles.resolver import _tenant_qualifies


@dataclass
class _MockSystemProfile:
    """Minimal stand-in for the SystemProfile DB row — resolver only
    reads ``visibility_mode``, ``min_plan``, ``visible_tenant_ids``,
    and ``preflight_profile_json``."""

    visibility_mode: str
    min_plan: str | None
    visible_tenant_ids: list | None
    preflight_profile_json: dict


@dataclass
class _MockTenant:
    id: str = "t-1"
    plan: str = "starter"


# ── Visibility filter blocks admin-only profiles ────────────────────────


class TestVisibilityFilter:
    @staticmethod
    def test_admin_only_profile_invisible_to_tenant_with_visibility_all() -> None:
        sp = _MockSystemProfile(
            visibility_mode="all",
            min_plan=None,
            visible_tenant_ids=None,
            preflight_profile_json={"is_admin_only": True},
        )
        assert _tenant_qualifies(sp, _MockTenant()) is False

    @staticmethod
    def test_admin_only_profile_invisible_even_when_tenant_in_allowlist() -> None:
        """Belt-and-braces: even if visibility_mode=tenants and the tenant
        is on the allow list, is_admin_only still blocks them."""
        sp = _MockSystemProfile(
            visibility_mode="tenants",
            min_plan=None,
            visible_tenant_ids=["t-1"],
            preflight_profile_json={"is_admin_only": True},
        )
        assert _tenant_qualifies(sp, _MockTenant()) is False

    @staticmethod
    def test_non_admin_profile_unaffected() -> None:
        sp = _MockSystemProfile(
            visibility_mode="all",
            min_plan=None,
            visible_tenant_ids=None,
            preflight_profile_json={"is_admin_only": False},
        )
        assert _tenant_qualifies(sp, _MockTenant()) is True

    @staticmethod
    def test_missing_flag_treated_as_false() -> None:
        """Backwards-compat: profiles authored before the flag existed
        don't carry it; default to visible."""
        sp = _MockSystemProfile(
            visibility_mode="all",
            min_plan=None,
            visible_tenant_ids=None,
            preflight_profile_json={},
        )
        assert _tenant_qualifies(sp, _MockTenant()) is True


# ── Built-in profile loads correctly ────────────────────────────────────


class TestSystemTestProfile:
    @staticmethod
    def test_system_test_profile_registered() -> None:
        registry = ProfileRegistry()
        assert registry.has("lintpdf-system-test")

    @staticmethod
    def test_system_test_profile_carries_admin_only_flag() -> None:
        registry = ProfileRegistry()
        profile = registry.get("lintpdf-system-test")
        assert profile.is_admin_only is True

    @staticmethod
    def test_system_test_profile_enables_all_check_families() -> None:
        registry = ProfileRegistry()
        profile = registry.get("lintpdf-system-test")
        # Every prefix the engine ever emits should be enabled.
        enabled_patterns = profile.checks.enabled
        assert any(p.startswith("LPDF_") for p in enabled_patterns)
        assert any(p.startswith("PDFX4-") for p in enabled_patterns)
        assert any(p.startswith("AI_") for p in enabled_patterns)
        # And no disables that would suppress anything.
        assert profile.checks.disabled == []

    @staticmethod
    def test_system_test_profile_enables_all_ai_categories() -> None:
        registry = ProfileRegistry()
        profile = registry.get("lintpdf-system-test")
        assert profile.ai.enabled is True
        assert "all" in profile.ai.categories

    @staticmethod
    def test_default_profile_not_admin_only() -> None:
        """Sanity: the default profile must remain tenant-visible."""
        registry = ProfileRegistry()
        profile = registry.get("lintpdf-default")
        assert profile.is_admin_only is False


# ── is_admin_request soft helper ────────────────────────────────────────


class TestIsAdminRequest:
    @staticmethod
    def test_no_header_returns_false() -> None:
        from lintpdf.api.auth import is_admin_request

        assert is_admin_request(None) is False
        assert is_admin_request("") is False

    @staticmethod
    def test_wrong_key_returns_false() -> None:
        from lintpdf.api.auth import is_admin_request

        # Without an admin key configured we expect False (no leak).
        # When configured but mismatched we also expect False.
        assert is_admin_request("definitely-not-the-real-key") is False
