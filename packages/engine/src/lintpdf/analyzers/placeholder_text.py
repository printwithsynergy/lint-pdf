"""PlaceholderTextAnalyzer — flags variable-data tokens left in artwork.

The 2026-04-27 Opus audit flagged this as the dominant text-category
miss (≥10 missed findings across 5+ fixtures). Tokens like
``LOT NUMBER``, ``DATE CODE``, ``FRONT PANEL``, ``Template #...``
typically live in variable-data zones that get over-printed at
production. Designers leaving them in the artwork at plate-making time
ship a label with the literal placeholder text printed.

Check ID:
    LPDF_PLACEHOLDER_001 — Placeholder / variable-data token left
        in artwork. Severity: WARNING.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Pattern → human-readable label. Patterns are deliberately conservative
# (must be standalone tokens, not part of another word) to avoid false
# positives on legitimate copy that happens to contain the keyword.
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bLOT\s+NUMBER\b", re.IGNORECASE), "LOT NUMBER"),
    (re.compile(r"\bDATE\s+CODE\b", re.IGNORECASE), "DATE CODE"),
    (re.compile(r"\bEXP(?:IRY)?\s+DATE\b", re.IGNORECASE), "EXPIRY DATE"),
    (re.compile(r"\bMANUFACTURED\s+ON\b", re.IGNORECASE), "MANUFACTURED ON"),
    (re.compile(r"\bUSE\s+BY\b", re.IGNORECASE), "USE BY"),
    (re.compile(r"\bBEST\s+BEFORE\b", re.IGNORECASE), "BEST BEFORE"),
    (re.compile(r"\bFRONT\s+PANEL\b", re.IGNORECASE), "FRONT PANEL"),
    (re.compile(r"\bBACK\s+PANEL\b", re.IGNORECASE), "BACK PANEL"),
    (re.compile(r"\bTOP\s+PANEL\b", re.IGNORECASE), "TOP PANEL"),
    (re.compile(r"\bBOTTOM\s+PANEL\b", re.IGNORECASE), "BOTTOM PANEL"),
    (re.compile(r"\bSIDE\s+PANEL\b", re.IGNORECASE), "SIDE PANEL"),
    (re.compile(r"\bTemplate\s*#\s*\d+\b", re.IGNORECASE), "Template #..."),
    (re.compile(r"\bINSERT\s+IN\s+(?:END\s+SEAL|HERE)\b", re.IGNORECASE), "INSERT IN ..."),
    (
        re.compile(r"\bENHANCED\s+TO\s+SHOW\s+DETAIL\b", re.IGNORECASE),
        "ENHANCED TO SHOW DETAIL",
    ),
    (
        re.compile(r"\bACTUAL\s+SIZE\s+MAY\s+VARY\b", re.IGNORECASE),
        "ACTUAL SIZE MAY VARY",
    ),
    # Bracketed all-caps placeholders like [BRAND NAME], [STORE NAME]
    (re.compile(r"\[[A-Z][A-Z\s_\-/]{2,30}\]"), "[BRACKETED PLACEHOLDER]"),
)

# Tokens that look like placeholders but are legitimate marketing /
# regulatory copy on real-world packaging — explicitly NOT flagged so
# we don't pile false positives back onto the analyzer we just removed
# 75 of.
_LEGITIMATE_PHRASES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bBest\s+Before\s*:\s*\d", re.IGNORECASE),  # already filled in
    re.compile(r"\bUse\s+by\s*:\s*\d", re.IGNORECASE),
    re.compile(r"\bLot\s+#\s*[A-Z0-9]", re.IGNORECASE),
)


class PlaceholderTextAnalyzer(BaseAnalyzer):
    """Detect placeholder / variable-data tokens left in artwork."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        # Dedupe: at most one finding per (page, label) so an
        # imposed sheet doesn't emit 10 copies of the same token.
        seen: set[tuple[int, str]] = set()

        for page in document.pages:
            raw = page.content_stream
            if not raw:
                continue
            try:
                text = raw.decode("latin-1") if isinstance(raw, bytes) else str(raw)
            except Exception:
                continue

            # Skip when the page text is dominated by a clearly
            # legitimate phrase that would otherwise trip our
            # placeholder-detection. We don't blanket-skip the whole
            # page — just narrow windows around the legit phrases.
            for pat, label in _PATTERNS:
                m = pat.search(text)
                if not m:
                    continue
                start, end = m.span()
                # Suppress if a legitimate phrase appears within 30
                # chars on either side (filled-in dates etc.).
                window = text[max(0, start - 30) : end + 30]
                if any(legit.search(window) for legit in _LEGITIMATE_PHRASES):
                    continue
                key = (page.page_num, label)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    Finding(
                        inspection_id="LPDF_PLACEHOLDER_001",
                        severity=Severity.WARNING,
                        message=(
                            f"Placeholder text '{label}' on page {page.page_num} — "
                            "variable-data token left in artwork. Either replace "
                            "with the live data or mark the area as a non-printing "
                            "imprint zone before plate-making."
                        ),
                        page_num=page.page_num,
                        details={"placeholder": label},
                        category="text",
                        object_type="text",
                    )
                )
        return findings
