"""Tests for BarcodeAnalyzer — barcode pattern detection heuristics."""

from __future__ import annotations

from lintpdf.analyzers.barcode import BarcodeAnalyzer
from lintpdf.analyzers.finding import Severity
from lintpdf.semantic.events import PathPaintingEvent
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document() -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _narrow_stroke(page_num: int = 1, index: int = 0, width: float = 0.5) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="S",
        page_num=page_num,
        operator_index=index,
        stroke=True,
        fill=False,
        line_width=width,
        line_cap=0,
        line_join=0,
        stroke_color_space="DeviceGray",
        stroke_color_values=(0.0,),
    )


class TestBarcodePatternDetection:
    """Test LPDF_BARCODE_001: Potential barcode pattern on page."""

    @staticmethod
    def test_many_narrow_strokes_flags_barcode() -> None:
        events = [_narrow_stroke(index=i) for i in range(25)]
        analyzer = BarcodeAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 1
        assert barcode[0].severity == Severity.ADVISORY
        assert barcode[0].page_num == 1
        assert barcode[0].details["narrow_stroke_count"] == 25

    @staticmethod
    def test_below_threshold_no_flag() -> None:
        events = [_narrow_stroke(index=i) for i in range(15)]
        analyzer = BarcodeAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 0

    @staticmethod
    def test_exactly_at_threshold() -> None:
        events = [_narrow_stroke(index=i) for i in range(20)]
        analyzer = BarcodeAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 1

    @staticmethod
    def test_custom_threshold() -> None:
        events = [_narrow_stroke(index=i) for i in range(10)]
        analyzer = BarcodeAnalyzer(min_narrow_strokes=5)
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 1

    @staticmethod
    def test_wide_strokes_ignored() -> None:
        events = [_narrow_stroke(index=i, width=2.0) for i in range(30)]
        analyzer = BarcodeAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 0

    @staticmethod
    def test_custom_narrow_width() -> None:
        events = [_narrow_stroke(index=i, width=1.5) for i in range(25)]
        analyzer = BarcodeAnalyzer(narrow_stroke_width=2.0)
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 1

    @staticmethod
    def test_fill_only_paths_ignored() -> None:
        events = [
            PathPaintingEvent(
                operator="f",
                page_num=1,
                operator_index=i,
                stroke=False,
                fill=True,
                line_width=0.5,
                line_cap=0,
                line_join=0,
            )
            for i in range(30)
        ]
        analyzer = BarcodeAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 0

    @staticmethod
    def test_multiple_pages_flagged_independently() -> None:
        doc = SemanticDocument(
            version="2.0",
            page_count=2,
            is_encrypted=False,
            pages=[
                SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792)),
                SemanticPage(page_num=2, media_box=PdfBox(0, 0, 612, 792)),
            ],
        )
        events = [_narrow_stroke(page_num=1, index=i) for i in range(25)]
        events += [_narrow_stroke(page_num=2, index=i + 25) for i in range(25)]
        analyzer = BarcodeAnalyzer()
        findings = analyzer.analyze(doc, events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 2
        pages = {f.page_num for f in barcode}
        assert pages == {1, 2}

    @staticmethod
    def test_zero_width_strokes_excluded() -> None:
        """Zero-width strokes should not count (condition is 0 < width < threshold)."""
        events = [_narrow_stroke(index=i, width=0.0) for i in range(30)]
        analyzer = BarcodeAnalyzer()
        findings = analyzer.analyze(_make_document(), events)
        barcode = [f for f in findings if f.inspection_id == "LPDF_BARCODE_001"]
        assert len(barcode) == 0
