"""PR-W tests — GS1 quiet-zone-on-fold barcode check.

Reuses the ``DielineResult`` attached to ``SemanticDocument`` by the
orchestrator. Tests construct synthetic candidates + a stub result so
no PDF is rendered.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lintpdf.analyzers.barcode import BarcodeAnalyzer, _BarcodeCandidate
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


@dataclass
class _StubDielineResult:
    source: str = "name"
    regions: list[dict[str, float]] = field(default_factory=list)
    polylines: list[list[list[float]]] = field(default_factory=list)


def _doc(*, dieline: _StubDielineResult | None = None) -> SemanticDocument:
    page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 600, 800))
    doc = SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])
    doc.dieline_result = dieline
    return doc


def _candidate(
    bbox: tuple[float, float, float, float], narrow_bar: float = 0.5
) -> _BarcodeCandidate:
    c = _BarcodeCandidate(page_num=1)
    x0, y0, x1, y1 = bbox
    c.add_stroke(narrow_bar, bbox=(x0, y0, x0 + narrow_bar, y1))
    c.add_stroke(narrow_bar, bbox=(x1 - narrow_bar, y0, x1, y1))
    c.stroke_widths = [narrow_bar] * 30
    return c


# ── DielineResult overlapping the quiet zone ──────────────────────────


def test_fold_region_overlaps_quiet_zone_fires() -> None:
    """Barcode at (100,100)-(200,200) with narrow_bar=0.5pt has a 5pt
    quiet zone (10x). A fold region at (193,90)-(199,210) sits fully
    inside the quiet-zone halo, so the check fires.
    """
    dl = _StubDielineResult(
        regions=[{"x0": 193, "y0": 90, "x1": 199, "y1": 210}],
    )
    doc = _doc(dieline=dl)
    c = _candidate((100, 100, 200, 200))
    findings = BarcodeAnalyzer()._check_fold_proximity([c], doc)
    ids = [f.inspection_id for f in findings]
    assert ids.count("LPDF_BARCODE_QUIET_ZONE_ON_FOLD") == 1
    f = findings[0]
    assert f.severity.value == "warning"
    assert f.page_num == 1
    assert f.details["dieline_source"] == "name"


def test_fold_region_outside_quiet_zone_no_finding() -> None:
    """Same barcode, but fold sits 50pt away — well outside the 5pt
    quiet zone — so the check does not fire.
    """
    dl = _StubDielineResult(
        regions=[{"x0": 260, "y0": 90, "x1": 280, "y1": 210}],
    )
    doc = _doc(dieline=dl)
    c = _candidate((100, 100, 200, 200))
    findings = BarcodeAnalyzer()._check_fold_proximity([c], doc)
    assert not findings


def test_polyline_fallback_when_regions_empty() -> None:
    """When ``regions`` is empty but ``polylines`` carries a closed
    polygon overlapping the quiet zone, the check still fires using
    the polygon's bbox.
    """
    dl = _StubDielineResult(
        polylines=[[[195, 100], [199, 100], [199, 200], [195, 200], [195, 100]]],
    )
    doc = _doc(dieline=dl)
    c = _candidate((100, 100, 200, 200))
    findings = BarcodeAnalyzer()._check_fold_proximity([c], doc)
    assert any(f.inspection_id == "LPDF_BARCODE_QUIET_ZONE_ON_FOLD" for f in findings)


def test_dieline_missing_no_finding() -> None:
    """When dieline_result is None or source='missing' the check is
    a silent no-op (defensive — never fail when geometry is absent).
    """
    doc = _doc(dieline=None)
    c = _candidate((100, 100, 200, 200))
    assert BarcodeAnalyzer()._check_fold_proximity([c], doc) == []

    doc2 = _doc(dieline=_StubDielineResult(source="missing"))
    assert BarcodeAnalyzer()._check_fold_proximity([c], doc2) == []


def test_one_finding_per_barcode_even_with_multiple_folds() -> None:
    """Step-and-repeat sheets carry many fold regions. Don't emit
    a duplicate per-fold finding — one per barcode is the correct
    operator-facing signal.
    """
    dl = _StubDielineResult(
        regions=[
            {"x0": 193, "y0": 90, "x1": 199, "y1": 210},
            {"x0": 196, "y0": 95, "x1": 198, "y1": 205},
            {"x0": 100, "y0": 100, "x1": 200, "y1": 200},
        ],
    )
    doc = _doc(dieline=dl)
    c = _candidate((100, 100, 200, 200))
    findings = BarcodeAnalyzer()._check_fold_proximity([c], doc)
    assert len(findings) == 1
