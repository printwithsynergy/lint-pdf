"""PR-X tests — FDA / CFIA legal-copy minimum size."""

from __future__ import annotations

import math

from lintpdf.analyzers.legal_copy_min_size import LegalCopyMinSizeAnalyzer
from lintpdf.semantic.events import TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc() -> SemanticDocument:
    page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def _event(
    *,
    font_size: float,
    rotation_deg: float = 0.0,
    font_name: str = "F1",
    page_num: int = 1,
    rendering_mode: int = 0,
    operator_index: int = 0,
) -> TextRenderedEvent:
    """Build a TextRenderedEvent at a given composed size + rotation."""
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


# ── Below threshold (axis-aligned) ────────────────────────────────────


def test_axis_aligned_4pt_fires() -> None:
    """4.0 pt horizontal text → LPDF_LEGALCOPY_001 (the legibility rule
    would NOT fire since rotation is 0)."""
    findings = LegalCopyMinSizeAnalyzer().analyze(_doc(), [_event(font_size=4.0)])
    assert len(findings) == 1
    f = findings[0]
    assert f.inspection_id == "LPDF_LEGALCOPY_001"
    assert f.severity.value == "advisory"
    assert f.details["font_size_pt"] == 4.0
    assert f.details["min_legal_pt"] == 5.0


def test_axis_aligned_at_threshold_no_finding() -> None:
    """Exactly 5.0 pt is acceptable per FDA / CFIA — no finding."""
    findings = LegalCopyMinSizeAnalyzer().analyze(_doc(), [_event(font_size=5.0)])
    assert findings == []


def test_above_threshold_no_finding() -> None:
    findings = LegalCopyMinSizeAnalyzer().analyze(_doc(), [_event(font_size=8.0)])
    assert findings == []


# ── Rotated text (no rotation requirement) ────────────────────────────


def test_rotated_small_text_also_fires() -> None:
    """Unlike LPDF_LEGIBILITY_001 this rule doesn't require rotation.
    Sub-5pt rotated text fires both rules (different IDs)."""
    findings = LegalCopyMinSizeAnalyzer().analyze(
        _doc(), [_event(font_size=4.0, rotation_deg=90.0)]
    )
    assert any(f.inspection_id == "LPDF_LEGALCOPY_001" for f in findings)


# ── Suppressions ──────────────────────────────────────────────────────


def test_invisible_text_suppressed() -> None:
    """Rendering mode 3 = invisible. Doesn't print, no legibility risk."""
    findings = LegalCopyMinSizeAnalyzer().analyze(_doc(), [_event(font_size=4.0, rendering_mode=3)])
    assert findings == []


def test_degenerate_size_suppressed() -> None:
    """Sub-2pt sizes are stray-glyph noise from outlined paths or
    transform artefacts, not body copy."""
    findings = LegalCopyMinSizeAnalyzer().analyze(_doc(), [_event(font_size=1.5)])
    assert findings == []


# ── Dedupe ────────────────────────────────────────────────────────────


def test_dedupe_per_page_font_size() -> None:
    """One ingredient block emits N glyph events at the same font + size.
    Should produce one finding, not N."""
    events = [_event(font_size=4.0, operator_index=i) for i in range(20)]
    findings = LegalCopyMinSizeAnalyzer().analyze(_doc(), events)
    assert len(findings) == 1


def test_distinct_sizes_emit_separate_findings() -> None:
    """Different sizes on the same page => separate findings."""
    events = [
        _event(font_size=4.0, operator_index=0),
        _event(font_size=3.5, operator_index=1),
    ]
    findings = LegalCopyMinSizeAnalyzer().analyze(_doc(), events)
    assert len(findings) == 2
