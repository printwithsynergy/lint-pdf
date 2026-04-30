"""DielinePerfIndicatorAnalyzer — flags artwork text that names a
finishing operation (tear / perforation / score / kiss-cut) when no
matching ISO 19593-1 ProcessingStep spot exists.

Audit closure (PR-J): the post-merge Opus 4.7 audit surfaced 4
fixtures (Cherry-Twist, OrangeKiss, Pink-Slush, HSI_ADM) where the
artwork itself includes a "TEAR ACROSS / DECHIRER ICI" indicator or
similar perforation/score callout, but the document only has a
single /Dieline (or no dieline) spot. Without a dedicated
Perforating / KissCut / Scoring spot the converter can't route the
operation to the correct finishing tool — the dashed indicator may
print on the live plates.

Detection sources (in order):
1. ``page.detected_text_regions`` — populated by the OCR pass on
   outlined / image-heavy pages. Outlined fixtures live and die here.
2. ``page.annotations`` — annotation /Contents text.
3. The page-level content stream raw bytes — last-resort substring
   search for the literal phrase patterns. Catches live-text PDFs
   where the parser didn't surface text events with strings.

Check ID:
    LPDF_DIE_PERF_INDICATOR_NO_STEP — Tear / perf / score indicator
        present in artwork without a matching ISO 19593 ProcessingStep
        spot. Severity: ADVISORY.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


# Phrase fragments that strongly imply a tear / perf / score finishing
# operation. Compared against lower-cased text. Includes English,
# French, and German variants common on packaging in North America +
# EU markets.
_PERF_PHRASES: tuple[str, ...] = (
    "tear across",
    "tear here",
    "tear notch",
    "tear-off",
    "tear off",
    "déchirer",
    "dechirer",  # diacritic-stripped fallback
    "perforation",
    "perf line",
    "score line",
    "kiss cut",
    "kiss-cut",
    "abreissen",
    "abreiß",
)

# ISO 19593-1 ProcessingStep names that satisfy the "matching spot
# exists" requirement. Any of these in the spot inventory clears the
# advisory — the document already names a non-printing finishing op.
_PROCESSING_STEP_NAMES: frozenset[str] = frozenset(
    {
        "perforating",
        "perforation",
        "perf",
        "perf_line",
        "perfline",
        "kisscut",
        "kiss_cut",
        "kiss-cut",
        "scoring",
        "score",
        "creasing",
        "crease",
        "tearline",
        "tear_line",
        "tear-line",
    }
)


def _normalise_spot(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.strip().strip("/").lower().replace("-", "_").replace(" ", "_")


def _matches_perf_phrase(text: str) -> str | None:
    """Return the first matching perf phrase, or None."""
    if not text:
        return None
    haystack = text.lower()
    for phrase in _PERF_PHRASES:
        if phrase in haystack:
            return phrase
    return None


class DielinePerfIndicatorAnalyzer(BaseAnalyzer):
    """Detect tear / perf / score indicator text without a matching
    ISO 19593-1 ProcessingStep spot."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        # Inventory of ProcessingStep-class spots. If any are present
        # we never fire — the converter has the decomposition info.
        for page in document.pages:
            for cs in (page.color_spaces or {}).values():
                if getattr(cs, "cs_type", None) not in ("Separation", "DeviceN", "NChannel"):
                    continue
                for colorant in getattr(cs, "colorant_names", None) or ():
                    norm = _normalise_spot(colorant)
                    if norm and norm in _PROCESSING_STEP_NAMES:
                        return []

        findings: list[Finding] = []
        for page in document.pages:
            match = self._find_match_on_page(page)
            if match is None:
                continue
            phrase, source = match
            findings.append(
                Finding(
                    inspection_id="LPDF_DIE_PERF_INDICATOR_NO_STEP",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Page {page.page_num}: artwork contains a "
                        f"'{phrase}' indicator but no ISO 19593-1 "
                        "ProcessingStep spot (Perforating / KissCut / "
                        "Scoring / Creasing) was declared. Without a "
                        "dedicated finishing spot the converter cannot "
                        "route the operation to the perf/score tool; "
                        "the indicator art may also print on the live "
                        "plates."
                    ),
                    page_num=page.page_num,
                    details={
                        "matched_phrase": phrase,
                        "source": source,
                    },
                    category="dieline",
                    object_type="page",
                    iso_clause="ISO 19593-1:2018 Annex A.4",
                )
            )
        return findings

    @staticmethod
    def _find_match_on_page(page: object) -> tuple[str, str] | None:
        # 1. OCR text regions (best signal on outlined fixtures).
        for region in getattr(page, "detected_text_regions", None) or []:
            phrase = _matches_perf_phrase(getattr(region, "text", "") or "")
            if phrase:
                return (phrase, "ocr_text_region")

        # 2. PDF annotations (/Contents).
        for ann in getattr(page, "annotations", None) or []:
            phrase = _matches_perf_phrase(getattr(ann, "contents", "") or "")
            if phrase:
                return (phrase, "annotation")

        # 3. Raw content stream substring scan — catches live-text
        # cases where the parser did not surface annotation contents
        # but the literal phrase appears in a Tj string.
        content = getattr(page, "content_stream", None) or b""
        if isinstance(content, (bytes, bytearray)):
            try:
                text = content.decode("latin-1", errors="ignore")
            except Exception:
                text = ""
        else:
            text = str(content)
        # Only inspect if the page has fonts (live text) — outlined
        # pages are handled by OCR above.
        if getattr(page, "fonts", None):
            phrase = _matches_perf_phrase(_strip_pdf_tj(text))
            if phrase:
                return (phrase, "content_stream")

        return None


_TJ_STRING_RE = re.compile(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", re.DOTALL)


def _strip_pdf_tj(latin: str) -> str:
    """Concatenate Tj string operands from a content-stream-as-string.

    Best-effort — handles unescaped single-line strings only. Skips
    PDF escape sequences and split TJ arrays, which is fine because
    the perf phrases are short and usually appear as single Tj calls.
    """
    out: list[str] = []
    for match in _TJ_STRING_RE.finditer(latin.encode("latin-1", errors="ignore")):
        try:
            out.append(match.group(1).decode("latin-1", errors="ignore"))
        except Exception:
            continue
    return " ".join(out)
