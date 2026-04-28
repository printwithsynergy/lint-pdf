"""Tests for HairlineAnalyzer Part 5 checks — LPDF_STROKE_004, LPDF_PATH_001."""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.hairline import HairlineAnalyzer
from lintpdf.semantic.events import PathPaintingEvent
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document() -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestMultiInkThinStroke:
    """Test LPDF_STROKE_004: Multi-ink thin stroke."""

    @staticmethod
    def test_multi_ink_thin_stroke_flags() -> None:
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=0.3,
                line_cap=1,
                line_join=0,
                stroke_color_space="DeviceCMYK",
                stroke_color_values=(0.5, 0.3, 0.0, 1.0),
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_STROKE_004"]
        assert len(f) == 1
        assert f[0].severity == Severity.WARNING

    @staticmethod
    def test_single_ink_thin_stroke_no_flag() -> None:
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=0.3,
                line_cap=1,
                line_join=0,
                stroke_color_space="DeviceCMYK",
                stroke_color_values=(0.0, 0.0, 0.0, 1.0),
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_STROKE_004"]
        assert len(f) == 0

    @staticmethod
    def test_multi_ink_thick_stroke_no_flag() -> None:
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=1,
                line_join=0,
                stroke_color_space="DeviceCMYK",
                stroke_color_values=(0.5, 0.3, 0.0, 1.0),
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_STROKE_004"]
        assert len(f) == 0

    @staticmethod
    def test_non_cmyk_thin_stroke_no_flag() -> None:
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=0.3,
                line_cap=1,
                line_join=0,
                stroke_color_space="DeviceRGB",
                stroke_color_values=(1.0, 0.0, 0.0),
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_STROKE_004"]
        assert len(f) == 0


class TestExcessivePathPoints:
    """Test LPDF_PATH_001: Excessive path points."""

    @staticmethod
    def test_many_points_flags() -> None:
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                point_count=15000,
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_PATH_001"]
        assert len(f) == 1
        assert f[0].severity == Severity.WARNING
        assert f[0].details["point_count"] == 15000

    @staticmethod
    def test_normal_points_no_flag() -> None:
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                point_count=500,
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_PATH_001"]
        assert len(f) == 0

    @staticmethod
    def test_exactly_10000_no_flag() -> None:
        events = [
            PathPaintingEvent(
                operator="S",
                page_num=1,
                operator_index=0,
                stroke=True,
                fill=False,
                line_width=1.0,
                line_cap=0,
                line_join=0,
                point_count=10000,
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_PATH_001"]
        assert len(f) == 0

    @staticmethod
    def test_10001_flags() -> None:
        events = [
            PathPaintingEvent(
                operator="f",
                page_num=1,
                operator_index=0,
                stroke=False,
                fill=True,
                line_width=0.0,
                line_cap=0,
                line_join=0,
                point_count=10001,
            )
        ]
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        f = [f for f in findings if f.inspection_id == "LPDF_PATH_001"]
        assert len(f) == 1
