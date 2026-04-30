"""Unit tests for ``LPDF_DIM_CALLOUT_001`` (dimension callouts in artwork)."""

from __future__ import annotations

from siftpdf.analyzers.dimension_callout import DimensionCalloutAnalyzer
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


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


def test_two_inch_callouts_fire() -> None:
    findings = DimensionCalloutAnalyzer().analyze(_doc(b'(2.4409") Tj (5.7500") Tj'), events=[])
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_DIM_CALLOUT_001"


def test_inch_plus_mm_fires() -> None:
    findings = DimensionCalloutAnalyzer().analyze(_doc(b'(2.4409") Tj (10mm) Tj'), events=[])
    assert len(findings) == 1


def test_two_pt_callouts_fire() -> None:
    findings = DimensionCalloutAnalyzer().analyze(_doc(b"(8.5pt) Tj (17pt) Tj"), events=[])
    assert len(findings) == 1


def test_concat_matrix_operator_does_not_fire() -> None:
    """The original v1 bug: ``\\d+ \\d+ \\d+ \\d+ \\d+ \\d+ cm`` matrix
    operators matched the unit pattern in raw bytes. The v2 ``(...)``
    string-only matcher must NOT trigger on these."""
    cs = b"q\n1 0 0 1 100 200 cm\nBT\n0 0 0 RG\n12 0 0 12 0 0 Tm\n(Hello world) Tj\nET\nQ\n"
    findings = DimensionCalloutAnalyzer().analyze(_doc(cs), events=[])
    assert findings == []


def test_single_dimension_does_not_fire() -> None:
    """Single isolated dimension is not enough signal."""
    findings = DimensionCalloutAnalyzer().analyze(_doc(b"(10mm) Tj"), events=[])
    assert findings == []


def test_only_mm_dimensions_does_not_fire() -> None:
    """Bare ``5cm`` / ``250mm`` callouts in body copy aren't a
    reliable spec-layer signal — fire only when at least one is a
    technical unit (in/pt/px/")."""
    findings = DimensionCalloutAnalyzer().analyze(_doc(b"(10mm) Tj (5cm) Tj"), events=[])
    assert findings == []


def test_dimension_inside_body_copy_does_not_fire() -> None:
    """``(Net Wt. 250g)`` is a single-string body-copy event that
    doesn't match the standalone-dimension pattern (g isn't a unit
    here, and the whole string isn't pure dimension)."""
    findings = DimensionCalloutAnalyzer().analyze(
        _doc(b'(Net Wt. 250g) Tj (Best by 12") Tj'), events=[]
    )
    # ``Best by 12"`` doesn't fully match the pattern (text before the
    # number), so 0 standalone dims — no finding.
    assert findings == []


def test_per_page_dedupe() -> None:
    """One finding per page even if many dimensions are present."""
    cs = b'(1") Tj (2") Tj (3") Tj (4") Tj (5") Tj'
    findings = DimensionCalloutAnalyzer().analyze(_doc(cs), events=[])
    assert len(findings) == 1
    assert findings[0].details["count"] == 5


def test_multiple_pages_fire_separately() -> None:
    """Each page gets its own finding."""
    findings = DimensionCalloutAnalyzer().analyze(
        _doc(b'(2.4409") Tj (5.7500") Tj', pages=3), events=[]
    )
    pages = sorted(f.page_num for f in findings)
    assert pages == [1, 2, 3]


def test_clean_artwork_emits_nothing() -> None:
    findings = DimensionCalloutAnalyzer().analyze(
        _doc(b"(Organic Green Tea Net Wt 250g) Tj (Best by 2026) Tj"), events=[]
    )
    assert findings == []


def test_message_includes_examples() -> None:
    findings = DimensionCalloutAnalyzer().analyze(
        _doc(b'(2.4409") Tj (5.7500") Tj (10mm) Tj'), events=[]
    )
    msg = findings[0].message
    assert "2.4409" in msg or "5.7500" in msg or "10mm" in msg
