"""Tests for HairlineAnalyzer — thin strokes and small text detection."""

from __future__ import annotations

from grounded.analyzers.finding import Severity
from grounded.analyzers.hairline import HairlineAnalyzer
from grounded.semantic.events import PathPaintingEvent, TextRenderedEvent
from grounded.semantic.graphics_state import TransformationMatrix
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document() -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _stroke_event(
    line_width: float,
    page_num: int = 1,
    line_cap: int = 0,
) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="S",
        page_num=page_num,
        operator_index=0,
        fill=False,
        stroke=True,
        stroke_color_space="DeviceCMYK",
        stroke_color_values=(0.0, 0.0, 0.0, 1.0),
        line_width=line_width,
        line_cap=line_cap,
    )


def _text_event(
    font_size: float,
    ctm_scale: float = 1.0,
    tm_scale: float = 1.0,
    page_num: int = 1,
) -> TextRenderedEvent:
    return TextRenderedEvent(
        operator="Tj",
        page_num=page_num,
        operator_index=0,
        font_name="F1",
        font_size=font_size,
        ctm=TransformationMatrix(a=ctm_scale, d=ctm_scale),
        text_matrix=TransformationMatrix(a=tm_scale, d=tm_scale),
    )


class TestZeroWidthStroke:
    @staticmethod
    def test_zero_width_aground() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_stroke_event(0.0)])
        assert len(findings) == 1
        assert findings[0].inspection_id == "GRD_STROKE_002"
        assert findings[0].severity == Severity.AGROUND

    @staticmethod
    def test_negative_width_aground() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_stroke_event(-0.1)])
        ids = [f.inspection_id for f in findings]
        assert "GRD_STROKE_002" in ids


class TestHairlineStroke:
    @staticmethod
    def test_hairline_delay() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_stroke_event(0.1)])
        ids = [f.inspection_id for f in findings]
        assert "GRD_STROKE_001" in ids

    @staticmethod
    def test_above_threshold_no_finding() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_stroke_event(0.5)])
        ids = [f.inspection_id for f in findings]
        assert "GRD_STROKE_001" not in ids

    @staticmethod
    def test_custom_threshold() -> None:
        analyzer = HairlineAnalyzer(hairline_threshold=0.5)
        findings = analyzer.analyze(_make_document(), [_stroke_event(0.3)])
        ids = [f.inspection_id for f in findings]
        assert "GRD_STROKE_001" in ids


class TestButtCapThinStroke:
    @staticmethod
    def test_butt_cap_advisory() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_stroke_event(0.3, line_cap=0)])
        ids = [f.inspection_id for f in findings]
        assert "GRD_STROKE_003" in ids

    @staticmethod
    def test_round_cap_no_finding() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_stroke_event(0.3, line_cap=1)])
        ids = [f.inspection_id for f in findings]
        assert "GRD_STROKE_003" not in ids

    @staticmethod
    def test_thick_stroke_no_finding() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_stroke_event(1.0, line_cap=0)])
        ids = [f.inspection_id for f in findings]
        assert "GRD_STROKE_003" not in ids


class TestSmallText:
    @staticmethod
    def test_small_text_advisory() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_text_event(5.0)])
        assert len(findings) == 1
        assert findings[0].inspection_id == "GRD_TEXT_001"
        assert findings[0].severity == Severity.ADVISORY

    @staticmethod
    def test_very_small_text_delay() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_text_event(3.0)])
        assert len(findings) == 1
        assert findings[0].inspection_id == "GRD_TEXT_002"
        assert findings[0].severity == Severity.SQUALL

    @staticmethod
    def test_normal_text_no_finding() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_text_event(12.0)])
        assert len(findings) == 0

    @staticmethod
    def test_scaled_text_effective_size() -> None:
        """12pt text at 0.25 CTM scale = 3pt effective → very small."""
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_text_event(12.0, ctm_scale=0.25)])
        assert len(findings) == 1
        assert findings[0].inspection_id == "GRD_TEXT_002"

    @staticmethod
    def test_object_type_set() -> None:
        analyzer = HairlineAnalyzer()
        findings = analyzer.analyze(_make_document(), [_text_event(3.0)])
        assert findings[0].object_type == "text"
