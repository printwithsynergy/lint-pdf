"""PR-Y tests — /Cutting spot overprint-flag check."""

from __future__ import annotations

from lintpdf.analyzers.cutting_overprint import CuttingOverprintAnalyzer
from lintpdf.semantic.events import (
    OverprintChangedEvent,
    PathPaintingEvent,
)
from lintpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(*, cutting_spot: str | None = "Cutting") -> SemanticDocument:
    """Build a doc with a Separation color space named after the given
    colorant. ``cutting_spot=None`` means no cutting spot in the doc."""
    color_spaces: dict[str, PdfColorSpace] = {}
    if cutting_spot is not None:
        color_spaces["CS_DIE"] = PdfColorSpace(
            name="CS_DIE",
            cs_type="Separation",
            components=1,
            colorant_names=(cutting_spot,),
        )
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=color_spaces,
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def _stroke_event(cs_name: str = "CS_DIE", page_num: int = 1, opi: int = 0) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="S",
        page_num=page_num,
        operator_index=opi,
        fill=False,
        stroke=True,
        stroke_color_space=cs_name,
        stroke_color_values=(1.0,),
    )


def _fill_event(cs_name: str = "CS_DIE", page_num: int = 1, opi: int = 0) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="f",
        page_num=page_num,
        operator_index=opi,
        fill=True,
        stroke=False,
        fill_color_space=cs_name,
        fill_color_values=(1.0,),
    )


def _op(
    stroke: bool | None = None, fill: bool | None = None, opi: int = 0
) -> OverprintChangedEvent:
    return OverprintChangedEvent(
        operator="gs",
        page_num=1,
        operator_index=opi,
        overprint_stroking=stroke,
        overprint_non_stroking=fill,
    )


# ── Cutting spot painted without OP fires ─────────────────────────────


def test_cutting_stroke_without_overprint_fires() -> None:
    """Default graphics state has OP=false. Stroke on Cutting spot fires."""
    findings = CuttingOverprintAnalyzer().analyze(_doc(), [_stroke_event()])
    assert len(findings) == 1
    f = findings[0]
    assert f.inspection_id == "LPDF_DIE_CUTTING_NOT_OVERPRINT"
    assert f.severity.value == "warning"
    assert f.details["colorant_name"] == "Cutting"
    assert f.details["operation"] == "stroke"


def test_cutting_fill_without_overprint_fires() -> None:
    findings = CuttingOverprintAnalyzer().analyze(_doc(), [_fill_event()])
    assert any(f.inspection_id == "LPDF_DIE_CUTTING_NOT_OVERPRINT" for f in findings)


def test_explicit_op_false_then_stroke_fires() -> None:
    events = [_op(stroke=False, opi=0), _stroke_event(opi=1)]
    findings = CuttingOverprintAnalyzer().analyze(_doc(), events)
    assert len(findings) == 1


# ── Overprint set: no finding ────────────────────────────────────────


def test_op_true_then_stroke_no_finding() -> None:
    events = [_op(stroke=True, opi=0), _stroke_event(opi=1)]
    findings = CuttingOverprintAnalyzer().analyze(_doc(), events)
    assert findings == []


def test_op_true_for_fill_then_fill_no_finding() -> None:
    events = [_op(fill=True, opi=0), _fill_event(opi=1)]
    findings = CuttingOverprintAnalyzer().analyze(_doc(), events)
    assert findings == []


def test_op_set_anywhere_in_stream_clears_finding() -> None:
    """First stroke is OP=false (would fire), but a later stroke with
    OP=true counts as overprinted at least once. Per-spot rule: if it
    overprinted somewhere we trust the converter — net no finding."""
    events = [
        _stroke_event(opi=0),  # OP=false default — would fire
        _op(stroke=True, opi=1),
        _stroke_event(opi=2),  # OP=true now
    ]
    findings = CuttingOverprintAnalyzer().analyze(_doc(), events)
    assert findings == []


# ── No cutting spot: silent ──────────────────────────────────────────


def test_no_cutting_spot_in_doc_no_finding() -> None:
    """Document has no dieline / cutting spot. Even if random strokes
    appear, the analyzer is a no-op."""
    findings = CuttingOverprintAnalyzer().analyze(
        _doc(cutting_spot=None), [_stroke_event(cs_name="CS1")]
    )
    assert findings == []


def test_non_dieline_spot_no_finding() -> None:
    """Document has a Pantone spot (not a dieline). No finding fires."""
    doc = _doc(cutting_spot="PANTONE 485 C")
    findings = CuttingOverprintAnalyzer().analyze(doc, [_stroke_event()])
    assert findings == []


# ── Dedupe: one finding per cutting spot ─────────────────────────────


def test_one_finding_per_spot_even_with_many_strokes() -> None:
    """20 stroke events on the cutting spot → 1 finding, not 20."""
    events = [_stroke_event(opi=i) for i in range(20)]
    findings = CuttingOverprintAnalyzer().analyze(_doc(), events)
    assert len(findings) == 1


# ── Variant dieline names ─────────────────────────────────────────────


def test_crease_spot_also_fires() -> None:
    """Dieline name matcher recognises Crease, Perf, Score, etc."""
    doc = _doc(cutting_spot="Crease")
    findings = CuttingOverprintAnalyzer().analyze(doc, [_stroke_event()])
    assert any(f.inspection_id == "LPDF_DIE_CUTTING_NOT_OVERPRINT" for f in findings)


def test_dieline_spot_also_fires() -> None:
    doc = _doc(cutting_spot="Dieline")
    findings = CuttingOverprintAnalyzer().analyze(doc, [_stroke_event()])
    assert any(f.inspection_id == "LPDF_DIE_CUTTING_NOT_OVERPRINT" for f in findings)
