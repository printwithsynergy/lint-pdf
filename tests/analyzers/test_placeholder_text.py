"""Unit tests for ``LPDF_PLACEHOLDER_001`` (placeholder-text detector)."""

from __future__ import annotations

from lintpdf.analyzers.placeholder_text import PlaceholderTextAnalyzer
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(content: bytes, pages: int = 1) -> SemanticDocument:
    out = []
    for i in range(pages):
        out.append(
            SemanticPage(
                page_num=i + 1,
                media_box=PdfBox(0, 0, 612, 792),
                content_stream=content,
            )
        )
    return SemanticDocument(
        version="1.7",
        page_count=pages,
        is_encrypted=False,
        pages=out,
    )


def test_lot_number_fires() -> None:
    findings = PlaceholderTextAnalyzer().analyze(_doc(b"(LOT NUMBER) Tj"), events=[])
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_PLACEHOLDER_001"
    assert "LOT NUMBER" in findings[0].message


def test_date_code_fires() -> None:
    findings = PlaceholderTextAnalyzer().analyze(_doc(b"(DATE CODE) Tj"), events=[])
    assert len(findings) == 1
    assert findings[0].details["placeholder"] == "DATE CODE"


def test_front_back_panel_fires() -> None:
    findings = PlaceholderTextAnalyzer().analyze(
        _doc(b"(FRONT PANEL) Tj (BACK PANEL) Tj"), events=[]
    )
    labels = {f.details["placeholder"] for f in findings}
    assert "FRONT PANEL" in labels
    assert "BACK PANEL" in labels


def test_template_number_fires() -> None:
    findings = PlaceholderTextAnalyzer().analyze(_doc(b"(Template #114511) Tj"), events=[])
    assert len(findings) == 1
    assert findings[0].details["placeholder"] == "Template #..."


def test_bracketed_placeholder_fires() -> None:
    findings = PlaceholderTextAnalyzer().analyze(
        _doc(b"([BRAND NAME]) Tj ([STORE NAME]) Tj"), events=[]
    )
    # Both bracketed tokens collapse onto the same label so dedupe
    # gives us 1.
    assert len(findings) == 1
    assert findings[0].details["placeholder"] == "[BRACKETED PLACEHOLDER]"


def test_filled_in_lot_does_not_fire() -> None:
    """``Lot # ABC123`` is real data — must NOT trigger LOT NUMBER."""
    # Note: we only flag LOT NUMBER (with NUMBER literal), not Lot #
    findings = PlaceholderTextAnalyzer().analyze(_doc(b"(Lot # ABC123) Tj"), events=[])
    assert findings == []


def test_filled_in_best_before_does_not_fire() -> None:
    """``Best Before: 2026-01-01`` is real data; legitimate-phrase
    suppression should kick in."""
    findings = PlaceholderTextAnalyzer().analyze(_doc(b"(Best Before: 2026-01-01) Tj"), events=[])
    assert findings == []


def test_dedupe_per_page_and_label() -> None:
    """Same placeholder appearing twice on a page emits one finding."""
    findings = PlaceholderTextAnalyzer().analyze(
        _doc(b"(LOT NUMBER) Tj (LOT NUMBER) Tj"), events=[]
    )
    assert len(findings) == 1


def test_clean_artwork_emits_nothing() -> None:
    findings = PlaceholderTextAnalyzer().analyze(
        _doc(b"(Organic Green Tea Net Wt 250g) Tj"), events=[]
    )
    assert findings == []


def test_multi_page_separates_findings() -> None:
    """Each page gets its own finding for the same placeholder."""
    findings = PlaceholderTextAnalyzer().analyze(_doc(b"(LOT NUMBER) Tj", pages=3), events=[])
    pages = sorted(f.page_num for f in findings)
    assert pages == [1, 2, 3]
