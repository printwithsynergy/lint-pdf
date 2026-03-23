"""Tests for OverprintAnalyzer — OP/op/OPM interaction checks."""

from __future__ import annotations

from grounded.analyzers.finding import Severity
from grounded.analyzers.overprint import OverprintAnalyzer
from grounded.semantic.events import (
    ColorChangedEvent,
    OpacityChangedEvent,
    OverprintChangedEvent,
)
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document() -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestOverprintOnNonCMYK:
    """Test GRD_OVER_001: overprint on non-CMYK color space."""

    @staticmethod
    def test_overprint_on_rgb() -> None:
        events = [
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                overprint_stroking=True,
            ),
            ColorChangedEvent(
                operator="RG",
                page_num=1,
                operator_index=1,
                stroking=True,
                color_space="DeviceRGB",
                color_values=(1.0, 0.0, 0.0),
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        op_findings = [f for f in findings if f.inspection_id == "GRD_OVER_001"]
        assert len(op_findings) == 1
        assert op_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_overprint_on_cmyk_ok() -> None:
        events = [
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                overprint_stroking=True,
            ),
            ColorChangedEvent(
                operator="K",
                page_num=1,
                operator_index=1,
                stroking=True,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        op_findings = [f for f in findings if f.inspection_id == "GRD_OVER_001"]
        assert len(op_findings) == 0

    @staticmethod
    def test_overprint_on_gray_ok() -> None:
        """DeviceGray with overprint is acceptable."""
        events = [
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                overprint_non_stroking=True,
            ),
            ColorChangedEvent(
                operator="g",
                page_num=1,
                operator_index=1,
                stroking=False,
                color_space="DeviceGray",
                color_values=(0.0,),
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        op_findings = [f for f in findings if f.inspection_id == "GRD_OVER_001"]
        assert len(op_findings) == 0

    @staticmethod
    def test_no_overprint_rgb_ok() -> None:
        """RGB without overprint does not trigger GRD_OVER_001."""
        events = [
            ColorChangedEvent(
                operator="RG",
                page_num=1,
                operator_index=0,
                stroking=True,
                color_space="DeviceRGB",
                color_values=(1.0, 0.0, 0.0),
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        op_findings = [f for f in findings if f.inspection_id == "GRD_OVER_001"]
        assert len(op_findings) == 0


class TestOPMZero:
    """Test GRD_OVER_002: OPM=0 with DeviceCMYK."""

    @staticmethod
    def test_opm0_cmyk_delay() -> None:
        events = [
            ColorChangedEvent(
                operator="k",
                page_num=1,
                operator_index=0,
                stroking=False,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
            ),
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=1,
                overprint_non_stroking=True,
                overprint_mode=0,
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        opm_findings = [f for f in findings if f.inspection_id == "GRD_OVER_002"]
        assert len(opm_findings) == 1
        assert opm_findings[0].severity == Severity.WARNING

    @staticmethod
    def test_opm1_cmyk_ok() -> None:
        events = [
            ColorChangedEvent(
                operator="k",
                page_num=1,
                operator_index=0,
                stroking=False,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
            ),
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=1,
                overprint_non_stroking=True,
                overprint_mode=1,
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        opm_findings = [f for f in findings if f.inspection_id == "GRD_OVER_002"]
        assert len(opm_findings) == 0


class TestOverprintWithTransparency:
    """Test GRD_OVER_003: overprint with transparency."""

    @staticmethod
    def test_overprint_transparency_conflict() -> None:
        events = [
            OpacityChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                non_stroking_alpha=0.5,
            ),
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=1,
                overprint_stroking=True,
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        conflict_findings = [f for f in findings if f.inspection_id == "GRD_OVER_003"]
        assert len(conflict_findings) == 1

    @staticmethod
    def test_overprint_no_transparency_ok() -> None:
        events = [
            OverprintChangedEvent(
                operator="gs",
                page_num=1,
                operator_index=0,
                overprint_stroking=True,
            ),
        ]
        analyzer = OverprintAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        conflict_findings = [f for f in findings if f.inspection_id == "GRD_OVER_003"]
        assert len(conflict_findings) == 0
