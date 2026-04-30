"""Unit tests for ``LPDF_SPOT_NAME_TYPO`` + ``LPDF_SPOT_NAME_CASE``."""

from __future__ import annotations

from siftpdf.analyzers.spot_name_similarity import (
    SpotNameSimilarityAnalyzer,
    _levenshtein,
)
from siftpdf.semantic.model import (
    PdfBox,
    PdfColorSpace,
    SemanticDocument,
    SemanticPage,
)


def _doc(*colorant_names: str) -> SemanticDocument:
    color_spaces = {}
    for i, name in enumerate(colorant_names):
        cs = PdfColorSpace(
            name=f"CS{i}",
            cs_type="Separation",
            components=1,
            colorant_names=(name,),
        )
        color_spaces[f"CS{i}"] = cs
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[
            SemanticPage(
                page_num=1,
                media_box=PdfBox(0, 0, 612, 792),
                color_spaces=color_spaces,
            )
        ],
    )


# -- Levenshtein helper -----------------------------------------------------


def test_levenshtein_identical_zero() -> None:
    assert _levenshtein("Beige", "Beige") == 0


def test_levenshtein_one_edit() -> None:
    assert _levenshtein("Biege", "Beige") == 2  # swap two adjacent letters


def test_levenshtein_short_circuits_far_pairs() -> None:
    """Length difference > max → ``max + 1`` (short-circuit)."""
    assert _levenshtein("a", "abcdefgh", max_dist=2) == 3


# -- typo detection ---------------------------------------------------------


def test_biege_beige_flagged() -> None:
    """Canonical case from the audit: '/Dark Biege' vs '/Dark Beige'."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("Dark Beige", "Dark Biege"), events=[])
    typos = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert len(typos) == 1
    pair = {typos[0].details["name_a"], typos[0].details["name_b"]}
    assert pair == {"Dark Beige", "Dark Biege"}


def test_distinct_colors_not_flagged() -> None:
    """Real different beiges shouldn't trigger."""
    findings = SpotNameSimilarityAnalyzer().analyze(
        _doc("Med Beige", "Lt Beige", "Faint Beige"), events=[]
    )
    # ``Med Beige`` vs ``Lt Beige`` is 2-edit-distance; that's at the
    # boundary — actually let me compute: M-e-d → L-t = swap 3 chars,
    # so distance is 3. Should NOT flag. Verify.
    typos = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert typos == []


def test_pantone_pairs_not_flagged() -> None:
    """``PANTONE 225 C`` and ``PANTONE 226 C`` are 1 edit apart but
    intentionally distinct — must not flag."""
    findings = SpotNameSimilarityAnalyzer().analyze(
        _doc("PANTONE 225 C", "PANTONE 226 C"), events=[]
    )
    typos = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert typos == []


def test_process_names_not_flagged() -> None:
    """Process channel names handled by LPDF_SPOT_DUPE_PROCESS, not here."""
    findings = SpotNameSimilarityAnalyzer().analyze(
        _doc("Cyan", "Cian"),
        events=[],  # 'Cian' would be a typo, but excluded
    )
    typos = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert typos == []


def test_short_names_skip_typo_check() -> None:
    """Names < 4 chars don't go through the typo check (too noisy)."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("Red", "Rad"), events=[])
    typos = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert typos == []


def test_pair_dedupe_two_typos() -> None:
    """Each unordered pair emits at most one finding."""
    findings = SpotNameSimilarityAnalyzer().analyze(
        _doc("Pumpkin", "Pumkin", "Coral", "Corral"), events=[]
    )
    typos = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert len(typos) == 2


# -- case detection ---------------------------------------------------------


def test_case_inconsistency_flagged() -> None:
    """``BUFF`` and ``Buff`` are the same colorant in different casing."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("BUFF", "Buff"), events=[])
    case = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_CASE"]
    assert len(case) == 1


def test_three_way_case_inconsistency() -> None:
    """Three casings of one name → one finding listing all three."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("Beige", "BEIGE", "beige"), events=[])
    case = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_CASE"]
    assert len(case) == 1
    assert len(case[0].details["variants"]) == 3


def test_case_check_skips_pantone() -> None:
    """``PANTONE 225 C`` and ``pantone 225 C`` (case mismatch on
    Pantone) — Pantone names are excluded entirely."""
    findings = SpotNameSimilarityAnalyzer().analyze(
        _doc("PANTONE 225 C", "pantone 225 C"), events=[]
    )
    case = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_CASE"]
    assert case == []


# -- clean documents --------------------------------------------------------


def test_clean_inventory_emits_nothing() -> None:
    findings = SpotNameSimilarityAnalyzer().analyze(
        _doc("PMS185", "PANTONE 7401 C", "Cyan", "Magenta", "Yellow", "Black"),
        events=[],
    )
    assert findings == []


def test_single_spot_emits_nothing() -> None:
    """Need at least 2 names to compare."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("PMS185"), events=[])
    assert findings == []


# -- whitespace / trailing punctuation -------------------------------------


def test_trailing_whitespace_flagged() -> None:
    """Cherry-Twist ``PANTONE 3582 C.  `` from the audit — trailing
    period + spaces produce a separately named plate from the clean
    name."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("PANTONE 3582 C.  "), events=[])
    ws = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_WHITESPACE"]
    assert len(ws) == 1
    assert ws[0].details["raw_name"] == "PANTONE 3582 C.  "
    assert ws[0].details["cleaned_name"] == "PANTONE 3582 C"


def test_leading_whitespace_flagged() -> None:
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("  Dark Beige"), events=[])
    ws = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_WHITESPACE"]
    assert len(ws) == 1
    assert ws[0].details["cleaned_name"] == "Dark Beige"


def test_trailing_punctuation_alone_flagged() -> None:
    """Just a trailing period (no spaces) still produces a separate plate."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("Buff."), events=[])
    ws = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_WHITESPACE"]
    assert len(ws) == 1
    assert ws[0].details["cleaned_name"] == "Buff"


def test_clean_name_not_flagged() -> None:
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("PANTONE 3582 C"), events=[])
    ws = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_WHITESPACE"]
    assert ws == []


def test_whitespace_applies_to_pantone() -> None:
    """The whitespace check must NOT exclude Pantone names — the stray
    whitespace IS the defect, even on a Pantone name."""
    findings = SpotNameSimilarityAnalyzer().analyze(_doc("PANTONE 3582 C.  "), events=[])
    ws = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_WHITESPACE"]
    assert len(ws) == 1


def test_whitespace_dedupe() -> None:
    """Same dirty name appearing twice → one finding, not two."""
    # Note: ``_doc`` deduplicates by exact original string already (the
    # color_spaces dict + seen_exact set in _collect_spot_names), so
    # duplicating the same string in two color-spaces still yields one
    # spot-name entry. This test guards against a future where that
    # dedupe is loosened — the whitespace_seen set in the analyzer
    # itself should still emit only one finding per raw name.
    doc = _doc("PANTONE 3582 C.  ", "PANTONE 3582 C.  ")
    findings = SpotNameSimilarityAnalyzer().analyze(doc, events=[])
    ws = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_WHITESPACE"]
    assert len(ws) == 1


def test_whitespace_and_typo_can_coexist() -> None:
    """A document with both a dirty Pantone name AND a typo-pair on
    custom colors emits both findings."""
    findings = SpotNameSimilarityAnalyzer().analyze(
        _doc("PANTONE 3582 C.  ", "Dark Beige", "Dark Biege"), events=[]
    )
    ws = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_WHITESPACE"]
    typos = [f for f in findings if f.inspection_id == "LPDF_SPOT_NAME_TYPO"]
    assert len(ws) == 1
    assert len(typos) == 1
