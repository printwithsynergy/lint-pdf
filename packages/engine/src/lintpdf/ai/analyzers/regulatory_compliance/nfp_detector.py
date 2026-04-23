"""Nutrition Facts Panel structural detector.

The 2026-04-23 Opus audit flagged two false-positive
``AI_FDA_003`` / ``AI_FDA_004`` findings on a test PDF whose page
happened to contain the phrase "Nutrition Facts" in marketing
copy but had no actual NFP panel. The prior regex
``_find_nutrition_panel_pages`` only checked for the header
string, so any page that mentioned it became an "NFP page" and
reported every one of the 14 required nutrients as missing.

Structural detection here requires three independent signals,
all of which a real NFP carries:

1. The "Nutrition Facts" / "Nutrition Information" / "Supplement
   Facts" header (case-insensitive).
2. At least three tokens from a closed nutrient vocabulary
   (Calories, Total Fat, Saturated Fat, etc.).
3. At least two numeric values with an NFP-compatible unit
   (``g``, ``mg``, ``mcg``, ``kcal``, or percentage).

A header without nutrients, or nutrients without numeric values,
no longer counts as a panel and downstream FDA rules short-
circuit on that page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.semantic.model import SemanticDocument

# Header anchors. ``re.IGNORECASE`` at use site.
_HEADER_PATTERNS = (
    re.compile(r"\bNutrition\s+Facts\b", re.IGNORECASE),
    re.compile(r"\bNutrition\s+Information\b", re.IGNORECASE),
    re.compile(r"\bSupplement\s+Facts\b", re.IGNORECASE),
)

# Closed nutrient vocabulary. The detector requires >= 3 of these
# to appear on a page before it qualifies as an NFP.
_NUTRIENT_TOKENS = (
    re.compile(r"\bCalories\b", re.IGNORECASE),
    re.compile(r"\bTotal\s+Fat\b", re.IGNORECASE),
    re.compile(r"\bSaturated\s+Fat\b", re.IGNORECASE),
    re.compile(r"\bTrans\s+Fat\b", re.IGNORECASE),
    re.compile(r"\bCholesterol\b", re.IGNORECASE),
    re.compile(r"\bSodium\b", re.IGNORECASE),
    re.compile(r"\bTotal\s+Carbohydrate", re.IGNORECASE),
    re.compile(r"\bDietary\s+Fib(?:re|er)\b", re.IGNORECASE),
    re.compile(r"\bTotal\s+Sugars?\b", re.IGNORECASE),
    re.compile(r"\bAdded\s+Sugars?\b", re.IGNORECASE),
    re.compile(r"\bProtein\b", re.IGNORECASE),
    re.compile(r"\bVitamin\s+[A-E]\d*\b", re.IGNORECASE),
    re.compile(r"\bCalcium\b", re.IGNORECASE),
    re.compile(r"\bIron\b", re.IGNORECASE),
    re.compile(r"\bPotassium\b", re.IGNORECASE),
)

# Numeric value + unit. Captures ``12g``, ``2.5 mg``, ``260 kcal``,
# ``15%``. The detector requires >= 2 distinct matches on the page
# so a header plus one stray "0g" from marketing copy doesn't
# qualify.
_VALUE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:g\b|mg\b|mcg\b|kcal\b|%)", re.IGNORECASE
)

_MIN_NUTRIENT_TOKENS = 3
_MIN_NUMERIC_VALUES = 2


@dataclass
class NfpPanelRegion:
    """Positive detection result for a Nutrition Facts panel on
    one page.

    ``bbox`` is left as ``None`` for now -- the text-based detector
    can't reliably localise a region without layout data from the
    upstream pipeline. Downstream callers treat a non-None region
    as "panel present on this page" and scope their checks to the
    whole page; WS-6 doesn't need sub-page bounds.
    """

    page_num: int
    nutrient_tokens: list[str]
    numeric_values: int
    confidence: float
    bbox: tuple[float, float, float, float] | None = None


def _page_text(page: object) -> str:
    raw = getattr(page, "content_stream", None)
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        try:
            return raw.decode("latin-1")
        except Exception:
            return ""
    return str(raw)


def detect_nfp_regions(page: object) -> list[NfpPanelRegion]:
    """Return one ``NfpPanelRegion`` when the page carries a
    structurally valid Nutrition Facts panel, or an empty list
    when any of the three signals (header, nutrient tokens,
    numeric values) falls short of its threshold.

    Deliberately returns a list rather than ``Optional[...]`` so
    future per-region localisation (e.g. multi-panel mixed
    labels) slots in without an API break.
    """
    text = _page_text(page)
    if not text:
        return []

    # Signal 1: header.
    if not any(p.search(text) for p in _HEADER_PATTERNS):
        return []

    # Signal 2: closed-vocab nutrient tokens (dedup by pattern id).
    matched_tokens: list[str] = []
    for pattern in _NUTRIENT_TOKENS:
        match = pattern.search(text)
        if match is not None:
            matched_tokens.append(match.group(0))
    if len(matched_tokens) < _MIN_NUTRIENT_TOKENS:
        return []

    # Signal 3: numeric values with NFP-compatible units.
    value_count = len(_VALUE_PATTERN.findall(text))
    if value_count < _MIN_NUMERIC_VALUES:
        return []

    # Confidence is just the number of nutrient matches normalised
    # to the full vocab size, clamped to [0, 1]. Callers can use
    # it as a soft signal; the hard gate is the thresholds above.
    confidence = min(1.0, len(matched_tokens) / len(_NUTRIENT_TOKENS) * 2)

    return [
        NfpPanelRegion(
            page_num=int(getattr(page, "page_num", 0) or 0),
            nutrient_tokens=matched_tokens,
            numeric_values=value_count,
            confidence=confidence,
        )
    ]


def pages_with_nfp(document: SemanticDocument) -> list[int]:
    """Convenience wrapper: return the page numbers on which the
    structural detector fires. Replaces the old keyword-only
    ``_find_nutrition_panel_pages`` in ``fda_nutrition.py``."""
    out: list[int] = []
    for page in document.pages:
        if detect_nfp_regions(page):
            out.append(int(getattr(page, "page_num", 0) or 0))
    return out
