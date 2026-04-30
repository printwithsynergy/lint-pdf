"""Unit tests for WS-7 per-page aggregation.

The 2026-04-23 Opus audit flagged 3,159 findings on a single-page
Pink-Slush label. LPDF_ADV_005 produced 1,256 of those; LPDF_COLOR_010
produced 1,246; LPDF_COLOR_009 produced 552. Those three rules
emit one finding per matching PathPaintingEvent; on vector-dense
artwork the volume is unusable.

This test proves the aggregation collapses many matching events
into one finding per page per rule, with object_count and
representative_bboxes preserved on `details` so the viewer can
still drill in.
"""

from __future__ import annotations

from siftpdf.analyzers.advanced_color_analyzer import AdvancedColorAnalyzer
from siftpdf.analyzers.color import ColorAnalyzer
from siftpdf.semantic.events import PathPaintingEvent
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _path_event(
    *,
    page_num: int,
    cmyk: tuple[float, float, float, float],
    op_index: int,
) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="f",
        page_num=page_num,
        operator_index=op_index,
        fill=True,
        stroke=False,
        fill_color_space="DeviceCMYK",
        fill_color_values=cmyk,
        bbox=(float(op_index), 0.0, float(op_index) + 10.0, 10.0),
    )


def _doc(page_count: int = 1) -> SemanticDocument:
    pages = [
        SemanticPage(page_num=i, media_box=PdfBox(0, 0, 612, 792)) for i in range(1, page_count + 1)
    ]
    return SemanticDocument(
        version="1.7",
        page_count=page_count,
        is_encrypted=False,
        pages=pages,
    )


# -- LPDF_COLOR_010 (pure K-only fill) ---------------------------------------


def test_lpdf_color_010_aggregates_to_one_per_page() -> None:
    """1,000 matching K-only fills on page 1 should produce exactly
    one LPDF_COLOR_010 finding, not 1,000."""
    events = [_path_event(page_num=1, cmyk=(0.0, 0.0, 0.0, 0.9), op_index=i) for i in range(1000)]
    findings = ColorAnalyzer(brand_palette_present=True).analyze(_doc(), events)
    color_010 = [f for f in findings if f.inspection_id == "LPDF_COLOR_010"]
    assert len(color_010) == 1
    assert color_010[0].page_num == 1
    details = color_010[0].details or {}
    assert details.get("object_count") == 1000
    # Representative bboxes are capped at 5 so the finding payload
    # stays small.
    assert len(details.get("representative_bboxes", [])) == 5


def test_lpdf_color_010_one_finding_per_page_in_multi_page() -> None:
    """Matching fills on two pages => exactly two findings."""
    events = [
        _path_event(page_num=1, cmyk=(0.0, 0.0, 0.0, 0.9), op_index=0),
        _path_event(page_num=1, cmyk=(0.0, 0.0, 0.0, 0.9), op_index=1),
        _path_event(page_num=2, cmyk=(0.0, 0.0, 0.0, 0.9), op_index=2),
    ]
    findings = ColorAnalyzer(brand_palette_present=True).analyze(_doc(page_count=2), events)
    color_010 = [f for f in findings if f.inspection_id == "LPDF_COLOR_010"]
    assert {f.page_num for f in color_010} == {1, 2}
    assert len(color_010) == 2


def test_lpdf_color_010_silent_when_no_matches() -> None:
    """A PDF with no pure K-only fills emits no aggregate finding
    (no empty shell with object_count=0)."""
    events = [
        _path_event(page_num=1, cmyk=(0.5, 0.3, 0.2, 0.1), op_index=0),
    ]
    findings = ColorAnalyzer(brand_palette_present=True).analyze(_doc(), events)
    color_010 = [f for f in findings if f.inspection_id == "LPDF_COLOR_010"]
    assert color_010 == []


# -- LPDF_COLOR_009 (knockout black, no overprint) ---------------------------


def test_lpdf_color_009_aggregates_to_one_per_page() -> None:
    events = [_path_event(page_num=1, cmyk=(0.0, 0.0, 0.0, 1.0), op_index=i) for i in range(500)]
    findings = ColorAnalyzer(brand_palette_present=True).analyze(_doc(), events)
    color_009 = [f for f in findings if f.inspection_id == "LPDF_COLOR_009"]
    assert len(color_009) == 1
    assert (color_009[0].details or {}).get("object_count") == 500


# -- LPDF_ADV_005 (large pure K advisory) ------------------------------------


def test_no_brand_palette_suppresses_ambiguous_advisories() -> None:
    """Without a tenant brand palette, the engine can't tell whether
    pure-K fills were intentional. LPDF_COLOR_009/010 and
    LPDF_ADV_005 (pure_k path variant) must stay silent rather
    than spam ``needs_context`` advisories. Universal rules for
    small-text / thin-stroke multi-ink (LPDF_COLOR_008,
    LPDF_STROKE_004, LPDF_TEXT_006) still run regardless -- they
    enforce print-production invariants that aren't brand-specific."""
    events = [_path_event(page_num=1, cmyk=(0.0, 0.0, 0.0, 0.99), op_index=i) for i in range(50)]
    # Default: brand_palette_present=False -> silent.
    color_findings = ColorAnalyzer().analyze(_doc(), events)
    assert [
        f for f in color_findings if f.inspection_id in {"LPDF_COLOR_009", "LPDF_COLOR_010"}
    ] == []

    adv_findings = AdvancedColorAnalyzer().analyze(_doc(), events)
    pure_k_adv = [
        f
        for f in adv_findings
        if f.inspection_id == "LPDF_ADV_005" and (f.details or {}).get("classification") == "pure_k"
    ]
    assert pure_k_adv == []


def test_lpdf_adv_005_large_k_aggregates_to_one_per_page() -> None:
    """The advanced-color advisory about large pure K fills also
    aggregates per page."""
    # Classifier needs K > 95% for pure_k; 99% matches.
    events = [_path_event(page_num=1, cmyk=(0.0, 0.0, 0.0, 0.99), op_index=i) for i in range(200)]
    findings = AdvancedColorAnalyzer(brand_palette_present=True).analyze(_doc(), events)
    large_k = [
        f
        for f in findings
        if f.inspection_id == "LPDF_ADV_005" and (f.details or {}).get("classification") == "pure_k"
    ]
    assert len(large_k) == 1
    assert (large_k[0].details or {}).get("object_count") == 200
