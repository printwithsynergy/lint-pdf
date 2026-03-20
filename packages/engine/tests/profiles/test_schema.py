"""Tests for VoyagePlan schema validation."""

from __future__ import annotations

# skipcq: PYL-R0201
import pytest
from pydantic import ValidationError

from grounded.profiles.schema import CheckConfig, ThresholdConfig, VoyagePlan


class TestThresholdConfig:
    def test_defaults(self) -> None:
        t = ThresholdConfig()
        assert t.min_dpi == 150.0
        assert t.tac_limit == 300.0
        assert t.min_bleed_mm == 3.0
        assert t.hairline_threshold == 0.25
        assert t.safety_margin_mm == 3.0

    def test_custom_values(self) -> None:
        t = ThresholdConfig(min_dpi=300.0, tac_limit=280.0)
        assert t.min_dpi == 300.0
        assert t.tac_limit == 280.0

    def test_negative_dpi_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ThresholdConfig(min_dpi=-1.0)


class TestCheckConfig:
    def test_defaults(self) -> None:
        c = CheckConfig()
        assert "GRD_*" in c.enabled
        assert "PDFX4-*" in c.enabled
        assert len(c.disabled) == 0
        assert len(c.severity_overrides) == 0

    def test_custom_disabled(self) -> None:
        c = CheckConfig(disabled=["GRD_IMG_002"])
        assert "GRD_IMG_002" in c.disabled


class TestVoyagePlan:
    def test_minimal(self) -> None:
        fp = VoyagePlan(name="Test")
        assert fp.name == "Test"
        assert fp.conformance is None
        assert fp.workflow == "CMYK"
        assert fp.version == "1.0"

    def test_full(self) -> None:
        fp = VoyagePlan(
            name="Full",
            description="Full profile",
            conformance="pdfx4",
            workflow="CMYK",
            thresholds=ThresholdConfig(min_dpi=300.0),
        )
        assert fp.conformance == "pdfx4"
        assert fp.thresholds.min_dpi == 300.0

    def test_json_round_trip(self) -> None:
        fp = VoyagePlan(name="Test", conformance="pdfx4")
        data = fp.model_dump()
        fp2 = VoyagePlan.model_validate(data)
        assert fp2.name == "Test"
        assert fp2.conformance == "pdfx4"


class TestCheckEnabled:
    def test_default_enables_all_grd(self) -> None:
        fp = VoyagePlan(name="Test")
        assert fp.is_check_enabled("GRD_IMG_001")
        assert fp.is_check_enabled("GRD_FONT_003")
        assert fp.is_check_enabled("PDFX4-001")

    def test_disabled_overrides_enabled(self) -> None:
        fp = VoyagePlan(
            name="Test",
            checks=CheckConfig(disabled=["GRD_IMG_002"]),
        )
        assert not fp.is_check_enabled("GRD_IMG_002")
        assert fp.is_check_enabled("GRD_IMG_001")

    def test_ignore_severity_disables(self) -> None:
        fp = VoyagePlan(
            name="Test",
            checks=CheckConfig(severity_overrides={"GRD_IMG_005": "ignore"}),
        )
        assert not fp.is_check_enabled("GRD_IMG_005")

    def test_pattern_matching(self) -> None:
        fp = VoyagePlan(
            name="Test",
            checks=CheckConfig(enabled=["GRD_IMG_*"], disabled=[]),
        )
        assert fp.is_check_enabled("GRD_IMG_001")
        assert not fp.is_check_enabled("GRD_FONT_001")

    def test_disable_pattern(self) -> None:
        fp = VoyagePlan(
            name="Test",
            checks=CheckConfig(disabled=["PDFX4-*"]),
        )
        assert not fp.is_check_enabled("PDFX4-001")
        assert fp.is_check_enabled("GRD_IMG_001")


class TestSeverityOverride:
    def test_no_override_returns_none(self) -> None:
        fp = VoyagePlan(name="Test")
        assert fp.get_severity_override("GRD_IMG_001") is None

    def test_override_returns_value(self) -> None:
        fp = VoyagePlan(
            name="Test",
            checks=CheckConfig(severity_overrides={"GRD_IMG_001": "advisory"}),
        )
        assert fp.get_severity_override("GRD_IMG_001") == "advisory"
