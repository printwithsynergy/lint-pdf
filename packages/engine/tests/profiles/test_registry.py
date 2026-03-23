"""Tests for ProfileRegistry."""

from __future__ import annotations

import pytest

from grounded.profiles.registry import ProfileNotFoundError, ProfileRegistry
from grounded.profiles.schema import PreflightProfile


class TestProfileRegistry:
    @staticmethod
    def test_register_and_get() -> None:
        registry = ProfileRegistry()
        fp = PreflightProfile(name="Custom")
        registry.register("custom", fp)
        assert registry.get("custom").name == "Custom"

    @staticmethod
    def test_get_missing_raises() -> None:
        registry = ProfileRegistry()
        with pytest.raises(ProfileNotFoundError):
            registry.get("nonexistent")

    @staticmethod
    def test_list_profiles() -> None:
        registry = ProfileRegistry()
        fp1 = PreflightProfile(name="A")
        fp2 = PreflightProfile(name="B")
        registry.register("profile-b", fp2)
        registry.register("profile-a", fp1)
        profiles = registry.list_profiles()
        # Should include builtins + custom, sorted
        assert "profile-a" in profiles
        assert "profile-b" in profiles

    @staticmethod
    def test_has() -> None:
        registry = ProfileRegistry()
        fp = PreflightProfile(name="Test")
        registry.register("test-profile", fp)
        assert registry.has("test-profile")
        assert not registry.has("nope")


class TestBuiltinProfiles:
    @staticmethod
    def test_builtins_load() -> None:
        registry = ProfileRegistry()
        profiles = registry.list_profiles()
        assert len(profiles) >= 9

    @staticmethod
    def test_known_builtins_exist() -> None:
        registry = ProfileRegistry()
        expected = [
            "lintpdf-default",
            "lintpdf-strict",
            "lintpdf-advisory-only",
            "gwg-2022-coated-offset",
            "gwg-2022-uncoated-offset",
            "gwg-2022-newspaper",
            "gwg-2022-digital-print",
            "gwg-2022-sign-display",
            "gwg-2022-packaging",
        ]
        for profile_id in expected:
            assert registry.has(profile_id), f"Missing builtin: {profile_id}"

    @staticmethod
    def test_builtin_coated_offset() -> None:
        registry = ProfileRegistry()
        fp = registry.get("gwg-2022-coated-offset")
        assert fp.conformance == "pdfx4"
        assert fp.thresholds.min_dpi == 250.0
        assert fp.thresholds.tac_limit == 300.0

    @staticmethod
    def test_builtin_newspaper() -> None:
        registry = ProfileRegistry()
        fp = registry.get("gwg-2022-newspaper")
        assert fp.thresholds.min_dpi == 170.0
        assert fp.thresholds.tac_limit == 240.0

    @staticmethod
    def test_builtin_sign_display() -> None:
        registry = ProfileRegistry()
        fp = registry.get("gwg-2022-sign-display")
        assert fp.thresholds.min_dpi == 72.0
        assert fp.workflow == "auto"

    @staticmethod
    def test_all_builtins_validate() -> None:
        registry = ProfileRegistry()
        for profile_id in registry.list_profiles():
            fp = registry.get(profile_id)
            assert fp.name, f"Profile {profile_id} has no name"
            assert fp.thresholds.min_dpi >= 0
