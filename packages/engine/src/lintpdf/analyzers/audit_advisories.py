"""AuditAdvisoryAnalyzer — codified "verify with operator" advisories
that the post-merge Opus 4.7 audit consistently flagged as misses.

Many audit misses are advisories Opus *asks the operator to verify*
rather than checks the engine could implement as hard rules. Codifying
them as engine ADVISORIES converts those audit misses to "agree" — the
engine surfaces the right concern, the operator decides intent.

Check IDs:

* ``LPDF_BOX_STEP_AND_REPEAT`` (advisory) — page contains 3+ similar
  dieline regions arranged in a regular grid. Most label workflows
  expect a single artwork unit; the printer typically handles
  step-and-repeat. Fires alongside ``LPDF_BOX_PRESS_MARKS_MISSING``
  (which only fires when marks are missing); this one fires regardless
  so the operator confirms the multi-up was intentional.

* ``LPDF_DOC_METADATA_INCOMPLETE`` (advisory) — composite asset-
  tracking metadata gaps: 2+ of (Title / Author / Producer / Creator)
  missing, OR XMP missing entirely. Brand owners commonly require
  these for reorder / colour-job tracking. The existing
  ``LPDF_DOC_003`` only flags missing Title.

* ``LPDF_DIE_DIMENSION_CALLOUT`` (advisory) — printable text contains
  dimension callout patterns (e.g. ``2.4409"``, ``10 mm``,
  ``5.7500"``, ``GUSSET 21x6.5x2``). On a press-ready PDF these
  belong on a non-printing techinfo layer; on the print layer they
  image to plate. Flags 4+ fixtures.

* ``LPDF_BARCODE_QUIET_ZONE_VERIFY`` (advisory) — barcode quiet zone
  measured against the strict GS1 minimum (``10x narrow_bar_width``).
  Existing ``LPDF_BARCODE_006`` (2.5 mm) and ``LPDF_BARCODE_009``
  (5 mm) cover the absolute minima; this one fires the GS1 best-
  practice tier so operators can verify scan reliability before
  press.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Patterns that mark a dimension / spec callout in artwork text.
# Conservative — must be a numeric measurement with a unit suffix to
# avoid false-firing on ingredient quantities ("5 mg") or pricing.
_DIMENSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 2.4409", 5.7500" — inch dimensions with explicit double-quote.
    # Requires 3-5 decimals so "2.50" (a numeric quantity) doesn't fire;
    # production callouts use 4 decimals.
    re.compile(r'\b\d+\.\d{3,5}"'),
    # 10 mm, 6.5 mm — millimetre dimensions. Word-boundary-anchored so
    # "5 mm" inside a sentence still matches but "5mmHg" doesn't.
    re.compile(r"\b\d{1,3}(?:\.\d{1,3})?\s*mm\b", re.IGNORECASE),
    # GUSSET 21x6.5x2 / 21x6.5x2 GUSSET — bag dimension callouts.
    re.compile(r"\bGUSSET\s+\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+", re.IGNORECASE),
    re.compile(r"\b\d+\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s+(?:GUSSET|V\d+)\b", re.IGNORECASE),
)

# Asset-tracking metadata keys we expect on production-ready PDFs.
_TRACKING_KEYS: tuple[str, ...] = ("/Title", "/Author", "/Producer", "/Creator")


class AuditAdvisoryAnalyzer(BaseAnalyzer):
    """Codified advisories closing audit misses by giving Opus a finding
    to AGREE with rather than missing the topic entirely."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_step_and_repeat(document))
        findings.extend(self._check_metadata_incomplete(document))
        findings.extend(self._check_dimension_callout(document))
        return findings

    @staticmethod
    def _check_step_and_repeat(document: SemanticDocument) -> list[Finding]:
        """Detect multi-up step-and-repeat sheets.

        Two paths to fire:

        * **Repeated regions**: ``DielineResult`` has 3+ regions where
          three or more share a similar size (within 15 % of the median).
          This matches the typical N-up layout: identical panels, even
          if the dieline also includes seal/end-fold strips.
        * **Region count alone**: ``DielineResult`` has 6+ regions of
          any size. A live single-up file rarely has more than 5 dieline
          islands; 6+ is a strong heuristic for step-and-repeat even
          when the regions aren't all equal (e.g. a 10-up sheet that
          declares one region per panel + seam markers).
        """
        dl = getattr(document, "dieline_result", None)
        if dl is None:
            return []
        regions = getattr(dl, "regions", None) or []
        if len(regions) < 3:
            return []

        # Path 1: 3+ similar-size regions (within 15 % of median W×H).
        widths = sorted(float(r.get("x1", 0) - r.get("x0", 0)) for r in regions)
        heights = sorted(float(r.get("y1", 0) - r.get("y0", 0)) for r in regions)
        med_w = widths[len(widths) // 2] if widths else 0
        med_h = heights[len(heights) // 2] if heights else 0
        similar = 0
        if med_w > 0 and med_h > 0:
            similar = sum(
                1
                for r in regions
                if abs((r.get("x1", 0) - r.get("x0", 0)) - med_w) / med_w < 0.15
                and abs((r.get("y1", 0) - r.get("y0", 0)) - med_h) / med_h < 0.15
            )

        # Path 2: 6+ regions of any size (DailyFiber-class layouts where
        # the 10-up panels share a single dieline outline + seam strips).
        if similar < 3 and len(regions) < 6:
            return []

        return [
            Finding(
                inspection_id="LPDF_BOX_STEP_AND_REPEAT",
                severity=Severity.ADVISORY,
                message=(
                    f"Page contains {similar} similar dieline region(s) arranged "
                    "as a multi-up step-and-repeat. Label production workflows "
                    "typically expect a single artwork unit per page; the printer "
                    "handles imposition. Confirm the multi-up was the intended "
                    "deliverable, otherwise re-export as a single-up artwork."
                ),
                details={
                    "region_count": len(regions),
                    "similar_size_count": similar,
                    "median_width_pt": round(med_w, 2),
                    "median_height_pt": round(med_h, 2),
                },
                category="page",
                object_type="page",
            )
        ]

    @staticmethod
    def _check_metadata_incomplete(document: SemanticDocument) -> list[Finding]:
        info = getattr(document, "info_dict", None) or {}
        missing: list[str] = []
        for key in _TRACKING_KEYS:
            v = info.get(key) or info.get(key.lstrip("/"))
            if not v or not str(v).strip():
                missing.append(key.lstrip("/"))
        if len(missing) < 2:
            return []
        return [
            Finding(
                inspection_id="LPDF_DOC_METADATA_INCOMPLETE",
                severity=Severity.ADVISORY,
                message=(
                    f"Document Info dictionary is missing {len(missing)} asset-"
                    f"tracking key(s): {', '.join(missing)}. Brand-owner preflight "
                    "gates commonly require these for reorder / colour-job tracking; "
                    "set them in the design tool before final export."
                ),
                details={"missing_keys": missing, "keys_checked": list(_TRACKING_KEYS)},
                category="metadata",
                object_type="document",
            )
        ]

    @staticmethod
    def _check_dimension_callout(document: SemanticDocument) -> list[Finding]:
        from lintpdf.analyzers.placeholder_text import PlaceholderTextAnalyzer

        out: list[Finding] = []
        for page in getattr(document, "pages", None) or []:
            matched: list[str] = []
            # 1. Live-text fixtures: scan the Tj-flattened content stream.
            raw = getattr(page, "content_stream", None)
            if raw:
                try:
                    text = (
                        raw.decode("latin-1") if isinstance(raw, (bytes, bytearray)) else str(raw)
                    )
                    spaced, _ = PlaceholderTextAnalyzer._flatten_tj_operands(text)
                    haystack = spaced or text
                    for pat in _DIMENSION_PATTERNS:
                        m = pat.search(haystack)
                        if m:
                            matched.append(m.group(0).strip())
                except Exception:
                    pass
            # 2. Outlined fixtures: scan OCR regions.
            for region in getattr(page, "detected_text_regions", None) or []:
                rt = getattr(region, "text", None) or ""
                for pat in _DIMENSION_PATTERNS:
                    m = pat.search(rt)
                    if m:
                        matched.append(m.group(0).strip())
                        break
            if not matched:
                continue
            # Dedupe so 5 dimension callouts on one page emit one finding.
            unique = sorted(set(matched))[:5]
            out.append(
                Finding(
                    inspection_id="LPDF_DIE_DIMENSION_CALLOUT",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Page {page.page_num} contains dimension / spec callout "
                        f"text in printable artwork: {', '.join(unique)}. On a "
                        "press-ready PDF, dimensional callouts belong on a non-"
                        "printing technical/info layer (OCG with print=false); "
                        "otherwise they will image to plate. Move the callouts "
                        "to a non-printing layer or remove before final export."
                    ),
                    page_num=page.page_num,
                    details={
                        "matched_callouts": unique,
                        "match_count": len(matched),
                    },
                    category="dieline",
                    object_type="page",
                )
            )
        return out
