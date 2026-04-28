"""Unit tests for ``LPDF_LEGIBILITY_001`` (small + rotated text)."""

from __future__ import annotations

from lintpdf.analyzers.legibility_composite import LegibilityCompositeAnalyzer
from lintpdf.semantic.events import TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc() -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


def _event(
    *,
    font_size: float,
    font_name: str = "T1_0",
    page_num: int = 1,
    rotation_deg: float = 0.0,
    rendering_mode: int = 0,
    operator_index: int = 0,
) -> TextRenderedEvent:
    """Build a TextRenderedEvent with specified composed font size + rotation."""
    import math

    cos_r = math.cos(math.radians(rotation_deg))
    sin_r = math.sin(math.radians(rotation_deg))
    ctm = TransformationMatrix(cos_r, sin_r, -sin_r, cos_r, 0, 0)
    tm = TransformationMatrix(1, 0, 0, 1, 0, 0)
    return TextRenderedEvent(
        operator="Tj",
        page_num=page_num,
        operator_index=operator_index,
        font_name=font_name,
        font_size=font_size,
        ctm=ctm,
        text_matrix=tm,
        rendering_mode=rendering_mode,
    )


def test_small_rotated_fires() -> None:
    """5 pt @ 90° rotation → fires."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=5.0, rotation_deg=90.0)]
    )
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_LEGIBILITY_001"


def test_small_axis_aligned_does_not_fire() -> None:
    """5 pt at 0° rotation → silent (jurisdiction rules cover this)."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=5.0, rotation_deg=0.0)]
    )
    assert findings == []


def test_large_rotated_does_not_fire() -> None:
    """8 pt rotated → silent (above legibility threshold)."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=8.0, rotation_deg=90.0)]
    )
    assert findings == []


def test_skewed_text_does_not_fire() -> None:
    """5 pt rotated 30° (below ~45° threshold) → silent."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=5.0, rotation_deg=30.0)]
    )
    assert findings == []


def test_invisible_text_does_not_fire() -> None:
    """rendering_mode=3 is invisible — legibility math doesn't apply."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=5.0, rotation_deg=90.0, rendering_mode=3)]
    )
    assert findings == []


def test_degenerate_sub_2pt_does_not_fire() -> None:
    """Sub-2pt sizes are stray glyphs, not real text."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=1.0, rotation_deg=90.0)]
    )
    assert findings == []


def test_dedupe_per_page_font_size_rotation() -> None:
    """Multiple TextRendered events at the same (page, font, size,
    rotation bucket) → one finding."""
    events = [_event(font_size=5.0, rotation_deg=90.0, operator_index=i) for i in range(10)]
    findings = LegibilityCompositeAnalyzer().analyze(_doc(), events)
    assert len(findings) == 1


def test_270_degree_rotation_fires() -> None:
    """270° rotation (vertical text the other way) → fires."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=5.0, rotation_deg=270.0)]
    )
    assert len(findings) == 1


def test_45_degree_boundary_fires() -> None:
    """At exactly 45° we want it to fire — sin(45°) ≈ 0.707 > 0.7."""
    findings = LegibilityCompositeAnalyzer().analyze(
        _doc(), [_event(font_size=5.0, rotation_deg=45.0)]
    )
    assert len(findings) == 1
