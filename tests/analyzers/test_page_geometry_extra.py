"""PR-S tests — page geometry extra checks."""

from __future__ import annotations

from siftpdf.analyzers.page_geometry_extra import PageGeometryExtraAnalyzer
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


# ── LPDF_BOX_TRIMBOX_DEFAULTED ────────────────────────────────────


def test_trimbox_equals_mediabox_on_large_page_fires() -> None:
    """test-sample-style 8.5x11" page with no explicit TrimBox."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),  # 8.5x11"
        trim_box=PdfBox(0, 0, 612, 792),  # defaulted
    )
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), [])
    f = [x for x in findings if x.inspection_id == "LPDF_BOX_TRIMBOX_DEFAULTED"]
    assert len(f) == 1
    assert f[0].details["trim_equals_media"] is True


def test_trimbox_distinct_from_mediabox_no_finding() -> None:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(36, 36, 576, 756),  # margin between media and trim
    )
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_TRIMBOX_DEFAULTED"]


def test_small_label_page_with_default_no_finding() -> None:
    """A 3x4" stick-pack label legitimately has TrimBox==MediaBox."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 216, 288),  # 3x4"
        trim_box=PdfBox(0, 0, 216, 288),
    )
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_TRIMBOX_DEFAULTED"]


# ── LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT ────────────────────────────


def test_bleed_thin_with_content_past_fires() -> None:
    """Amalgam case: BleedBox 4.5pt past trim, content extends ~9pt
    past trim (i.e. past the bleed)."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 750, 320),
        trim_box=PdfBox(33, 33, 717, 285),
        bleed_box=PdfBox(28.5, 28.5, 721.5, 289.5),  # 4.5pt past trim
    )
    # Content extends to (24, 24, 726, 294) — 4.5pt past bleed
    events = [_path(0, 1, (24.0, 24.0, 726.0, 294.0))]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    f = [x for x in findings if x.inspection_id == "LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT"]
    assert len(f) == 1
    assert f[0].details["bleed_offsets_pt"] == [4.5, 4.5, 4.5, 4.5]


def test_bleed_adequate_no_finding() -> None:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 750, 320),
        trim_box=PdfBox(33, 33, 717, 285),
        bleed_box=PdfBox(20, 20, 730, 300),  # ~12pt past trim
    )
    events = [_path(0, 1, (20.0, 20.0, 730.0, 300.0))]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT"]


def test_bleed_zero_skipped_handled_by_other_check() -> None:
    """When bleed_box == trim_box, LPDF_BOX_BG_NO_BLEED owns this case."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 750, 320),
        trim_box=PdfBox(33, 33, 717, 285),
        bleed_box=PdfBox(33, 33, 717, 285),  # zero bleed
    )
    events = [_path(0, 1, (33.0, 33.0, 717.0, 285.0))]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT"]


def test_bleed_thin_but_content_inside_no_finding() -> None:
    """Standalone LPDF_BOX_003 owns the inadequate-bleed-with-no-spill
    case; this combined check stays silent."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 750, 320),
        trim_box=PdfBox(33, 33, 717, 285),
        bleed_box=PdfBox(28.5, 28.5, 721.5, 289.5),
    )
    events = [_path(0, 1, (33.0, 33.0, 717.0, 285.0))]  # all inside trim
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT"]


# ── LPDF_BOX_MULTI_LABEL_PAGE ─────────────────────────────────────


def test_two_clusters_separated_by_gap_fires() -> None:
    """Pavette case: two labels stacked with a clear empty band
    between them."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 600, 800),
    )
    # 30 events forming a top cluster (y 50..250) and bottom cluster
    # (y 500..700) with ~250pt empty band between them.
    events = []
    for i in range(15):
        events.append(_path(i, 1, (50.0 + i * 2, 50.0 + i * 5, 80.0 + i * 2, 250.0 - i * 5)))
    for i in range(15, 30):
        events.append(_path(i, 1, (50.0 + (i - 15) * 2, 500.0, 80.0 + (i - 15) * 2, 700.0)))
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    multi = [x for x in findings if x.inspection_id == "LPDF_BOX_MULTI_LABEL_PAGE"]
    assert len(multi) == 1
    assert multi[0].details["empty_band_pt"] >= 30


def test_single_dense_cluster_no_finding() -> None:
    """Single label artwork with no internal gaps."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 600, 800),
    )
    events = [
        _path(
            i,
            1,
            (
                50.0 + (i % 10) * 30,
                100.0 + (i // 10) * 30,
                80.0 + (i % 10) * 30,
                130.0 + (i // 10) * 30,
            ),
        )
        for i in range(40)
    ]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_MULTI_LABEL_PAGE"]


def test_few_events_no_finding() -> None:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 600, 800),
    )
    events = [_path(0, 1, (50.0, 100.0, 80.0, 130.0))]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_MULTI_LABEL_PAGE"]


# ── LPDF_BOX_TRIMBOX_UNDERSIZED (PR-BB) ────────────────────────────


def test_artwork_extends_far_past_trimbox_fires() -> None:
    """Pink-Slush p2 case: TrimBox covers left panel only, artwork
    extends ~30 pt past the right edge — well beyond a normal 3 mm
    bleed allowance. Fires LPDF_BOX_TRIMBOX_UNDERSIZED."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 400, 200),
        trim_box=PdfBox(50, 50, 200, 150),  # left panel only
    )
    events = [
        _path(0, 1, (50.0, 50.0, 350.0, 150.0)),  # extends 150 pt past right
    ]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    f = [x for x in findings if x.inspection_id == "LPDF_BOX_TRIMBOX_UNDERSIZED"]
    assert len(f) == 1
    assert f[0].details["worst_side"] == "right"


def test_artwork_just_past_trim_within_bleed_no_finding() -> None:
    """Artwork extends only 5 pt past TrimBox — within normal bleed
    allowance. Should NOT fire (LPDF_BOX_006 covers the bleed case)."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 400, 200),
        trim_box=PdfBox(50, 50, 350, 150),
    )
    events = [
        _path(0, 1, (50.0, 50.0, 355.0, 150.0)),  # 5 pt past right
    ]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_TRIMBOX_UNDERSIZED"]


def test_trim_equals_media_no_undersized_finding() -> None:
    """When TrimBox==MediaBox the LPDF_BOX_TRIMBOX_DEFAULTED rule owns
    the case — undersized check should suppress to avoid duplicate
    coverage."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 400, 200),
        trim_box=PdfBox(0, 0, 400, 200),
    )
    events = [_path(0, 1, (10.0, 10.0, 390.0, 190.0))]
    findings = PageGeometryExtraAnalyzer().analyze(_doc(page), events)
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_TRIMBOX_UNDERSIZED"]
