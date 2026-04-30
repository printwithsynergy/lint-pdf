"""Unit tests for WS-5 allergen-declaration context filter.

The 2026-04-23 Opus audit flagged one false-positive AI_EU1169_002
on Nutrops where "Gluten Free" on the front panel was treated as
an allergen declaration. The fix: a match only counts when it's
inside a declaration context (ingredients, contains:, may contain,
etc.) AND is NOT adjacent to a claim pattern (gluten-free, dairy-
free, etc.)."""

from __future__ import annotations

from lintpdf.ai.analyzers.regulatory_compliance.eu_fir_1169 import (
    EuFir1169Analyzer,
    _in_declaration_context,
)
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _ctx(document, events=None, pdf_bytes=b"", ai_config=None):
    """Build an AnalyzerContext for analyze_v2 calls."""
    from lintpdf.plugin.protocol import AnalyzerContext

    return AnalyzerContext(
        document=document,
        events=events or [],
        pdf_bytes=pdf_bytes,
        config={"ai_config": ai_config} if ai_config is not None else {},
    )


def _doc_with_text(text: str) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=text.encode("latin-1"),
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


# -- _in_declaration_context unit tests ---------------------------------------


def test_match_inside_ingredients_declaration_is_declaration() -> None:
    text = "Ingredients: wheat flour, water, salt."
    # "wheat" starts at 13
    start = text.find("wheat")
    assert _in_declaration_context(text, start, start + 5) is True


def test_match_inside_contains_block_is_declaration() -> None:
    text = "Allergen info. Contains: milk, eggs."
    start = text.find("milk")
    assert _in_declaration_context(text, start, start + 4) is True


def test_gluten_free_claim_is_not_declaration() -> None:
    text = "Certified Gluten Free. Ingredients: rice, water, sea salt."
    # "Gluten" inside "Gluten Free" claim — rejected.
    start = text.find("Gluten")
    assert _in_declaration_context(text, start, start + 6) is False


def test_no_anchor_on_page_is_not_declaration() -> None:
    text = "Marketing copy about wheat goodness. Enjoy responsibly."
    start = text.find("wheat")
    assert _in_declaration_context(text, start, start + 5) is False


# -- integration: AI_EU1169_002 end-to-end ------------------------------------


def test_gluten_free_front_panel_does_not_flag() -> None:
    """Reproduces the Nutrops Opus dispute: 'Gluten Free' on a
    front panel is a claim, not an allergen declaration — it must
    not produce AI_EU1169_002."""
    text = (
        "nutrops Functional Nootropics Gummies. "
        "Gluten Free. Non-GMO. Vegan. "
        "Ingredients: Organic rice, natural flavors, gum arabic."
    )
    findings = EuFir1169Analyzer().analyze_v2(_ctx(_doc_with_text(text), events=[], pdf_bytes=b""))
    allergen = [f for f in findings if f.inspection_id == "AI_EU1169_002"]
    assert allergen == [], (
        f"expected no allergen finding on a 'Gluten Free' claim page; "
        f"got {[f.message for f in allergen]}"
    )


def test_real_allergen_declaration_without_emphasis_still_flags() -> None:
    """Unemphasised 'Wheat' inside an ingredients list — the rule
    should still fire."""
    text = "Ingredients: wheat flour, sugar, vegetable oil."
    findings = EuFir1169Analyzer().analyze_v2(_ctx(_doc_with_text(text), events=[], pdf_bytes=b""))
    allergen = [f for f in findings if f.inspection_id == "AI_EU1169_002"]
    assert len(allergen) >= 1
