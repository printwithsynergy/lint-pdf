"""Unit tests for ``LPDF_DIE_PERF_INDICATOR_NO_STEP`` (PR-J)."""

from __future__ import annotations

from lintpdf.analyzers.dieline_perf_indicator import DielinePerfIndicatorAnalyzer
from lintpdf.semantic.model import (
    DetectedTextRegion,
    PdfAnnotation,
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _box() -> PdfBox:
    return PdfBox(0, 0, 612, 792)


def _doc(
    *,
    spot_names: list[str] | None = None,
    detected: list[DetectedTextRegion] | None = None,
    annotations: list[PdfAnnotation] | None = None,
    fonts: dict | None = None,
    content_stream: bytes = b"",
) -> SemanticDocument:
    color_spaces: dict[str, PdfColorSpace] = {}
    for i, name in enumerate(spot_names or []):
        color_spaces[f"CS{i}"] = PdfColorSpace(
            name=f"CS{i}",
            cs_type="Separation",
            components=1,
            colorant_names=(name,),
        )
    page = SemanticPage(
        page_num=1,
        media_box=_box(),
        color_spaces=color_spaces,
        fonts=fonts or {},
        annotations=annotations or [],
        content_stream=content_stream,
        detected_text_regions=detected,
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


# ── Detection sources ──────────────────────────────────────────────


def test_ocr_text_region_with_tear_phrase_fires() -> None:
    region = DetectedTextRegion(
        bbox=PdfBox(10, 10, 200, 30),
        text="TEAR ACROSS / DECHIRER ICI",
        confidence=0.95,
    )
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline"], detected=[region]), events=[]
    )
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_DIE_PERF_INDICATOR_NO_STEP"
    assert findings[0].details["source"] == "ocr_text_region"
    assert findings[0].details["matched_phrase"] == "tear across"


def test_annotation_contents_with_perforation_fires() -> None:
    ann = PdfAnnotation(subtype="/FreeText", contents="Perforation here", page_num=1)
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline"], annotations=[ann]), events=[]
    )
    assert len(findings) == 1
    assert findings[0].details["source"] == "annotation"


def test_content_stream_tj_with_score_phrase_fires() -> None:
    # Live-text page: fonts present + Tj operator carrying "Score line"
    cs = b"BT /F1 12 Tf 100 700 Td (Score line) Tj ET"
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline"], fonts={"F1": object()}, content_stream=cs),
        events=[],
    )
    assert len(findings) == 1
    assert findings[0].details["source"] == "content_stream"


# ── Suppressors ────────────────────────────────────────────────────


def test_perforating_step_present_suppresses() -> None:
    """If a Perforating spot exists the converter has decomposition;
    don't double-flag even when art also says 'TEAR ACROSS'."""
    region = DetectedTextRegion(bbox=PdfBox(10, 10, 200, 30), text="TEAR ACROSS", confidence=0.9)
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline", "Perforating"], detected=[region]),
        events=[],
    )
    assert findings == []


def test_kisscut_step_present_suppresses() -> None:
    region = DetectedTextRegion(bbox=PdfBox(0, 0, 100, 20), text="kiss-cut", confidence=0.8)
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Cutting", "KissCut"], detected=[region]), events=[]
    )
    assert findings == []


def test_no_phrase_no_finding() -> None:
    region = DetectedTextRegion(bbox=PdfBox(0, 0, 100, 20), text="NET WT 28 g", confidence=0.95)
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline"], detected=[region]), events=[]
    )
    assert findings == []


def test_content_stream_skipped_for_outlined_page() -> None:
    """Outlined pages (no fonts) should rely on OCR; the content
    stream contains drawing ops that are not real text."""
    # Bytes happen to contain the string but the page has no fonts.
    cs = b"(perforation) Tj"  # raw — no font dict on page
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline"], content_stream=cs, fonts={}),
        events=[],
    )
    assert findings == []


# ── Multi-language coverage ────────────────────────────────────────


def test_french_dechirer_matches() -> None:
    region = DetectedTextRegion(bbox=PdfBox(0, 0, 100, 20), text="DÉCHIRER ICI", confidence=0.9)
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline"], detected=[region]), events=[]
    )
    assert len(findings) == 1
    assert findings[0].details["matched_phrase"] in ("déchirer", "dechirer")


def test_german_abreissen_matches() -> None:
    region = DetectedTextRegion(
        bbox=PdfBox(0, 0, 100, 20), text="Abreissen entlang", confidence=0.9
    )
    findings = DielinePerfIndicatorAnalyzer().analyze(
        _doc(spot_names=["Dieline"], detected=[region]), events=[]
    )
    assert len(findings) == 1


def test_no_spots_no_indicator_no_finding() -> None:
    findings = DielinePerfIndicatorAnalyzer().analyze(_doc(), events=[])
    assert findings == []
