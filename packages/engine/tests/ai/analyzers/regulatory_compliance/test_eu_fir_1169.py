"""Unit tests for ``AI_EU1169_001`` after WS-2 swap.

Focus: the 14 disputed findings from the 2026-04-23 Opus audit
(large logo text flagged as "1 pt, x-height 0.17 mm") must no
longer fire. The fix is structural — read the composed Tm x CTM
scale rather than the raw Tf operand — so the test synthesises a
``TextRenderedEvent`` with the Nutrops logo matrices and asserts
no finding is emitted. A second test with identity matrices at
nominal 1 pt asserts the true-positive path still fires.
"""

from __future__ import annotations

from lintpdf.ai.analyzers.regulatory_compliance.eu_fir_1169 import (
    EuFir1169Analyzer,
)
from lintpdf.semantic.events import TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import PdfBox, PdfFont, SemanticDocument, SemanticPage


def _doc_with_ingredients(page_num: int = 1) -> SemanticDocument:
    """EU_FIR_1169 only runs when 'ingredients' keyword is on a
    page — add it to the content stream so the analyzer doesn't
    short-circuit before the x-height check."""
    page = SemanticPage(
        page_num=page_num,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=b"(Ingredients: flour, water) Tj",
    )
    page.fonts["F1"] = PdfFont(
        name="F1",
        base_font="Helvetica",
        font_type="Type1",
        embedded=False,
        subset=False,
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


def _text_event(
    *,
    page_num: int = 1,
    font_size: float,
    tm_scale: float = 1.0,
    ctm_scale: float = 1.0,
) -> TextRenderedEvent:
    return TextRenderedEvent(
        operator="Tj",
        page_num=page_num,
        operator_index=0,
        font_name="F1",
        font_size=font_size,
        text_matrix=TransformationMatrix(a=tm_scale, d=tm_scale),
        ctm=TransformationMatrix(a=ctm_scale, d=ctm_scale),
        bbox=(100.0, 100.0, 200.0, 140.0),
    )


def test_nutrops_logo_scenario_does_not_flag() -> None:
    """Tf=1.0, Tm.a=72, CTM.a=1.5 → 108 pt on page.

    This is the exact shape of the 14 disputed EU_FIR_1169_001
    findings from the 2026-04-23 Opus audit on
    ``Test1_Nutrops_LS_Dieline.pdf``."""
    doc = _doc_with_ingredients()
    event = _text_event(font_size=1.0, tm_scale=72.0, ctm_scale=1.5)
    findings = EuFir1169Analyzer().analyze(doc, [event], pdf_bytes=b"")
    x_height_findings = [f for f in findings if f.inspection_id == "AI_EU1169_001"]
    assert x_height_findings == [], (
        f"expected no x-height finding for a 108pt logo; got {len(x_height_findings)}: "
        f"{[f.message for f in x_height_findings]}"
    )


def test_genuinely_tiny_text_still_flags() -> None:
    """A 0.8pt font with identity matrices renders at 0.8pt — well
    below the 1.2 mm threshold. True positive must still fire."""
    doc = _doc_with_ingredients()
    event = _text_event(font_size=0.8)
    findings = EuFir1169Analyzer().analyze(doc, [event], pdf_bytes=b"")
    x_height_findings = [f for f in findings if f.inspection_id == "AI_EU1169_001"]
    assert len(x_height_findings) == 1, (
        "expected a finding on 0.8pt body text; got "
        f"{len(x_height_findings)}"
    )
