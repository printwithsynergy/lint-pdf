"""PR-V tests — placeholder analyzer hardening.

* Tj-operand flattening so split-glyph text matches the regex
  patterns (Pink-Slush p2, HSI_OUTLINED).
* New seal/finishing technical labels (OVERLAP IN SEAL, END SEAL,
  SEAL AREA, DIE CUT AREA) — DailyFiber multi-up case.
"""

from __future__ import annotations

from siftpdf.analyzers.placeholder_text import PlaceholderTextAnalyzer
from siftpdf.semantic.model import (
    PdfBox,
    SemanticDocument,
    SemanticPage,
)


def _doc(content: bytes) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=content,
        fonts={"F1": object()},
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


# ── Tj-operand flattening ─────────────────────────────────────────


def test_flattened_glyph_split_lot_number_fires() -> None:
    """Pink-Slush p2 case: each character emitted as its own Tj."""
    cs = (
        b"BT /F1 8 Tf 100 700 Td (L) Tj (O) Tj (T) Tj ( ) Tj "
        b"(N) Tj (U) Tj (M) Tj (B) Tj (E) Tj (R) Tj ET"
    )
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    placeholders = [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]
    assert len(placeholders) == 1
    assert placeholders[0].details["placeholder"] == "LOT NUMBER"
    assert placeholders[0].details["source"] == "live_flattened"


def test_flattened_date_code_fires() -> None:
    cs = b"BT /F1 8 Tf (D) Tj (A) Tj (T) Tj (E) Tj ( ) Tj (C) Tj (O) Tj (D) Tj (E) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    assert any(x.inspection_id == "LPDF_PLACEHOLDER_001" for x in findings)


def test_flattened_skip_when_already_caught_by_live_path() -> None:
    """When the raw stream contains the literal phrase, the live
    path catches it. Dedupe should keep us at one finding even when
    flattening would reproduce the same match."""
    cs = b"BT /F1 8 Tf (LOT NUMBER) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    placeholders = [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]
    assert len(placeholders) == 1


def test_flatten_handles_balanced_parens_in_string() -> None:
    """Literal strings can contain escaped/balanced parens. The
    parser must consume them without breaking the operand sweep."""
    cs = b"BT /F1 8 Tf (LOT (test)) Tj (NUMBER) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    # The flattened text would be "LOT (test) NUMBER". The
    # placeholder regex \bLOT\s+NUMBER\b only matches contiguous
    # tokens, so this case should NOT fire — confirming the parser
    # handled the balanced parens without crashing.
    assert not any(x.inspection_id == "LPDF_PLACEHOLDER_001" for x in findings)


def test_no_tj_operator_no_flatten_match() -> None:
    """Strings that aren't followed by Tj/TJ shouldn't be flattened."""
    cs = b"BT /F1 8 Tf (LOT NUMBER) ET"  # no Tj
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    # The raw stream still contains "LOT NUMBER" as a regex match,
    # so the live path catches it. The flattened path should
    # produce empty (no Tj operands).
    placeholders = [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]
    assert len(placeholders) == 1
    assert placeholders[0].details["source"] == "live"


# ── New seal/finishing technical labels ────────────────────────────


def test_overlap_in_seal_fires() -> None:
    cs = b"BT /F1 8 Tf (OVERLAP IN SEAL) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    placeholders = [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]
    assert len(placeholders) == 1
    assert placeholders[0].details["placeholder"] == "OVERLAP IN SEAL"


def test_end_seal_fires() -> None:
    cs = b"BT /F1 8 Tf (END SEAL) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    assert any(x.inspection_id == "LPDF_PLACEHOLDER_001" for x in findings)


def test_seal_area_fires() -> None:
    cs = b"BT /F1 8 Tf (SEAL AREA) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    assert any(x.inspection_id == "LPDF_PLACEHOLDER_001" for x in findings)


def test_die_cut_area_fires() -> None:
    cs = b"BT /F1 8 Tf (DIE CUT AREA) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    assert any(x.inspection_id == "LPDF_PLACEHOLDER_001" for x in findings)


def test_unrelated_seal_text_no_finding() -> None:
    """Non-technical mention of 'seal' shouldn't fire."""
    cs = b"BT /F1 8 Tf (Sealed for freshness) Tj ET"
    findings = PlaceholderTextAnalyzer().analyze(_doc(cs), [])
    assert not [x for x in findings if x.inspection_id == "LPDF_PLACEHOLDER_001"]
