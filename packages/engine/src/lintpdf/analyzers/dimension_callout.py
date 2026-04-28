"""DimensionCalloutAnalyzer — flags technical dimension callouts left
in artwork (should live on a separate spec/dimension layer).

The 2026-04-28 Opus audit flagged this on multiple stick-pack fixtures:
*"Dimension callouts (2.4409\", 5.7500\", 10 mm) and 'LOT NUMBER /
DATE CODE' placeholder appear to be live on the artwork page rather
than on a separate technical/info layer."*

V2 (2026-04-28b) — restricted matching to text strings ``(...)`` /
``<hex>`` inside the content stream so PDF operators like ``cm``
(concat-matrix) no longer match as a unit suffix. The original v1
matched anywhere in the raw bytes and produced thousands of false
positives on stick-pack fixtures whose content streams use
``\\d+ \\d+ \\d+ \\d+ \\d+ \\d+ cm`` matrix transforms hundreds of
times per page.

Check ID:
    LPDF_DIM_CALLOUT_001 — Dimension callouts left in artwork.
        Severity: WARNING. Per-page dedupe.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# PDF text strings inside a content stream are wrapped in parens
# (literal strings) or angle brackets (hex strings). We only inspect
# parenthesized literals because hex strings in this corpus are
# unlikely to encode a dimension callout.
_PDF_LITERAL_STRING = re.compile(rb"\(([^()\\]{1,40})\)")

# Standalone-dimension pattern. Whole-string match: just a number +
# unit, optionally with whitespace / trailing punctuation. The whole
# parenthesised string content must match.
_STANDALONE_DIMENSION = re.compile(
    r"^\s*\d{1,4}(?:\.\d+)?\s*"
    r"(?:mm|cm|in|inch(?:es)?|\"|pt|px)"
    r"\s*[\.\,]?\s*$",
    re.IGNORECASE,
)

# Per-page minimum count to fire. Two or more standalone dimensions
# on the same page is a strong signal of a technical callout block.
_MIN_DIMENSIONS_PER_PAGE = 2

# Require at least one technical-unit callout (in / pt / px / inch
# mark) to anchor the finding. Bare ``5cm`` / ``250mm`` text events
# are common in body copy ("5 cm pieces") and not a reliable
# spec-layer signal. NB: ``\b`` between digit and letter doesn't
# fire (both are word chars), so use a non-letter lookahead/behind
# instead — works for ``8.5pt``, ``5"``, ``10in``.
_TECHNICAL_UNITS_RE = re.compile(
    r"(?:^|[^A-Za-z])(?:in|inch(?:es)?|pt|px|\")(?![A-Za-z])",
    re.IGNORECASE,
)


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
            if isinstance(raw, str):
                raw = raw.encode("latin-1", errors="replace")

            page_dims: list[str] = []
            for m in _PDF_LITERAL_STRING.finditer(raw):
                try:
                    s = m.group(1).decode("latin-1")
                except Exception:
                    continue
                if not _STANDALONE_DIMENSION.match(s):
                    continue
                snippet = s.strip()
                if snippet not in page_dims:
                    page_dims.append(snippet)

            if len(page_dims) < _MIN_DIMENSIONS_PER_PAGE:
                continue

            joined = " ".join(page_dims)
            if not _TECHNICAL_UNITS_RE.search(joined):
                continue

            findings.append(
                Finding(
                    inspection_id="LPDF_DIM_CALLOUT_001",
                    severity=Severity.WARNING,
                    message=(
                        f"Dimension callouts found on page {page.page_num} "
                        f"({len(page_dims)} standalone measurements: "
                        f"{', '.join(page_dims[:5])}"
                        f"{', ...' if len(page_dims) > 5 else ''}). "
                        "These technical dimensions should live on a "
                        "separate spec / dimension layer (set to "
                        "non-printing) rather than the live artwork — "
                        "they will print unless removed before plate-making."
                    ),
                    page_num=page.page_num,
                    details={
                        "standalone_dimensions": page_dims,
                        "count": len(page_dims),
                    },
                    category="geometry",
                    object_type="text",
                )
            )
        return findings
