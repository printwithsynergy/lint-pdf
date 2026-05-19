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
    # PR-V (audit miss closure): seal/finishing technical labels —
    # printed annotations like 'OVERLAP IN SEAL' / 'END SEAL' /
    # 'TEAR HERE' that should be on a non-printing techinfo layer
    # but are sitting in the live artwork. Caught by Opus on
    # DailyFiber_10up multi-up sheet.
    (re.compile(r"\bOVERLAP\s+IN\s+SEAL\b", re.IGNORECASE), "OVERLAP IN SEAL"),
    (re.compile(r"\bEND\s+SEAL\b", re.IGNORECASE), "END SEAL"),
    (re.compile(r"\bSEAL\s+AREA\b", re.IGNORECASE), "SEAL AREA"),
    (re.compile(r"\bDIE\s+CUT\s+AREA\b", re.IGNORECASE), "DIE CUT AREA"),
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

        # Build event-text index keyed by page_num for the codex path
        # (content_stream=b"" but TextRenderedEvent.raw_text is populated).
        event_text_by_page: dict[int, str] = {}
        for evt in events:
            from lintpdf.semantic.events import TextRenderedEvent

            if isinstance(evt, TextRenderedEvent) and evt.raw_text:
                event_text_by_page[evt.page_num] = (
                    event_text_by_page.get(evt.page_num, "") + " " + evt.raw_text
                )

        for page in document.pages:
            raw_text = self._content_stream_text(page)
            findings.extend(self._scan_text(page, raw_text, seen, "live"))
            # PR-V (audit miss closure): some live-text PDFs encode
            # strings as positioned glyphs — Identity-H CID fonts emit
            # one (X) Tj per character, so the regex ``\bLOT\s+NUMBER\b``
            # never matches the raw stream even though the glyphs ARE
            # present. Build TWO concatenations of Tj/TJ operands —
            # space-joined (catches ``(LOT) Tj (NUMBER) Tj``) and no-
            # gap joined (catches ``(L)Tj (O)Tj ... (R)Tj``) — and
            # scan both. Caught on Pink-Slush p2 and HSI_OUTLINED
            # placeholder misses.
            flattened_spaced, flattened_dense = self._flatten_tj_operands(raw_text)
            if flattened_spaced and flattened_spaced != raw_text:
                findings.extend(self._scan_text(page, flattened_spaced, seen, "live_flattened"))
            if flattened_dense and flattened_dense != raw_text:
                findings.extend(self._scan_text(page, flattened_dense, seen, "live_flattened"))
            # Codex path: content_stream=b"" but events carry raw_text
            # strings decoded from Tj/TJ operands (ASCII-safe only).
            event_text = event_text_by_page.get(page.page_num, "")
            if event_text and not raw_text:
                findings.extend(self._scan_text(page, event_text, seen, "events"))
            # PR-N (audit miss closure): outlined fixtures (Cherry-
            # Twist / Pink-Slush / HSI / OrangeKiss) have their
            # placeholder copy as vector paths. The OCR pass
            # (PR #295) recovers the strings into
            # ``page.detected_text_regions``; scan them too so the
            # placeholder check no longer goes silent on outlined PDFs.
            for region_text in self._ocr_region_strings(page):
                findings.extend(self._scan_text(page, region_text, seen, "ocr"))
        return findings

    @staticmethod
    def _content_stream_text(page: object) -> str:
        raw = getattr(page, "content_stream", None)
        if not raw:
            return ""
        try:
            return raw.decode("latin-1") if isinstance(raw, bytes) else str(raw)
        except Exception:
            return ""

    @staticmethod
    def _flatten_tj_operands(stream: str) -> tuple[str, str]:
        """Return ``(space_joined, no_gap_joined)`` reconstructions
        of every ``(...)`` literal-string operand that precedes a
        ``Tj`` or ``TJ`` operator in the content stream.

        Many CID-encoded fonts emit one Tj call per glyph (``(L) Tj
        (O) Tj (T) Tj``) so the regex search across the raw stream
        misses multi-character placeholder phrases. Two flattenings
        cover both cases:

        * ``space_joined``: separator between operands. Catches
          ``(LOT) Tj (NUMBER) Tj`` → ``"LOT NUMBER"``.
        * ``no_gap_joined``: nothing between operands. Catches
          single-glyph splits like ``(L)Tj (O)Tj ... (R)Tj`` →
          ``"LOTNUMBER"``.

        The caller scans both. Best-effort: handles unescaped
        literal strings only. Hex strings (``<HHHH>``) and non-Latin
        encodings are skipped — those carry CID glyph indices rather
        than plain ASCII so regex matching wouldn't help even after
        extraction.
        """
        if not stream:
            return "", ""
        operands: list[str] = []
        i = 0
        n = len(stream)
        while i < n:
            ch = stream[i]
            if ch != "(":
                i += 1
                continue
            j = i + 1
            depth = 1
            buf: list[str] = []
            while j < n and depth > 0:
                c = stream[j]
                if c == "\\" and j + 1 < n:
                    buf.append(stream[j + 1])
                    j += 2
                    continue
                if c == "(":
                    depth += 1
                    buf.append(c)
                elif c == ")":
                    depth -= 1
                    if depth > 0:
                        buf.append(c)
                else:
                    buf.append(c)
                j += 1
            k = j
            while k < n and stream[k] in " \t\r\n":
                k += 1
            is_tj = k + 1 < n and stream[k] == "T" and stream[k + 1] in ("j", "J")
            if is_tj:
                operands.append("".join(buf))
            i = j
        space_joined = " ".join(operands).strip()
        no_gap_joined = "".join(operands)
        return space_joined, no_gap_joined

    @staticmethod
    def _ocr_region_strings(page: object) -> list[str]:
        regions = getattr(page, "detected_text_regions", None) or []
        return [getattr(r, "text", None) or "" for r in regions]

    @staticmethod
    def _scan_text(
        page: object,
        text: str,
        seen: set[tuple[int, str]],
        source: str,
    ) -> list[Finding]:
        if not text:
            return []
        page_num = getattr(page, "page_num", 0)
        out: list[Finding] = []
        for pat, label in _PATTERNS:
            m = pat.search(text)
            if not m:
                continue
            start, end = m.span()
            window = text[max(0, start - 30) : end + 30]
            if any(legit.search(window) for legit in _LEGITIMATE_PHRASES):
                continue
            key = (page_num, label)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                Finding(
                    inspection_id="LPDF_PLACEHOLDER_001",
                    severity=Severity.WARNING,
                    message=(
                        f"Placeholder text '{label}' on page {page_num} — "
                        "variable-data token left in artwork. Either replace "
                        "with the live data or mark the area as a non-printing "
                        "imprint zone before plate-making."
                    ),
                    page_num=page_num,
                    details={"placeholder": label, "source": source},
                    category="text",
                    object_type="text",
                )
            )
        return out
