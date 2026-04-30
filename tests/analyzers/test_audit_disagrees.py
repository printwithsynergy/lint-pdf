"""PR-P tests — audit disagree closures.

Two regressions surfaced by the post-merge Opus 4.7 audit's disagree
list (8 disagrees pre-PR-P, 2 expected after):

1. ``_canonical_colorant`` did not strip trailing punctuation, so
   ``/PANTONE 3582 C.  `` (with stray dot + spaces) failed the
   ``upper.endswith(" C")`` test inside the spot-suffix check and
   spuriously fired LPDF_SPOT_003 ``missing_suffix`` even though
   the C suffix was present.

2. ``is_supplement_document`` only matched literal "Supplement
   Facts" / "Dietary Supplement" strings. On Nutrops_SF the panel
   header is encoded as positioned glyphs (Identity-H + per-char
   Tj operators) so the literal string never appears in the raw
   content stream, and the gate failed to suppress AI_COSM /
   AI_FDA findings on what is clearly a dietary supplement.
"""

from __future__ import annotations

from siftpdf.ai.analyzers.regulatory_compliance._gates import is_supplement_document
from siftpdf.analyzers.spot_color_analyzer import _canonical_colorant
from siftpdf.semantic.model import (
    PdfBox,
    SemanticDocument,
    SemanticPage,
)

# ── _canonical_colorant trailing-punctuation strip ────────────────


def test_pantone_with_trailing_dot_and_spaces_canonicalises_clean() -> None:
    """The Cherry-Twist disagree case."""
    assert _canonical_colorant("/PANTONE 3582 C.  ") == "PANTONE 3582 C"


def test_pantone_with_trailing_comma_canonicalises_clean() -> None:
    assert _canonical_colorant("PANTONE 485 C,") == "PANTONE 485 C"


def test_pantone_clean_unchanged() -> None:
    assert _canonical_colorant("PANTONE 485 C") == "PANTONE 485 C"


def test_lower_then_canonicalises_uppercase() -> None:
    assert _canonical_colorant("pantone 485 c") == "PANTONE 485 C"


# ── is_supplement_document broader patterns ───────────────────────


def _doc_with_content(content: bytes) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=content,
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def test_legacy_supplement_facts_still_detected() -> None:
    doc = _doc_with_content(b"BT (Supplement Facts) Tj ET")
    assert is_supplement_document(doc) is True


def test_dietary_supplement_phrase_detected() -> None:
    doc = _doc_with_content(b"This is a Dietary Supplement product")
    assert is_supplement_document(doc) is True


def test_gummies_indicator_detected() -> None:
    """Nutrops_SF and similar — header glyphs missed but
    'gummies' indicator survives."""
    doc = _doc_with_content(b"60 Vegan Gummies per bottle")
    assert is_supplement_document(doc) is True


def test_softgels_indicator_detected() -> None:
    doc = _doc_with_content(b"30 Softgels")
    assert is_supplement_document(doc) is True


def test_other_ingredients_label_detected() -> None:
    doc = _doc_with_content(b"Other Ingredients: Gelatin, Water, Glycerin")
    assert is_supplement_document(doc) is True


def test_two_supplement_nutrients_detected() -> None:
    doc = _doc_with_content(b"Vitamins per serving: Folic Acid 400mcg, Biotin 30mcg")
    assert is_supplement_document(doc) is True


def test_nfp_label_text_does_not_falsely_trigger() -> None:
    """Nutrition Facts panel without supplement markers should NOT
    be treated as a supplement document."""
    doc = _doc_with_content(b"Nutrition Facts. Calories 240, Total Fat 12g, Protein 4g")
    assert is_supplement_document(doc) is False


def test_empty_document_no_finding() -> None:
    doc = _doc_with_content(b"")
    assert is_supplement_document(doc) is False
