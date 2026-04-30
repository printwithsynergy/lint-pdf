"""Unit tests for WS-13 new universal rules.

* ``LPDF_COLOR_021`` — Rich black text of any size (advisory).
  Complements the existing ``LPDF_COLOR_008`` warning by firing
  on display type as well as small text.
* ``LPDF_STROKE_007`` — Multi-ink stroke 0.5pt-1.0pt (advisory).
  Fills the gap between ``LPDF_STROKE_004`` (< 0.5pt, warning)
  and silence on thicker rules.

Neither rule is gated on brand palette: "Text and Thin Elements
SHOULD NEVER BE RICH BLACK" is a universal print-production
principle.
"""

from __future__ import annotations

from siftpdf.analyzers.color import ColorAnalyzer
from siftpdf.analyzers.finding import Severity
from siftpdf.analyzers.hairline import HairlineAnalyzer
from siftpdf.semantic.events import PathPaintingEvent, TextRenderedEvent
from siftpdf.semantic.graphics_state import TransformationMatrix
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc() -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _text_event(
    *,
    font_size: float,
    color_values: tuple[float, float, float, float] = (0.4, 0.3, 0.2, 1.0),
    color_space: str = "DeviceCMYK",
) -> TextRenderedEvent:
    return TextRenderedEvent(
        operator="Tj",
        page_num=1,
        operator_index=0,
        font_name="F1",
        font_size=font_size,
        ctm=TransformationMatrix.identity(),
        text_matrix=TransformationMatrix.identity(),
        color_space=color_space,
        color_values=color_values,
    )


def _stroke_event(
    *,
    line_width: float,
    stroke_color_values: tuple[float, float, float, float] = (0.4, 0.3, 0.2, 1.0),
    stroke_color_space: str = "DeviceCMYK",
) -> PathPaintingEvent:
    return PathPaintingEvent(
        operator="S",
        page_num=1,
        operator_index=0,
        fill=False,
        stroke=True,
        stroke_color_space=stroke_color_space,
        stroke_color_values=stroke_color_values,
        line_width=line_width,
    )


# -- LPDF_COLOR_021 (Rich black text, any size) ------------------------------


def test_small_multi_ink_text_fires_both_008_and_021() -> None:
    """10pt CMYK text with 4 inks fires both the legacy warning
    (LPDF_COLOR_008) and the new universal advisory
    (LPDF_COLOR_021). Back-compat preserved; catalog grows."""
    findings = ColorAnalyzer().analyze(_doc(), [_text_event(font_size=10.0)])
    by_id = {f.inspection_id: f for f in findings}
    assert "LPDF_COLOR_008" in by_id
    assert "LPDF_COLOR_021" in by_id
    assert by_id["LPDF_COLOR_008"].severity == Severity.WARNING
    assert by_id["LPDF_COLOR_021"].severity == Severity.ADVISORY


def test_large_multi_ink_text_fires_only_021() -> None:
    """14pt CMYK text with 4 inks stays out of LPDF_COLOR_008
    (small-text scope unchanged) but still surfaces as an
    advisory via the new universal LPDF_COLOR_021 rule."""
    findings = ColorAnalyzer().analyze(_doc(), [_text_event(font_size=14.0)])
    ids = {f.inspection_id for f in findings}
    assert "LPDF_COLOR_008" not in ids
    assert "LPDF_COLOR_021" in ids
    rb = [f for f in findings if f.inspection_id == "LPDF_COLOR_021"]
    assert rb[0].severity == Severity.ADVISORY


def test_pure_k_text_fires_neither() -> None:
    """Pure-K text is what we want customers to ship — no findings."""
    findings = ColorAnalyzer().analyze(
        _doc(),
        [_text_event(font_size=10.0, color_values=(0.0, 0.0, 0.0, 1.0))],
    )
    ids = {f.inspection_id for f in findings}
    assert "LPDF_COLOR_008" not in ids
    assert "LPDF_COLOR_021" not in ids


def test_rgb_text_fires_neither_universal_rule() -> None:
    """Non-CMYK text cannot be 'rich black' by definition."""
    findings = ColorAnalyzer().analyze(
        _doc(),
        [
            _text_event(
                font_size=10.0,
                color_space="DeviceRGB",
                color_values=(0.1, 0.2, 0.3, 0.0),
            )
        ],
    )
    ids = {f.inspection_id for f in findings}
    assert "LPDF_COLOR_008" not in ids
    assert "LPDF_COLOR_021" not in ids


def test_color_021_details_expose_ink_count() -> None:
    """Details payload carries the ink count + effective size so
    the viewer can render 'rich black text @ 18pt (3 inks)'."""
    findings = ColorAnalyzer().analyze(
        _doc(),
        [_text_event(font_size=18.0, color_values=(0.3, 0.0, 0.2, 1.0))],
    )
    rb = [f for f in findings if f.inspection_id == "LPDF_COLOR_021"]
    assert len(rb) == 1
    d = rb[0].details or {}
    assert d["non_zero_inks"] == 3
    assert d["effective_size"] == 18.0
    assert d["color_values"] == [0.3, 0.0, 0.2, 1.0]


# -- LPDF_STROKE_007 (multi-ink mid-weight stroke) ---------------------------


def test_mid_weight_multi_ink_stroke_fires_only_007() -> None:
    """A 0.7pt CMYK stroke with 3 inks fires the new advisory
    without re-tripping the stricter LPDF_STROKE_004 warning
    (which stays scoped to < 0.5pt)."""
    findings = HairlineAnalyzer().analyze(
        _doc(),
        [_stroke_event(line_width=0.7, stroke_color_values=(0.5, 0.4, 0.0, 1.0))],
    )
    ids = {f.inspection_id for f in findings}
    assert "LPDF_STROKE_004" not in ids
    assert "LPDF_STROKE_007" in ids
    new = [f for f in findings if f.inspection_id == "LPDF_STROKE_007"]
    assert new[0].severity == Severity.ADVISORY


def test_thin_multi_ink_stroke_still_fires_004_only() -> None:
    """A 0.3pt CMYK stroke with 3 inks stays on the existing
    LPDF_STROKE_004 warning; the new advisory does not
    double-fire below the 0.5pt boundary."""
    findings = HairlineAnalyzer().analyze(
        _doc(),
        [_stroke_event(line_width=0.3, stroke_color_values=(0.5, 0.4, 0.0, 1.0))],
    )
    ids = {f.inspection_id for f in findings}
    assert "LPDF_STROKE_004" in ids
    assert "LPDF_STROKE_007" not in ids


def test_thick_multi_ink_stroke_fires_neither() -> None:
    """A 2.0pt stroke is outside both the tight (< 0.5pt) and
    mid-weight (0.5-1.0pt) bands - the 'thin elements' principle
    no longer applies."""
    findings = HairlineAnalyzer().analyze(
        _doc(),
        [_stroke_event(line_width=2.0, stroke_color_values=(0.5, 0.4, 0.0, 1.0))],
    )
    ids = {f.inspection_id for f in findings}
    assert "LPDF_STROKE_004" not in ids
    assert "LPDF_STROKE_007" not in ids


def test_pure_k_mid_weight_stroke_fires_neither() -> None:
    """Pure-K 0.7pt stroke is the recommended output."""
    findings = HairlineAnalyzer().analyze(
        _doc(),
        [_stroke_event(line_width=0.7, stroke_color_values=(0.0, 0.0, 0.0, 1.0))],
    )
    ids = {f.inspection_id for f in findings}
    assert "LPDF_STROKE_004" not in ids
    assert "LPDF_STROKE_007" not in ids


def test_stroke_007_details_expose_ink_count() -> None:
    """Details payload carries the ink count + line width so the
    viewer can render 'multi-ink 0.7pt stroke (3 inks)'."""
    findings = HairlineAnalyzer().analyze(
        _doc(),
        [_stroke_event(line_width=0.7, stroke_color_values=(0.5, 0.4, 0.0, 1.0))],
    )
    stroke = [f for f in findings if f.inspection_id == "LPDF_STROKE_007"]
    assert len(stroke) == 1
    d = stroke[0].details or {}
    assert d["non_zero_inks"] == 3
    assert d["line_width"] == 0.7
    assert d["stroke_color_values"] == [0.5, 0.4, 0.0, 1.0]


def test_boundary_1pt_stroke_fires_007() -> None:
    """The 1.0pt upper bound is inclusive — still flagged as
    advisory. Above 1.0pt we stay silent (see thick-stroke test)."""
    findings = HairlineAnalyzer().analyze(
        _doc(),
        [_stroke_event(line_width=1.0, stroke_color_values=(0.5, 0.4, 0.0, 1.0))],
    )
    ids = {f.inspection_id for f in findings}
    assert "LPDF_STROKE_007" in ids
