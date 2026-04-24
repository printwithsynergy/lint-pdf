"""Unit tests for WS-6 Nutrition Facts Panel structural detector.

Covers the three-signal gate (header + nutrient vocab + numeric
values) and the integration with ``fda_nutrition.py`` so the two
Opus-disputed AI_FDA_003/004 findings on
``web_10p_test_final.pdf`` (a geometry-test page with "Nutrition
Facts" in copy but no actual panel) disappear.
"""

from __future__ import annotations

from lintpdf.ai.analyzers.regulatory_compliance.fda_nutrition import (
    FdaNutritionAnalyzer,
)
from lintpdf.ai.analyzers.regulatory_compliance.nfp_detector import (
    detect_nfp_regions,
    pages_with_nfp,
)
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _page(text: str, page_num: int = 1) -> SemanticPage:
    return SemanticPage(
        page_num=page_num,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=text.encode("latin-1"),
    )


def _doc(pages: list[SemanticPage]) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=len(pages),
        is_encrypted=False,
        pages=pages,
    )


_VALID_PANEL = (
    "Nutrition Facts\n"
    "Serving Size 1 bar (40g)\n"
    "Calories 180\n"
    "Total Fat 9g  11%\n"
    "Saturated Fat 2.5g  13%\n"
    "Sodium 140mg  6%\n"
    "Total Carbohydrate 22g  8%\n"
    "Dietary Fiber 4g\n"
    "Total Sugars 10g\n"
    "Protein 6g\n"
)


def test_detector_fires_on_valid_panel() -> None:
    regions = detect_nfp_regions(_page(_VALID_PANEL))
    assert len(regions) == 1
    r = regions[0]
    assert r.page_num == 1
    assert len(r.nutrient_tokens) >= 3
    assert r.numeric_values >= 2


def test_detector_rejects_header_only() -> None:
    # "Nutrition Facts" in marketing copy with no panel beneath.
    # This is the exact shape of the Opus-disputed false positives
    # on web_10p_test_final.pdf page 1 (the geometry-test page).
    text = "See Nutrition Facts for details. Visit our site."
    assert detect_nfp_regions(_page(text)) == []


def test_detector_rejects_nutrients_without_values() -> None:
    text = "Nutrition Facts\nCalories, Total Fat, Protein - see label.\n"
    assert detect_nfp_regions(_page(text)) == []


def test_detector_rejects_values_without_nutrients() -> None:
    text = "Nutrition Facts. 10g protein, 20g carbs in every serving!"
    # Only one nutrient token ("Protein"? no — just "protein" lowercase
    # matches the pattern too) — "Carbs" isn't in our closed vocab
    # (only Total Carbohydrate). Still short of 3.
    regions = detect_nfp_regions(_page(text))
    assert regions == []


def test_pages_with_nfp_collects_positive_pages() -> None:
    doc = _doc(
        [
            _page("Marketing copy, no panel here.", page_num=1),
            _page(_VALID_PANEL, page_num=2),
            _page("Nutrition Facts mentioned but no panel.", page_num=3),
        ]
    )
    assert pages_with_nfp(doc) == [2]


# -- integration: FDA rules short-circuit on no-panel pages -------------------


def test_fda_rules_silent_on_non_panel_page() -> None:
    doc = _doc([_page("Nutrition Facts blog post. Visit us online!", page_num=1)])
    findings = FdaNutritionAnalyzer().analyze(doc, [], pdf_bytes=b"")
    fda_003 = [f for f in findings if f.inspection_id == "AI_FDA_003"]
    fda_004 = [f for f in findings if f.inspection_id == "AI_FDA_004"]
    assert fda_003 == []
    assert fda_004 == []


def test_fda_rules_see_real_panel_page() -> None:
    """A real NFP page passes the WS-6 gate (detector returns the
    region), so downstream FDA rules get to run against real
    TextRenderedEvents when present. The analyzer's per-page
    check short-circuits when no text events are supplied, so we
    assert at the gate level -- the previous regex-only
    `_find_nutrition_panel_pages` would have matched any page
    containing 'Nutrition Facts', but this structural check only
    greenlights the valid panel."""
    doc = _doc(
        [
            _page("Nutrition Facts is a great blog.", page_num=1),
            _page(_VALID_PANEL, page_num=2),
        ]
    )
    # Directly observe the precondition the analyzer depends on.
    assert pages_with_nfp(doc) == [2]
    # And at the analyzer level, the no-panel page produces no
    # AI_FDA_004 noise (would previously have emitted "14 missing
    # nutrients").
    findings = FdaNutritionAnalyzer().analyze(doc, [], pdf_bytes=b"")
    assert [f for f in findings if f.page_num == 1] == []
