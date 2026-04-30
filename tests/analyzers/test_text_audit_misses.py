"""PR-N tests — text audit miss closures.

* PlaceholderTextAnalyzer extended to scan ``page.detected_text_regions``
  so outlined fixtures' placeholder text is no longer silent.
* SpotNameSimilarityAnalyzer extended with token-level comparison so
  '/Dark Biege' vs '/Faint Beige' siblings get caught despite having
  too-far whole-string Levenshtein distance.
"""

from __future__ import annotations

from siftpdf.analyzers.placeholder_text import PlaceholderTextAnalyzer
from siftpdf.analyzers.spot_name_similarity import SpotNameSimilarityAnalyzer
from siftpdf.semantic.model import (
    DetectedTextRegion,
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)

# ── PlaceholderTextAnalyzer (OCR scan) ─────────────────────────────


def _doc_with_regions(regions: list[DetectedTextRegion]) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=b"",  # outlined — no live text
        detected_text_regions=regions,
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def test_lot_number_in_ocr_region_fires() -> None:
    region = DetectedTextRegion(bbox=PdfBox(100, 100, 200, 110), text="LOT NUMBER", confidence=0.95)
    findings = PlaceholderTextAnalyzer().analyze(_doc_with_regions([region]), [])
    placeholders = [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]
    assert len(placeholders) == 1
    assert placeholders[0].details["placeholder"] == "LOT NUMBER"
    assert placeholders[0].details["source"] == "ocr"


def test_date_code_in_ocr_region_fires() -> None:
    region = DetectedTextRegion(bbox=PdfBox(0, 0, 50, 10), text="DATE CODE", confidence=0.9)
    findings = PlaceholderTextAnalyzer().analyze(_doc_with_regions([region]), [])
    assert any(x.inspection_id == "LPDF_PLACEHOLDER_001" for x in findings)


def test_template_id_in_ocr_region_fires() -> None:
    region = DetectedTextRegion(
        bbox=PdfBox(0, 0, 100, 10), text="Template # 114511", confidence=0.85
    )
    findings = PlaceholderTextAnalyzer().analyze(_doc_with_regions([region]), [])
    assert any(x.inspection_id == "LPDF_PLACEHOLDER_001" for x in findings)


def test_no_placeholder_in_ocr_region_no_finding() -> None:
    region = DetectedTextRegion(bbox=PdfBox(0, 0, 100, 10), text="NET WT 28 g", confidence=0.95)
    findings = PlaceholderTextAnalyzer().analyze(_doc_with_regions([region]), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]


def test_dedupe_across_live_and_ocr_sources() -> None:
    """Same placeholder appearing in both content stream and OCR
    regions should fire ONCE per page."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=b"BT (LOT NUMBER) Tj ET",
        detected_text_regions=[
            DetectedTextRegion(bbox=PdfBox(0, 0, 50, 10), text="LOT NUMBER", confidence=0.9)
        ],
    )
    doc = SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])
    findings = PlaceholderTextAnalyzer().analyze(doc, [])
    placeholders = [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]
    assert len(placeholders) == 1


# ── SpotNameSimilarityAnalyzer (token-level) ────────────────────────


def _doc_with_spots(spot_names: list[str]) -> SemanticDocument:
    color_spaces = {}
    for i, name in enumerate(spot_names):
        color_spaces[f"CS{i}"] = PdfColorSpace(
            name=f"CS{i}",
            cs_type="Separation",
            components=1,
            colorant_names=(name,),
        )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                color_spaces=color_spaces,
            )
        ],
    )


def test_token_typo_dark_biege_vs_beige_siblings_fires() -> None:
    """The audit-flagged Amalgam_Catalyst case: '/Dark Biege' should
    be caught against its '/Faint Beige', '/Lt Beige', '/Med Beige'
    siblings — the misspelled token 'Biege' is 2 edits from 'Beige'
    which appears verbatim across the others."""
    doc = _doc_with_spots(["Dark Biege", "Faint Beige", "Lt Beige", "Med Beige"])
    findings = SpotNameSimilarityAnalyzer().analyze(doc, [])
    typo = [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert any(f.details.get("token_a") in ("biege", "beige") for f in typo), (
        f"expected a beige/biege token typo finding, got: {[(f.details.get('name_a'), f.details.get('name_b')) for f in typo]}"
    )


def test_distinct_color_families_no_finding() -> None:
    doc = _doc_with_spots(["Dark Beige", "Lt Beige", "Med Beige", "Lt Red", "Dark Red"])
    findings = SpotNameSimilarityAnalyzer().analyze(doc, [])
    assert not [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_TYPO"]


def test_token_typo_no_verbatim_match_no_finding() -> None:
    """If the typo token has no verbatim companion in the rest of
    the inventory, suppress — too noisy."""
    doc = _doc_with_spots(
        ["Lt Foo", "Md Boo"]
    )  # foo / boo are 1 edit apart but neither verbatim elsewhere
    findings = SpotNameSimilarityAnalyzer().analyze(doc, [])
    typo = [x for x in findings if x.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert all("token_a" not in (x.details or {}) for x in typo)
