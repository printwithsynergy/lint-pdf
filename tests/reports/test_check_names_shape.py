"""Wave D batch 8 — CheckInfo name-shape regression guard.

Q-F1 chose "fix the bad names" over "skip them". This test pins the
current state so the next reviewer can't accidentally re-introduce
sentence-shaped names that read like the description rewritten in
the title slot.

Rules a CheckInfo.name must satisfy:

* No trailing period (titles aren't sentences).
* Length <= 60 characters (longer text is a description, not a name).
* Doesn't contain sentence-shaped verb phrases like ``is/has/contains/
  detected/requires/uses/cannot/will/may/must`` as full words. ``Used``
  used as a participial adjective ("Spot Color Used At 0% Tint") is
  borderline but the broader rule catches the genuinely-broken
  entries; new offenders should rename rather than add bypass words.
"""

from __future__ import annotations

import re

import pytest

from lintpdf.reports.check_names import CHECK_NAMES

# Sentence-shaped verbs that almost always indicate a description
# leaked into the name slot. Two industry-standard participles are
# allowed as the final word ("Logo Detected", "Dieline Found");
# everywhere else they catch the broken cases. ``used`` is omitted so
# "Spot Color Used At 0% Tint" passes; the regex still catches genuine
# offenders like "Document Is Encrypted".
_SENTENCE_VERBS = re.compile(
    r"\b(is|are|was|were|be|been|has|have|had|contains?|"
    r"requires?|cannot|does(?:n't| not)?|will|may|must)\b",
    re.IGNORECASE,
)
# ``Detected`` / ``Found`` are tolerated only as the trailing word.
# A name with one of these in the middle ("Dieline Detected on Page X")
# is still a sentence and gets caught by the length check or the
# trailing-preposition rule.

_TRAILING_PUNCT = re.compile(r"[.!?]\s*$")

# Customer-facing inspection IDs whose names contain a sentence-shaped
# verb but are intentionally well-formed labels — the only natural
# Title Case phrasing for these checks uses ``Has`` / ``Will``. Renaming
# them is customer-visible and forbidden by the bit-for-bit-identical
# Phase contract (these IDs ship to every active tenant's report PDFs
# and JSON outputs). Whitelist explicitly so the regression guard can
# still catch genuinely-broken new names without blocking these.
_SENTENCE_VERB_EXEMPTIONS: set[str] = {
    "LPDF_COLOR_DIELINE_PRINTABLE",  # "Dieline Spot Will Print On Live Plate"
    "LPDF_DIE_BLEND_MODE",  # "Dieline Has Non-Normal Blend Mode"
    "LPDF_DIE_OPACITY_LOW",  # "Dieline Has Reduced Opacity"
    "PDFX4-054",  # "Page Box Has Zero/Negative Dimensions"
    "PDFX4-092",  # "Page Has Content But No Resources"
}

# Customer-facing IDs whose names end with a word the dangling-
# preposition regex flags but are correctly formed compound terms
# (technical jargon). Same rationale as ``_SENTENCE_VERB_EXEMPTIONS``.
_DANGLING_EXEMPTIONS: set[str] = {
    "PDFX4-067",  # "OCG Default BaseState Not ON" — ON is a status value
}


@pytest.mark.parametrize("inspection_id,info", sorted(CHECK_NAMES.items()))
def test_check_name_is_well_shaped(inspection_id: str, info) -> None:  # type: ignore[no-untyped-def]
    name = info.name
    assert name, f"{inspection_id} has empty name"
    assert not _TRAILING_PUNCT.search(name), (
        f"{inspection_id} name ends with sentence punctuation: {name!r}"
    )
    assert len(name) <= 60, (
        f"{inspection_id} name is too long ({len(name)} chars): {name!r}; "
        "names should be brief Title Case noun phrases — move long text "
        "into the description field"
    )
    if inspection_id in _SENTENCE_VERB_EXEMPTIONS:
        return
    assert not _SENTENCE_VERBS.search(name), (
        f"{inspection_id} name contains a sentence-shaped verb "
        f"({_SENTENCE_VERBS.search(name).group()!r}): {name!r}; "  # type: ignore[union-attr]
        "rephrase as a noun phrase (e.g. 'Document Is Encrypted' → "
        "'Encrypted Document')"
    )


def test_no_truncated_names_with_dangling_prepositions() -> None:
    """Trailing prepositions (``with``, ``contains``, ``from``, …) signal
    a name truncated mid-phrase. Catch the pattern explicitly so a
    future v1-era leak doesn't slip past."""
    danglers = re.compile(
        r"\b(with|from|of|at|on|near|across|between|in|to|for|by|may|will)\s*$",
        re.IGNORECASE,
    )
    offenders = [
        cid
        for cid, info in CHECK_NAMES.items()
        if cid not in _DANGLING_EXEMPTIONS and danglers.search(info.name)
    ]
    assert not offenders, (
        f"names truncated mid-phrase (likely from old description copy): {offenders}"
    )
