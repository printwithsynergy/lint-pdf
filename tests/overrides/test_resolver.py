"""Unit tests for the universal per-call override resolver.

These cover the three public helpers in ``lintpdf.overrides.resolver``
and document the intended layering semantics: override wins,
``None`` leaves the profile value alone, empty string clears a cap.
"""

from __future__ import annotations

import pytest

from lintpdf.overrides import (
    AIOverrides,
    ChecksOverrides,
    ColorOverrides,
    EntitlementDenied,
    OverridesEnvelope,
    ReportOverrides,
    ViewerOverrides,
    apply_profile_overrides,
    enforce_report_entitlements,
    viewer_overrides_to_dict,
)
from lintpdf.profiles.schema import (
    AIFeatureConfig,
    CheckConfig,
    ColorConfig,
    PreflightProfile,
    ThresholdConfig,
)
from lintpdf.tenants.entitlements import TenantEntitlements


def _make_profile(**overrides: object) -> PreflightProfile:
    """Construct a baseline profile every test can mutate from."""
    base = {
        "name": "test-profile",
        "conformance": "pdfx4",
        "workflow": "CMYK",
        "checks": CheckConfig(
            enabled=["LPDF_*"],
            disabled=[],
            severity_overrides={"LPDF_IMG_001": "warning"},
            max_severity=None,
        ),
        "thresholds": ThresholdConfig(min_dpi=150.0, tac_limit=300.0),
        "ai": AIFeatureConfig(enabled=False, categories=["all"], features=[]),
        "color": ColorConfig(gamut_check=False),
    }
    base.update(overrides)
    return PreflightProfile(**base)


# ---------------------------------------------------------------------------
# apply_profile_overrides
# ---------------------------------------------------------------------------


class TestApplyProfileOverrides:
    def test_none_envelope_returns_profile_unchanged(self) -> None:
        profile = _make_profile()
        out = apply_profile_overrides(profile, None)
        assert out is profile

    def test_check_enabled_and_disabled_replace_lists(self) -> None:
        profile = _make_profile()
        env = OverridesEnvelope(
            checks=ChecksOverrides(
                enabled=["PDFX4-*", "LPDF_IMG_*"],
                disabled=["LPDF_TEXT_004"],
            )
        )
        out = apply_profile_overrides(profile, env)
        assert out.checks.enabled == ["PDFX4-*", "LPDF_IMG_*"]
        assert out.checks.disabled == ["LPDF_TEXT_004"]

    def test_severity_overrides_merge(self) -> None:
        profile = _make_profile()
        env = OverridesEnvelope(
            checks=ChecksOverrides(
                severity_overrides={
                    "LPDF_IMG_002": "advisory",
                    "LPDF_IMG_001": "error",  # overwrites baseline ``warning``
                }
            )
        )
        out = apply_profile_overrides(profile, env)
        assert out.checks.severity_overrides == {
            "LPDF_IMG_001": "error",
            "LPDF_IMG_002": "advisory",
        }

    def test_max_severity_empty_string_clears_cap(self) -> None:
        profile = _make_profile(
            checks=CheckConfig(
                enabled=["LPDF_*"],
                disabled=[],
                severity_overrides={},
                max_severity="warning",
            )
        )
        env = OverridesEnvelope(checks=ChecksOverrides(max_severity=""))
        out = apply_profile_overrides(profile, env)
        assert out.checks.max_severity is None

    def test_thresholds_dict_merge_drops_unknown_keys(self) -> None:
        profile = _make_profile()
        env = OverridesEnvelope(
            thresholds={
                "tac_limit": 280.0,  # known
                "min_dpi": 200.0,  # known
                "bogus_field": "zzz",  # unknown — must be dropped
            }
        )
        out = apply_profile_overrides(profile, env)
        assert out.thresholds.tac_limit == 280.0
        assert out.thresholds.min_dpi == 200.0
        # pydantic would reject ``bogus_field`` if we'd forwarded it;
        # silent drop means the rest still applied.
        assert not hasattr(out.thresholds, "bogus_field")

    def test_color_override_also_mirrors_onto_thresholds(self) -> None:
        # Analyzers read either ``profile.color.*`` OR
        # ``profile.thresholds.*`` depending on vintage; ensure a color
        # override propagates to both so every analyzer sees the same
        # value regardless of which field it looks up.
        profile = _make_profile()
        env = OverridesEnvelope(
            color=ColorOverrides(
                tac_limit=250.0,
                gamut_check=True,
                target_output_condition="FOGRA51",
            )
        )
        out = apply_profile_overrides(profile, env)
        assert out.color.tac_threshold == 250.0
        assert out.color.gamut_check is True
        assert out.color.target_condition == "FOGRA51"
        assert out.thresholds.tac_limit == 250.0
        assert out.thresholds.gamut_check is True
        assert out.thresholds.target_output_condition == "FOGRA51"

    def test_ai_overrides_apply(self) -> None:
        profile = _make_profile()
        env = OverridesEnvelope(
            ai=AIOverrides(
                enabled=True,
                categories=["barcode", "content_quality"],
                features=["wcag_contrast"],
                language_for_reports="de",
            )
        )
        out = apply_profile_overrides(profile, env)
        assert out.ai.enabled is True
        assert out.ai.categories == ["barcode", "content_quality"]
        assert out.ai.features == ["wcag_contrast"]
        assert out.ai.language_for_reports == "de"

    def test_conformance_and_workflow(self) -> None:
        profile = _make_profile()
        env = OverridesEnvelope(conformance="pdfa2b", workflow="RGB")
        out = apply_profile_overrides(profile, env)
        assert out.conformance == "pdfa2b"
        assert out.workflow == "RGB"

    def test_empty_conformance_clears_it(self) -> None:
        profile = _make_profile()
        env = OverridesEnvelope(conformance="")
        out = apply_profile_overrides(profile, env)
        assert out.conformance is None


# ---------------------------------------------------------------------------
# enforce_report_entitlements
# ---------------------------------------------------------------------------


def _entitlements(allowed: list[str]) -> TenantEntitlements:
    return TenantEntitlements(
        rate_limit_daily=1000,
        max_file_size_mb=1024,
        max_custom_profiles=10,
        overage_rate_cents=0,
        report_storage_mb=10_000,
        report_default_expiry_days=30,
        allowed_report_formats=allowed,
        allowed_preflight_sources=["upload", "endpoint", "webhook"],
        capability_fillin_enabled=True,
        annotations_enabled=True,
        webhooks_enabled=False,
        whitelabel_enabled=False,
        priority_processing=False,
        custom_integrations=False,
        custom_profiles=False,
        max_webhooks=0,
        ai_enabled=False,
    )


class TestEnforceReportEntitlements:
    def test_none_passes(self) -> None:
        out = enforce_report_entitlements(None, _entitlements(["html"]))
        assert out is None

    def test_allowed_formats_pass(self) -> None:
        ents = _entitlements(["html", "pdf", "json", "xml"])
        ov = ReportOverrides(formats=["html", "json"])
        assert enforce_report_entitlements(ov, ents) is ov

    def test_disallowed_format_raises_entitlement_denied(self) -> None:
        ents = _entitlements(["html", "pdf"])
        ov = ReportOverrides(formats=["annotated_pdf_markup"])
        with pytest.raises(EntitlementDenied) as exc:
            enforce_report_entitlements(ov, ents)
        assert "annotated_pdf_markup" in str(exc.value)
        assert "html" in str(exc.value)  # mentions what IS allowed


# ---------------------------------------------------------------------------
# viewer_overrides_to_dict
# ---------------------------------------------------------------------------


class TestViewerOverridesToDict:
    def test_none_returns_empty(self) -> None:
        assert viewer_overrides_to_dict(None) == {}

    def test_only_set_fields_survive(self) -> None:
        ov = ViewerOverrides(enable_separations=False, dark_mode=True)
        out = viewer_overrides_to_dict(ov)
        assert out == {"enable_separations": False, "dark_mode": True}
