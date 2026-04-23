"""Unit tests for WS-4 Prop 65 proximity exclusion in AI_GHS_003.

The 2026-04-23 Opus audit flagged one false-positive ``AI_GHS_003``
on a dietary-supplement page where the text was:

    "WARNING: This product can expose you to chemicals including
     lead, known to the State of California to cause cancer."

That's a Prop 65 cautionary statement under California Health &
Safety Code 25249.5, not a CLP/GHS hazard statement. The filter
keeps this from tripping the rule while still firing on genuine
CLP content that also appears on the page.
"""

from __future__ import annotations

from lintpdf.ai.analyzers.regulatory_compliance.ghs_clp import GhsClpAnalyzer
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


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


def test_prop65_warning_alone_does_not_trigger_ghs_003() -> None:
    text = (
        "WARNING: This product can expose you to chemicals including "
        "lead, known to the State of California to cause cancer. For "
        "more information go to www.P65Warnings.ca.gov."
    )
    findings = GhsClpAnalyzer().analyze(_doc_with_text(text), [], pdf_bytes=b"")
    ghs003 = [f for f in findings if f.inspection_id == "AI_GHS_003"]
    assert ghs003 == []


def test_real_h_statement_still_triggers_even_alongside_prop65() -> None:
    """A page that carries both a Prop 65 disclaimer AND a real CLP
    H-statement must still produce AI_GHS_003 — the H-statement is
    CLP-regulated regardless of whether the signal words are
    suppressed as Prop 65."""
    text = (
        "WARNING: Proposition 65 cancer warning. "
        "DANGER. Causes serious eye damage. H318."
    )
    findings = GhsClpAnalyzer().analyze(_doc_with_text(text), [], pdf_bytes=b"")
    ghs003 = [f for f in findings if f.inspection_id == "AI_GHS_003"]
    assert len(ghs003) == 1
    # The H-statement is CLP-specific and carries the finding; the
    # signal-word list in the emitted details is filtered down,
    # which is the whole point of the Prop 65 exclusion.
    details = ghs003[0].details or {}
    assert "H318" in details.get("h_statements", [])


def test_clp_warning_without_prop65_still_triggers() -> None:
    """Plain 'WARNING: Causes skin irritation' with no Prop 65
    anchor anywhere on the page still fires — the filter only
    suppresses signal words that are actually near Prop 65 text."""
    text = "WARNING: Causes skin irritation. Avoid contact with eyes."
    findings = GhsClpAnalyzer().analyze(_doc_with_text(text), [], pdf_bytes=b"")
    ghs003 = [f for f in findings if f.inspection_id == "AI_GHS_003"]
    assert len(ghs003) == 1
