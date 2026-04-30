"""PR-M tests — LPDF_BOX_BG_NO_BLEED + LPDF_BOX_PRESS_MARKS_MISSING."""

from __future__ import annotations

from siftpdf.analyzers.page_geometry_audit import PageGeometryAuditAnalyzer
from siftpdf.semantic.events import PathPaintingEvent
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _path(idx: int, page_num: int, bbox: tuple[float, float, float, float]) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="f",
        page_num=page_num,
        operator_index=idx,
        stroke=False,
        fill=True,
        line_width=0.0,
        bbox=bbox,
    )


def _doc(page: SemanticPage) -> SemanticDocument:
    return SemanticDocument(version="2.0", page_count=1, is_encrypted=False, pages=[page])


# ── LPDF_BOX_BG_NO_BLEED ──────────────────────────────────────────


def test_zero_bleed_with_art_at_trim_edge_fires() -> None:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(50, 50, 562, 742),
        bleed_box=PdfBox(50, 50, 562, 742),  # == trim → zero bleed
    )
    # Background fills exactly to the trim box edges.
    events = [_path(0, 1, (50.0, 50.0, 562.0, 742.0))]
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    no_bleed = [x for x in findings if x.inspection_id == "LPDF_BOX_BG_NO_BLEED"]
    assert len(no_bleed) == 1
    edges = no_bleed[0].details["edges_touched"]
    assert set(edges) == {"left", "right", "top", "bottom"}


def test_art_extending_past_trim_suppresses_finding() -> None:
    """When 3+ paths extend meaningfully past the trim edge the press
    has bleed material to trim through; no white-sliver risk. Caught
    on Pink-Slush p2 where the background extended ~10pt past trim
    but the PDF's BleedBox wasn't updated.

    PR-GG: requires 3+ events past the edge to count as real bleed
    material — single stray glyph paths shouldn't suppress."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(50, 50, 562, 742),
        bleed_box=PdfBox(50, 50, 562, 742),
    )
    # 3 background paths extend 10pt past trim on all sides.
    events = [_path(i, 1, (40.0, 40.0, 572.0, 752.0)) for i in range(3)]
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_BG_NO_BLEED"]


def test_partial_overhang_only_clears_clean_edges() -> None:
    """Art extends past trim on left only — should still fire on
    other 3 edges where art stops at trim. PR-GG: 3+ events to
    qualify as overhang."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(50, 50, 562, 742),
        bleed_box=PdfBox(50, 50, 562, 742),
    )
    # 3 paths bleed past LEFT only, stop AT trim on right/top/bottom.
    events = [_path(i, 1, (40.0, 50.0, 562.0, 742.0)) for i in range(3)]
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    no_bleed = [x for x in findings if x.inspection_id == "LPDF_BOX_BG_NO_BLEED"]
    assert len(no_bleed) == 1
    edges = set(no_bleed[0].details["edges_touched"])
    assert "left" not in edges  # has overhang → clean
    assert {"right", "top", "bottom"} <= edges


def test_single_outlier_path_does_not_suppress() -> None:
    """PR-GG: ONE stray glyph extending past trim is anti-aliasing /
    bbox tolerance, not real bleed material — finding still fires.
    Closes Cherry-Twist / OrangeKiss / Pink-Slush misses where a few
    outlier outlined paths previously silenced the rule on outlined
    fixtures whose actual background fills stop at trim."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(50, 50, 562, 742),
        bleed_box=PdfBox(50, 50, 562, 742),
    )
    # Background fill at trim, plus ONE stray glyph path 5pt past right.
    events = [
        _path(0, 1, (50.0, 50.0, 562.0, 742.0)),  # at trim
        _path(1, 1, (557.0, 100.0, 567.0, 110.0)),  # 5pt past right
    ]
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    no_bleed = [x for x in findings if x.inspection_id == "LPDF_BOX_BG_NO_BLEED"]
    assert len(no_bleed) == 1


def test_zero_bleed_with_art_inside_safe_no_finding() -> None:
    """Art with margin from trim — no white-sliver risk."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(50, 50, 562, 742),
        bleed_box=PdfBox(50, 50, 562, 742),
    )
    events = [_path(0, 1, (100.0, 100.0, 500.0, 700.0))]  # 50pt margin
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_BG_NO_BLEED"]


def test_real_bleed_declared_no_finding() -> None:
    """When bleed_box extends past trim_box the existing
    LPDF_BOX_003 / LPDF_BOX_006 checks own this case."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(50, 50, 562, 742),
        bleed_box=PdfBox(40, 40, 572, 752),  # 10pt bleed
    )
    events = [_path(0, 1, (50.0, 50.0, 562.0, 742.0))]
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_BG_NO_BLEED"]


def test_no_painted_content_no_finding() -> None:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(50, 50, 562, 742),
        bleed_box=PdfBox(50, 50, 562, 742),
    )
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_BG_NO_BLEED"]


# ── LPDF_BOX_PRESS_MARKS_MISSING ──────────────────────────────────


def _page_with_bleed_strip() -> SemanticPage:
    """Media 1000x1000, trim 100..900 — 100pt bleed strip on all
    sides (room for marks)."""
    return SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 1000, 1000),
        trim_box=PdfBox(100, 100, 900, 900),
    )


def _busy_page_events(count: int = 30) -> list[PathPaintingEvent]:
    """Heap of painted events ALL inside the trim box (no marks)."""
    return [_path(i, 1, (200.0 + i, 200.0, 250.0 + i, 800.0)) for i in range(count)]


def test_busy_page_with_mark_outside_trim_no_finding() -> None:
    page = _page_with_bleed_strip()
    # 30 in-trim events + 1 trim-mark with centre at (50, 500)
    events = [*_busy_page_events(30), _path(99, 1, (45.0, 495.0, 55.0, 505.0))]
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_PRESS_MARKS_MISSING"]


def test_busy_page_without_marks_fires() -> None:
    page = _page_with_bleed_strip()
    events = _busy_page_events(30)
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    miss = [x for x in findings if x.inspection_id == "LPDF_BOX_PRESS_MARKS_MISSING"]
    assert len(miss) == 1


def test_blank_page_no_finding() -> None:
    """Reference pages with very few painted elements should not
    trigger the press-marks expectation."""
    page = _page_with_bleed_strip()
    events = _busy_page_events(5)  # below the 30-event threshold
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_PRESS_MARKS_MISSING"]


def test_no_room_for_marks_no_finding() -> None:
    """Page where media_box == trim_box — no place to put marks."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(100, 100, 900, 900),
        trim_box=PdfBox(100, 100, 900, 900),
    )
    findings = PageGeometryAuditAnalyzer().analyze(_doc(page), _busy_page_events(50))
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_PRESS_MARKS_MISSING"]
