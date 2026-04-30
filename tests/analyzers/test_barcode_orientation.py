"""Tests for the barcode orientation / quiet-zone / bar-height suite
added in PR D Slot 4.

These rules consume an existing ``_BarcodeCandidate`` produced by
``BarcodeAnalyzer`` and emit findings derived purely from bbox + stroke
geometry — no rendering, no decoding. Tests construct candidates and
synthetic SemanticDocuments directly.
"""

from __future__ import annotations

from siftpdf.analyzers.barcode import BarcodeAnalyzer, _BarcodeCandidate
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc_with_page(width: float, height: float) -> SemanticDocument:
    page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, width, height))
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def _candidate(
    bbox: tuple[float, float, float, float],
    stroke_widths: list[float] | None = None,
) -> _BarcodeCandidate:
    c = _BarcodeCandidate(page_num=1)
    x0, y0, x1, y1 = bbox
    c.add_stroke(width=0.5, bbox=(x0, y0, x0 + 0.5, y1))
    c.add_stroke(width=0.5, bbox=(x1 - 0.5, y0, x1, y1))
    c.stroke_widths = list(stroke_widths or [0.5, 0.5])
    return c


# ── Orientation ─────────────────────────────────────────────────────────


class TestOrientation:
    @staticmethod
    def test_ladder_on_landscape_page_fires() -> None:
        # Landscape page: 800x500. Ladder barcode: 50 wide x 200 tall.
        doc = _doc_with_page(800, 500)
        c = _candidate((10, 10, 60, 210), stroke_widths=[0.4] * 30)
        analyzer = BarcodeAnalyzer()
        findings = analyzer._check_orientation_suite([c], doc)
        ids = [f.inspection_id for f in findings]
        assert "LPDF_BARCODE_ORIENTATION" in ids
        f = next(f for f in findings if f.inspection_id == "LPDF_BARCODE_ORIENTATION")
        assert f.severity.value == "warning"
        assert f.details["page_orientation"] == "landscape"
        assert f.details["barcode_aspect"] == "ladder"

    @staticmethod
    def test_picket_on_landscape_no_orientation_finding() -> None:
        doc = _doc_with_page(800, 500)
        # Picket: 200 wide x 50 tall — natural for a landscape page.
        c = _candidate((10, 10, 210, 60))
        analyzer = BarcodeAnalyzer()
        findings = analyzer._check_orientation_suite([c], doc)
        assert "LPDF_BARCODE_ORIENTATION" not in {f.inspection_id for f in findings}

    @staticmethod
    def test_no_bounds_silent() -> None:
        doc = _doc_with_page(612, 792)
        c = _BarcodeCandidate(page_num=1)
        # No strokes added → has_bounds is False.
        analyzer = BarcodeAnalyzer()
        findings = analyzer._check_orientation_suite([c], doc)
        assert findings == []


# ── Quiet zone ──────────────────────────────────────────────────────────


class TestQuietZone:
    @staticmethod
    def test_barcode_against_left_edge_fires() -> None:
        doc = _doc_with_page(612, 792)
        # 0..100 horizontally is well within the 5.2 mm = 14.74 pt
        # quiet zone of the left edge — actually starting at x=2 puts
        # the bbox's left margin at 2 pt, well below threshold.
        c = _candidate((2, 100, 102, 130))
        analyzer = BarcodeAnalyzer()
        findings = analyzer._check_orientation_suite([c], doc)
        qz = next((f for f in findings if f.inspection_id == "LPDF_BARCODE_QUIET_ZONE_EDGE"), None)
        assert qz is not None
        assert "left" in qz.details["edges_violated"]

    @staticmethod
    def test_barcode_well_inside_no_quiet_zone_finding() -> None:
        doc = _doc_with_page(612, 792)
        # Bbox in middle of page with > 100 pt margins on all sides.
        c = _candidate((200, 300, 400, 400))
        analyzer = BarcodeAnalyzer()
        findings = analyzer._check_orientation_suite([c], doc)
        assert "LPDF_BARCODE_QUIET_ZONE_EDGE" not in {f.inspection_id for f in findings}


# ── Bar height ──────────────────────────────────────────────────────────


class TestHeightMin:
    @staticmethod
    def test_bars_too_short_for_narrow_width_fires() -> None:
        doc = _doc_with_page(612, 792)
        # Bbox 200 wide x 8 tall. Narrow bar = 0.5 pt. Min height =
        # 0.5 * 10 = 5 pt. bar_height = min(200, 8) = 8 pt — fine,
        # so use a thinner bbox.
        c = _candidate((200, 100, 400, 105))  # 200 wide x 5 tall
        # narrow bar = 0.4 pt. Min height = 4 pt. bar_height = 5. OK.
        # Force narrow bar 0.6 to make min_height = 6 > bar_height 5.
        c.stroke_widths = [0.6, 0.6]
        analyzer = BarcodeAnalyzer()
        findings = analyzer._check_orientation_suite([c], doc)
        ids = {f.inspection_id for f in findings}
        assert "LPDF_BARCODE_HEIGHT_MIN" in ids
        f = next(f for f in findings if f.inspection_id == "LPDF_BARCODE_HEIGHT_MIN")
        assert f.severity.value == "warning"
        assert f.details["bar_height_pts"] == 5.0
        assert f.details["narrow_bar_pts"] == 0.6
        assert f.details["gs1_min_pts"] == 6.0

    @staticmethod
    def test_bars_at_or_above_minimum_no_finding() -> None:
        doc = _doc_with_page(612, 792)
        # Bbox 200 wide x 100 tall. Narrow bar = 1 pt. Min height = 10.
        # bar_height = min(200, 100) = 100 — well above.
        c = _candidate((200, 100, 400, 200))
        c.stroke_widths = [1.0, 1.0]
        analyzer = BarcodeAnalyzer()
        findings = analyzer._check_orientation_suite([c], doc)
        assert "LPDF_BARCODE_HEIGHT_MIN" not in {f.inspection_id for f in findings}
