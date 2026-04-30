"""PR-FF tests — audit-advisory analyzers."""

from __future__ import annotations

from types import SimpleNamespace

from lintpdf.analyzers.audit_advisories import AuditAdvisoryAnalyzer
from lintpdf.semantic.model import (
    DetectedTextRegion,
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _doc(
    *,
    info: dict | None = None,
    content_stream: bytes = b"",
    detected_regions: list[DetectedTextRegion] | None = None,
    dieline_regions: list[dict] | None = None,
) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=content_stream,
        detected_text_regions=tuple(detected_regions or ()),
    )
    doc = SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
        info_dict=info or {"/Title": "x", "/Author": "y", "/Producer": "z", "/Creator": "w"},
    )
    if dieline_regions is not None:
        # The analyzer reads `getattr(document, "dieline_result", None)`.
        # Use SimpleNamespace so we don't need the actual DielineResult class.
        object.__setattr__(doc, "dieline_result", SimpleNamespace(regions=dieline_regions))
    return doc


# ── LPDF_BOX_STEP_AND_REPEAT ─────────────────────────────────────────


def test_step_and_repeat_with_3_similar_regions_fires() -> None:
    """3 regions of similar size in a row → multi-up advisory."""
    regions = [
        {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
        {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
        {"x0": 220, "y0": 0, "x1": 320, "y1": 200},
    ]
    findings = AuditAdvisoryAnalyzer().analyze(_doc(dieline_regions=regions), [])
    f = [x for x in findings if x.inspection_id == "LPDF_BOX_STEP_AND_REPEAT"]
    assert len(f) == 1
    assert f[0].details["region_count"] == 3
    assert f[0].details["similar_size_count"] == 3


def test_two_regions_no_finding() -> None:
    regions = [
        {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
        {"x0": 110, "y0": 0, "x1": 210, "y1": 200},
    ]
    findings = AuditAdvisoryAnalyzer().analyze(_doc(dieline_regions=regions), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_STEP_AND_REPEAT"]


def test_dissimilar_regions_no_finding() -> None:
    """3 regions with very different sizes (front + back + tear-strip
    artwork) shouldn't fire."""
    regions = [
        {"x0": 0, "y0": 0, "x1": 100, "y1": 200},
        {"x0": 110, "y0": 0, "x1": 500, "y1": 200},  # 4x wider
        {"x0": 0, "y0": 250, "x1": 50, "y1": 280},  # tiny
    ]
    findings = AuditAdvisoryAnalyzer().analyze(_doc(dieline_regions=regions), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_STEP_AND_REPEAT"]


def test_no_dieline_no_finding() -> None:
    findings = AuditAdvisoryAnalyzer().analyze(_doc(), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_BOX_STEP_AND_REPEAT"]


# ── LPDF_DOC_METADATA_INCOMPLETE ─────────────────────────────────────


def test_metadata_two_keys_missing_fires() -> None:
    findings = AuditAdvisoryAnalyzer().analyze(
        _doc(info={"/Title": "Foo", "/Producer": "Adobe"}), []
    )
    f = [x for x in findings if x.inspection_id == "LPDF_DOC_METADATA_INCOMPLETE"]
    assert len(f) == 1
    assert "Author" in f[0].details["missing_keys"]
    assert "Creator" in f[0].details["missing_keys"]


def test_metadata_one_key_missing_no_finding() -> None:
    findings = AuditAdvisoryAnalyzer().analyze(
        _doc(info={"/Title": "Foo", "/Producer": "Adobe", "/Creator": "AI"}), []
    )
    assert not [x for x in findings if x.inspection_id == "LPDF_DOC_METADATA_INCOMPLETE"]


def test_metadata_all_present_no_finding() -> None:
    findings = AuditAdvisoryAnalyzer().analyze(_doc(), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_DOC_METADATA_INCOMPLETE"]


# ── LPDF_DIE_DIMENSION_CALLOUT ───────────────────────────────────────


def test_inch_dimension_callout_fires() -> None:
    cs = b'BT /F1 8 Tf (2.4409" ) Tj ET'
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    f = [x for x in findings if x.inspection_id == "LPDF_DIE_DIMENSION_CALLOUT"]
    assert len(f) == 1
    assert any("2.4409" in m for m in f[0].details["matched_callouts"])


def test_mm_dimension_callout_fires() -> None:
    cs = b"BT /F1 8 Tf (10 mm) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert any(f.inspection_id == "LPDF_DIE_DIMENSION_CALLOUT" for f in findings)


def test_gusset_callout_fires() -> None:
    cs = b"BT /F1 8 Tf (GUSSET 21x6.5x2) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert any(f.inspection_id == "LPDF_DIE_DIMENSION_CALLOUT" for f in findings)


def test_ingredient_quantity_no_finding() -> None:
    """``5 mg`` is a regulatory quantity, not a dimension callout —
    the pattern requires explicit dimension units (mm, inch double-quote,
    or gusset spec)."""
    cs = b"BT /F1 8 Tf (5 mg sodium per serving) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert not [f for f in findings if f.inspection_id == "LPDF_DIE_DIMENSION_CALLOUT"]


def test_ocr_dimension_callout_fires() -> None:
    """OCR-detected dimension text on outlined fixtures fires."""
    region = DetectedTextRegion(
        bbox=PdfBox(100, 100, 200, 110),
        text='5.7500" trim',
    )
    findings = AuditAdvisoryAnalyzer().analyze(_doc(detected_regions=[region]), [])
    assert any(f.inspection_id == "LPDF_DIE_DIMENSION_CALLOUT" for f in findings)


# ── LPDF_NET_WEIGHT_VERIFY ───────────────────────────────────────────


def test_net_weight_metric_only_fires() -> None:
    cs = b"BT /F1 8 Tf (NET WT 6.0 g) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    f = [x for x in findings if x.inspection_id == "LPDF_NET_WEIGHT_VERIFY"]
    assert len(f) == 1
    assert f[0].details["metric_present"] is True
    assert f[0].details["imperial_present"] is False


def test_net_weight_imperial_only_fires() -> None:
    cs = b"BT /F1 8 Tf (NET WT 8 oz) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert any(f.inspection_id == "LPDF_NET_WEIGHT_VERIFY" for f in findings)


def test_net_weight_dual_unit_no_finding() -> None:
    """Dual unit declaration `200 g (8 oz)` should NOT fire."""
    cs = b"BT /F1 8 Tf (NET WT 200 g (8 oz)) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert not [f for f in findings if f.inspection_id == "LPDF_NET_WEIGHT_VERIFY"]


def test_net_weight_french_metric_fires() -> None:
    cs = b"BT /F1 8 Tf (POIDS NET 250 g) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert any(f.inspection_id == "LPDF_NET_WEIGHT_VERIFY" for f in findings)


def test_nutrient_quantity_no_finding() -> None:
    """`5 g sodium per serving` is a regulatory quantity, NOT a net
    weight — must not fire."""
    cs = b"BT /F1 8 Tf (5 g sodium per serving) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert not [f for f in findings if f.inspection_id == "LPDF_NET_WEIGHT_VERIFY"]


def test_net_carbs_no_finding() -> None:
    """`Net Carbs 6 g` is a nutrition label fact, NOT a net weight
    declaration. Must not fire."""
    cs = b"BT /F1 8 Tf (Net Carbs 6 g and 200 calories) Tj ET"
    findings = AuditAdvisoryAnalyzer().analyze(_doc(content_stream=cs), [])
    assert not [f for f in findings if f.inspection_id == "LPDF_NET_WEIGHT_VERIFY"]
