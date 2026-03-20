"""Tests for ProfileRegistry."""

from __future__ import annotations

# skipcq: PYL-R0201
import pytest

from grounded.profiles.registry import ProfileNotFoundError, ProfileRegistry
from grounded.profiles.schema import VoyagePlan


class TestProfileRegistry:
    def test_register_and_get(self) -> None:
        registry = ProfileRegistry()
        fp = VoyagePlan(name="Custom")
        registry.register("custom", fp)
        assert registry.get("custom").name == "Custom"

    def test_get_missing_raises(self) -> None:
        registry = ProfileRegistry()
        with pytest.raises(ProfileNotFoundError):
            registry.get("nonexistent")

    def test_list_profiles(self) -> None:
        registry = ProfileRegistry()
        fp1 = VoyagePlan(name="A")
        fp2 = VoyagePlan(name="B")
        registry.register("profile-b", fp2)
        registry.register("profile-a", fp1)
        profiles = registry.list_profiles()
        # Should include builtins + custom, sorted
        assert "profile-a" in profiles
        assert "profile-b" in profiles

    def test_has(self) -> None:
        registry = ProfileRegistry()
        fp = VoyagePlan(name="Test")
        registry.register("test-profile", fp)
        assert registry.has("test-profile")
        assert not registry.has("nope")


class TestBuiltinProfiles:
    def test_builtins_load(self) -> None:
        registry = ProfileRegistry()
        profiles = registry.list_profiles()
        assert len(profiles) >= 9

    def test_known_builtins_exist(self) -> None:
        registry = ProfileRegistry()
        expected = [
            "grounded-default",
            "grounded-strict",
            "grounded-advisory-only",
            "gwg-2022-coated-offset",
            "gwg-2022-uncoated-offset",
            "gwg-2022-newspaper",
            "gwg-2022-digital-print",
            "gwg-2022-sign-display",
            "gwg-2022-packaging",
        ]
        for profile_id in expected:
            assert registry.has(profile_id), f"Missing builtin: {profile_id}"

    def test_builtin_coated_offset(self) -> None:
        registry = ProfileRegistry()
        fp = registry.get("gwg-2022-coated-offset")
        assert fp.conformance == "pdfx4"
        assert fp.thresholds.min_dpi == 250.0
        assert fp.thresholds.tac_limit == 300.0

    def test_builtin_newspaper(self) -> None:
        registry = ProfileRegistry()
        fp = registry.get("gwg-2022-newspaper")
        assert fp.thresholds.min_dpi == 170.0
        assert fp.thresholds.tac_limit == 240.0

    def test_builtin_sign_display(self) -> None:
        registry = ProfileRegistry()
        fp = registry.get("gwg-2022-sign-display")
        assert fp.thresholds.min_dpi == 72.0
        assert fp.workflow == "auto"

    def test_all_builtins_validate(self) -> None:
        registry = ProfileRegistry()
        for profile_id in registry.list_profiles():
            fp = registry.get(profile_id)
            assert fp.name, f"Profile {profile_id} has no name"
            assert fp.thresholds.min_dpi >= 0
