"""DimensionCalloutAnalyzer — flags technical dimension callouts left
in artwork (should live on a separate spec/dimension layer).

The 2026-04-28 Opus audit flagged this on multiple stick-pack fixtures:
*"Dimension callouts (2.4409\", 5.7500\", 10 mm) and 'LOT NUMBER /
DATE CODE' placeholder appear to be live on the artwork page rather
than on a separate technical/info layer; they will print unless
removed or moved to a non-printing layer."*

Detection signal: pages that contain multiple standalone-dimension
text tokens (e.g. ``2.4409"``, ``5.7500"``, ``10mm``) — bare
numeric+unit strings that are NOT embedded in body copy. Real label
copy says "Net Wt. 250g" or "240ml serving" with surrounding
context; technical drawing dimensions appear isolated.

Check ID:
    LPDF_DIM_CALLOUT_001 — Dimension callouts left in artwork.
        Severity: WARNING. Per-page dedupe.

Calibration:
* Threshold: at least 2 standalone-dimension tokens on the same page.
  A single ``250g`` from ingredients is not a callout signal; two
  bare measurements (``2.4409"`` + ``5.7500"``) almost always are.
* Token shape: optional sign, digits, optional decimal, optional
  whitespace, unit suffix. The whole match must be word-bounded;
  surrounding non-numeric/non-unit characters disqualify.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Dimension callout pattern. Captures the digits + unit. The
# surrounding context check (``_is_standalone_dimension``) ensures
# we only count dimensions that aren't part of body copy like
# ``"Net Wt. 250g"`` or ``"4 oz / 113g"``.
_DIMENSION_PATTERN = re.compile(
    r"(?P<num>\d{1,4}(?:\.\d+)?)\s*"
    r"(?P<unit>mm|cm|in|inch(?:es)?|\"|pt|px)"
    # Boundary: not followed by another letter, so "250mm" matches
    # but "10minimum" doesn't. Letter-class lookahead works for both
    # letter units (mm, cm, in, pt, px) and the literal-quote inch
    # mark (\b doesn't fire between two non-word chars).
    r"(?![A-Za-z])",
    re.IGNORECASE,
)

# Words / patterns that, if present within ~30 chars of a dimension,
# strongly suggest the dimension is real-world product copy rather
# than a technical callout. Suppresses "Net Wt. 5.5 oz", "Serving
# size: 240ml", "20 ft above sea level", etc.
_PRODUCT_COPY_NEIGHBOURS = re.compile(
    r"\b(?:net\s+wt|net\s+weight|serving\s+size|contains|capacity|"
    r"volume|qty|quantity|fl\s*oz|oz|ml|gram|gramme|liter|litre|"
    r"each|per\s+serving|per\s+unit)\b",
    re.IGNORECASE,
)

# Minimum number of standalone-dimension tokens per page for the
# rule to fire. A single isolated dimension is not enough signal.
_MIN_DIMENSIONS_PER_PAGE = 2


def _is_standalone_dimension(text: str, start: int, end: int) -> bool:
    """True when the dimension match at [start, end) doesn't sit
    inside a product-copy context (Net Wt., Serving Size, etc.).

    Examines a 30-char window on either side of the match. Suppresses
    the dimension if any of the ``_PRODUCT_COPY_NEIGHBOURS`` patterns
    appear within that window.
    """
    window_start = max(0, start - 30)
    window_end = min(len(text), end + 30)
    window = text[window_start:window_end]
    return not _PRODUCT_COPY_NEIGHBOURS.search(window)


class DimensionCalloutAnalyzer(BaseAnalyzer):
    """Flag dimension callouts left in artwork (should be on a
    separate spec/dimension layer)."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []

        for page in document.pages:
            raw = page.content_stream
            if not raw:
                continue
            try:
                text = raw.decode("latin-1") if isinstance(raw, bytes) else str(raw)
            except Exception:
                continue

            standalone: list[str] = []
            for m in _DIMENSION_PATTERN.finditer(text):
                if _is_standalone_dimension(text, m.start(), m.end()):
                    snippet = m.group(0).strip()
                    if snippet not in standalone:
                        standalone.append(snippet)

            if len(standalone) < _MIN_DIMENSIONS_PER_PAGE:
                continue

            findings.append(
                Finding(
                    inspection_id="LPDF_DIM_CALLOUT_001",
                    severity=Severity.WARNING,
                    message=(
                        f"Dimension callouts found on page {page.page_num} "
                        f"({len(standalone)} standalone measurements: "
                        f"{', '.join(standalone[:5])}"
                        f"{', ...' if len(standalone) > 5 else ''}). "
                        "These technical dimensions should live on a "
                        "separate spec / dimension layer (set to "
                        "non-printing) rather than the live artwork — "
                        "they will print unless removed before plate-making."
                    ),
                    page_num=page.page_num,
                    details={
                        "standalone_dimensions": standalone,
                        "count": len(standalone),
                    },
                    category="geometry",
                    object_type="text",
                )
            )
        return findings
