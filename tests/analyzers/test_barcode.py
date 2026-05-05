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


# ---------------------------------------------------------------------------
# LPDF_BARCODE_031 — quiet zone close to trim edge (added 2026-04-28
# after audit run 4 — Pavette, OrangeKiss, AN-Energy, Pink-Slush)
# ---------------------------------------------------------------------------


def _stroke_at(
    x0: float, y0: float, x1: float, y1: float, page_num: int = 1, index: int = 0
) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="S",
        page_num=page_num,
        operator_index=index,
        stroke=True,
        fill=False,
        line_width=0.5,
        line_cap=0,
        line_join=0,
        stroke_color_space="DeviceGray",
        stroke_color_values=(0.0,),
        bbox=(x0, y0, x1, y1),
    )


def _doc_with_trim(trim: PdfBox) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                trim_box=trim,
            )
        ],
    )


def _barcode_strokes_at(
    cx: float, cy: float, width_pts: float = 80.0, height_pts: float = 30.0, count: int = 25
) -> list:
    """Generate ``count`` narrow strokes covering a barcode-shaped
    region centred at ``(cx, cy)`` with the given dimensions. Each
    stroke has a tight bbox so the candidate's overall bbox lands
    on the centred region."""
    out = []
    x0 = cx - width_pts / 2
    x1 = cx + width_pts / 2
    y0 = cy - height_pts / 2
    y1 = cy + height_pts / 2
    for i in range(count):
        # Spread strokes uniformly inside the region.
        sx = x0 + (i / max(1, count - 1)) * (x1 - x0)
        out.append(_stroke_at(sx, y0, sx + 0.5, y1, index=i))
    return out


def test_barcode_031_fires_when_close_to_left_trim() -> None:
    # Trim 0..612 x 0..792. Barcode centred at x=20, well inside trim.
    # Left edge of barcode bbox is at x=20-40 = -20. That's BEYOND
    # trim_box.x0 = 0, so it triggers 028 not 031. Move barcode
    # slightly right so left edge is inside trim but within 5mm.
    trim = PdfBox(0, 0, 612, 792)
    # 5mm = 14.17pt. Place barcode so its bbox left is at x=10pt
    # (inside trim, but only ~3.5mm clearance).
    events = _barcode_strokes_at(cx=50, cy=400, width_pts=80, height_pts=30)
    findings = BarcodeAnalyzer().analyze(_doc_with_trim(trim), events)
    qz = [f for f in findings if f.inspection_id == "LPDF_BARCODE_031"]
    assert len(qz) == 1
    assert "left" in qz[0].message
    # Must NOT fire 028 (extends beyond trim) — barcode is fully inside.
    extends = [f for f in findings if f.inspection_id == "LPDF_BARCODE_028"]
    assert extends == []


def test_barcode_031_does_not_fire_when_well_inside() -> None:
    """Barcode comfortably away from all trim edges (>5mm) should
    not trigger 031."""
    trim = PdfBox(0, 0, 612, 792)
    # Centre at (300, 400) with 80x30 bbox → all sides > 5mm clearance.
    events = _barcode_strokes_at(cx=300, cy=400, width_pts=80, height_pts=30)
    findings = BarcodeAnalyzer().analyze(_doc_with_trim(trim), events)
    qz = [f for f in findings if f.inspection_id == "LPDF_BARCODE_031"]
    assert qz == []


def test_barcode_031_does_not_double_fire_with_028() -> None:
    """When the barcode actually extends past trim (LPDF_BARCODE_028
    fires), LPDF_BARCODE_031 must NOT also fire — they're mutually
    exclusive in the if/else block."""
    trim = PdfBox(50, 50, 562, 742)  # smaller trim
    # Barcode centred near origin, extending into bleed.
    events = _barcode_strokes_at(cx=20, cy=400, width_pts=80, height_pts=30)
    findings = BarcodeAnalyzer().analyze(_doc_with_trim(trim), events)
    qz = [f for f in findings if f.inspection_id == "LPDF_BARCODE_031"]
    extends = [f for f in findings if f.inspection_id == "LPDF_BARCODE_028"]
    assert len(extends) == 1
    assert qz == []


def test_barcode_031_lists_all_close_sides() -> None:
    """Barcode tucked into a corner triggers two side breaches in the
    message."""
    trim = PdfBox(0, 0, 612, 792)
    # Centre at (600, 780) with 20x20 bbox → bbox right edge at 610
    # (2pt = 0.7mm clearance), top edge at 790 (2pt = 0.7mm). Both
    # sides < 5mm, both inside trim so 028 doesn't pre-empt.
    events = _barcode_strokes_at(cx=600, cy=780, width_pts=20, height_pts=20)
    findings = BarcodeAnalyzer().analyze(_doc_with_trim(trim), events)
    qz = [f for f in findings if f.inspection_id == "LPDF_BARCODE_031"]
    assert len(qz) == 1
    msg = qz[0].message
    assert "right" in msg
    assert "top" in msg


def test_barcode_031_skipped_when_no_trim_box() -> None:
    """No trim box → 031 has nothing to compare against."""
    doc = SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )
    events = _barcode_strokes_at(cx=20, cy=20, width_pts=80, height_pts=30)
    findings = BarcodeAnalyzer().analyze(doc, events)
    qz = [f for f in findings if f.inspection_id == "LPDF_BARCODE_031"]
    assert qz == []


def _fill_grid_events(
    *,
    rows: int,
    cols: int,
    module: float,
    step_x: float,
    step_y: float,
    page_num: int = 1,
) -> list[PathPaintingEvent]:
    """Dense small rectangular fills (2D-heuristic bait)."""
    events: list[PathPaintingEvent] = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            x0 = c * step_x
            y0 = r * step_y
            events.append(
                PathPaintingEvent(
                    operator="f",
                    page_num=page_num,
                    operator_index=idx,
                    fill=True,
                    stroke=False,
                    bbox=(x0, y0, x0 + module, y0 + module),
                )
            )
            idx += 1
    return events


def test_2d_barcode_suppressed_when_region_covers_trim_excessively() -> None:
    """WS-10 can admit a sub-200pt symbol that still covers most of a small trim box."""
    trim = PdfBox(0, 0, 200, 140)
    doc = _doc_with_trim(trim)
    doc._pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj trailer<<>>\n%%EOF\n"  # type: ignore[attr-defined]
    events = _fill_grid_events(rows=20, cols=30, module=4.0, step_x=5.0, step_y=6.0)
    findings = BarcodeAnalyzer().analyze(doc, events)
    two_d = [
        f
        for f in findings
        if f.inspection_id
        in ("LPDF_BARCODE_014", "LPDF_BARCODE_015", "LPDF_BARCODE_016", "LPDF_BARCODE_017", "LPDF_BARCODE_018")
    ]
    assert two_d == []
