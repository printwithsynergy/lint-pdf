"""PR-L tests — LPDF_BARCODE_NOMINAL_SIZE_LOW and
LPDF_BARCODE_QUIET_ZONE_INK from the post-merge audit closure."""

from __future__ import annotations

from siftpdf.analyzers.barcode import BarcodeAnalyzer
from siftpdf.semantic.events import PathPaintingEvent
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc() -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _bar(idx: int, x: float, y0: float, y1: float, width: float = 0.5) -> PathPaintingEvent:
    """A vertical narrow-bar stroke for a picket-fence barcode."""
    return PathPaintingEvent(
        operator="S",
        page_num=1,
        operator_index=idx,
        stroke=True,
        fill=False,
        line_width=width,
        stroke_color_space="DeviceGray",
        stroke_color_values=(0.0,),
        bbox=(x, y0, x + width, y1),
    )


def _make_picket_barcode(
    x_start: float = 100.0,
    y_low: float = 100.0,
    y_high: float = 130.0,
    span_pt: float = 100.0,
    bar_count: int = 30,
) -> list[PathPaintingEvent]:
    """Build a horizontal-arranged set of vertical bars covering
    [x_start, x_start + span_pt]."""
    bars: list[PathPaintingEvent] = []
    if bar_count <= 0:
        return bars
    spacing = span_pt / max(bar_count - 1, 1)
    for i in range(bar_count):
        bars.append(_bar(i, x_start + i * spacing, y_low, y_high))
    return bars


# ── LPDF_BARCODE_NOMINAL_SIZE_LOW ─────────────────────────────────


def test_full_size_barcode_no_finding() -> None:
    """Barcode 38mm wide (~107.7pt) — at full nominal — passes."""
    events = _make_picket_barcode(span_pt=108.0, bar_count=30)
    findings = BarcodeAnalyzer().analyze(_doc(), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BARCODE_NOMINAL_SIZE_LOW"]


def test_undersized_barcode_fires() -> None:
    """Barcode 18mm wide — below GS1 80% magnification floor."""
    events = _make_picket_barcode(span_pt=51.0, bar_count=30)
    findings = BarcodeAnalyzer().analyze(_doc(), events)
    sized = [x for x in findings if x.inspection_id == "LPDF_BARCODE_NOMINAL_SIZE_LOW"]
    assert len(sized) == 1
    assert sized[0].details["long_axis_mm"] < 29.83


# ── LPDF_BARCODE_QUIET_ZONE_INK ───────────────────────────────────


def test_clear_quiet_zone_no_finding() -> None:
    """Quiet zone is empty around the barcode — clean pass."""
    events = _make_picket_barcode()
    findings = BarcodeAnalyzer().analyze(_doc(), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BARCODE_QUIET_ZONE_INK"]


def test_painted_block_in_quiet_zone_fires() -> None:
    """A wide filled rectangle abutting the barcode's left edge
    encroaches the 10x narrow-bar quiet zone."""
    events = _make_picket_barcode(x_start=100.0, span_pt=100.0, bar_count=30)
    # Painted obstruction immediately to the left of the barcode bbox
    # at x in [97, 100], i.e. inside the 10*0.5 = 5pt quiet zone.
    obstruction = PathPaintingEvent(
        operator="f",
        page_num=1,
        operator_index=999,
        stroke=False,
        fill=True,
        line_width=0.0,
        fill_color_space="DeviceCMYK",
        fill_color_values=(0.5, 0.0, 0.5, 0.0),
        bbox=(97.0, 95.0, 100.0, 135.0),
    )
    findings = BarcodeAnalyzer().analyze(_doc(), [*events, obstruction])
    qz = [x for x in findings if x.inspection_id == "LPDF_BARCODE_QUIET_ZONE_INK"]
    assert len(qz) == 1
    assert qz[0].details["obstruction_count"] >= 1


def test_painted_block_outside_quiet_zone_no_finding() -> None:
    """An obstruction 50pt away from the barcode doesn't intersect
    the 5pt quiet zone."""
    events = _make_picket_barcode(x_start=100.0, span_pt=100.0, bar_count=30)
    far_obstruction = PathPaintingEvent(
        operator="f",
        page_num=1,
        operator_index=999,
        stroke=False,
        fill=True,
        line_width=0.0,
        fill_color_space="DeviceCMYK",
        fill_color_values=(0.5, 0.0, 0.5, 0.0),
        bbox=(40.0, 95.0, 90.0, 135.0),  # ends 10pt to left of barcode
    )
    findings = BarcodeAnalyzer().analyze(_doc(), [*events, far_obstruction])
    assert not [x for x in findings if x.inspection_id == "LPDF_BARCODE_QUIET_ZONE_INK"]


def test_obstruction_inside_barcode_bbox_does_not_count() -> None:
    """A path event inside the barcode's bbox is part of the symbol
    itself; should not be flagged as a quiet-zone obstruction."""
    events = _make_picket_barcode(x_start=100.0, span_pt=100.0, bar_count=30)
    # Filled rect entirely inside the barcode bbox.
    inside = PathPaintingEvent(
        operator="f",
        page_num=1,
        operator_index=999,
        stroke=False,
        fill=True,
        line_width=0.0,
        bbox=(120.0, 105.0, 180.0, 125.0),
    )
    findings = BarcodeAnalyzer().analyze(_doc(), [*events, inside])
    assert not [x for x in findings if x.inspection_id == "LPDF_BARCODE_QUIET_ZONE_INK"]
