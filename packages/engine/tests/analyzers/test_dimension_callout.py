"""Unit tests for ``LPDF_DIM_CALLOUT_001`` (dimension callouts in artwork)."""

from __future__ import annotations

from lintpdf.analyzers.dimension_callout import DimensionCalloutAnalyzer
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


def test_two_dimensions_inches_fires() -> None:
    findings = DimensionCalloutAnalyzer().analyze(_doc(b'(2.4409") Tj (5.7500") Tj'), events=[])
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_DIM_CALLOUT_001"


def test_two_dimensions_mm_fires() -> None:
    findings = DimensionCalloutAnalyzer().analyze(_doc(b"(10mm) Tj (5mm) Tj"), events=[])
    assert len(findings) == 1


def test_mixed_units_fires() -> None:
    """``2.4409"`` + ``10mm`` on the same page → fires."""
    findings = DimensionCalloutAnalyzer().analyze(_doc(b'(2.4409") Tj (10mm) Tj'), events=[])
    assert len(findings) == 1


def test_single_dimension_does_not_fire() -> None:
    """Single isolated dimension is not enough signal."""
    findings = DimensionCalloutAnalyzer().analyze(_doc(b"(10mm) Tj"), events=[])
    assert findings == []


def test_net_weight_does_not_fire() -> None:
    """Real product copy: ``Net Wt. 250g`` is not a callout."""
    findings = DimensionCalloutAnalyzer().analyze(
        _doc(b"(Net Wt. 250g) Tj (Net wt 5.5oz) Tj"), events=[]
    )
    # ``g`` and ``oz`` aren't in our unit set anyway, so nothing
    # matches. Keep the test for documentation; the assertion is
    # that we don't fire either way.
    assert findings == []


def test_serving_size_does_not_fire() -> None:
    """``Serving Size 240ml`` should be suppressed by neighbour
    context even if the unit pattern matched."""
    findings = DimensionCalloutAnalyzer().analyze(
        _doc(b"(Serving Size: 240ml in 1 cup) Tj (Serving Size: 12mm bites) Tj"),
        events=[],
    )
    assert findings == []


def test_pt_dimensions_fire() -> None:
    """Layout-spec dimensions in points (``8.5pt``, ``17pt``)."""
    findings = DimensionCalloutAnalyzer().analyze(_doc(b"(8.5pt) Tj (17pt) Tj"), events=[])
    assert len(findings) == 1


def test_per_page_dedupe() -> None:
    """One finding per page even if 10 dimensions are present."""
    content = b"(1mm) Tj (2mm) Tj (3mm) Tj (4mm) Tj (5mm) Tj"
    findings = DimensionCalloutAnalyzer().analyze(_doc(content), events=[])
    assert len(findings) == 1
    # Dimension count surfaces in details
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
