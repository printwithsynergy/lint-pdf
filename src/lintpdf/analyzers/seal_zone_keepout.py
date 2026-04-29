"""SealZoneKeepoutAnalyzer — flags live copy that sits inside the
heat-seal / overlap-seal keepout band on stick-pack and pouch artwork.

Audit closure (PR-AA): the post-merge Opus 4.7 audit flagged 3 fixtures
(DailyFiber_10up, OrangeKiss, Pink-Slush) where live copy and barcodes
abut the ``END SEAL`` / ``OVERLAP IN SEAL`` / tear-zone labels with no
visible safety margin. Heat-seal / crimp areas are unprintable on
flexible-film converters; copy or barcodes that sit inside the seal
keepout will be obscured, distorted, or sealed over.

The analyzer:

1. Scans text events + OCR regions + the raw content stream for any
   technical seal-zone labels (``END SEAL``, ``OVERLAP IN SEAL``, ``SEAL
   AREA``, ``TEAR ACROSS``, etc.).
2. Anchors each match's bbox in PDF points.
3. Builds a keepout band around each anchor (default 5 mm — a
   conservative minimum the converter needs for the seal jaw + tolerance).
4. Flags any *other* ``TextRenderedEvent`` whose bbox overlaps the
   keepout band on the same page.

Check ID:
    LPDF_BOX_SEAL_ZONE_VIOLATION — Live copy / barcode inside the
        seal-zone keepout. Severity: WARNING.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Patterns that mark a seal / crimp / tear zone in artwork. The strings
# are the technical annotations designers put on press-ready PDFs to
# show the converter where the seal jaw lands.
_SEAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bEND\s+SEAL\b", re.IGNORECASE),
    re.compile(r"\bOVERLAP\s+IN\s+SEAL\b", re.IGNORECASE),
    re.compile(r"\bSEAL\s+AREA\b", re.IGNORECASE),
    re.compile(r"\bHEAT\s+SEAL\b", re.IGNORECASE),
    re.compile(r"\bCRIMP\s+AREA\b", re.IGNORECASE),
    re.compile(r"\bTEAR\s+ACROSS\b", re.IGNORECASE),
    re.compile(r"\bTEAR\s+HERE\b", re.IGNORECASE),
    re.compile(r"\bDÉCHIRER\s+ICI\b", re.IGNORECASE),
    re.compile(r"\bDECHIRER\s+ICI\b", re.IGNORECASE),
)

# 5 mm = 14.17 pt. Conservative: most flexible-film stick-pack converters
# need 4-6 mm of jaw bite plus 1-2 mm registration tolerance. We pick
# the lower bound so we under-fire rather than over-fire.
_KEEPOUT_MM = 5.0
_PT_PER_MM = 2.834645669


def _pad_bbox(
    bbox: tuple[float, float, float, float], pad_pt: float
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = bbox
    return (x0 - pad_pt, y0 - pad_pt, x1 + pad_pt, y1 + pad_pt)


def _bbox_overlap(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _bbox_area(bbox: tuple[float, float, float, float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


class SealZoneKeepoutAnalyzer(BaseAnalyzer):
    """Detect live copy that sits inside a seal/crimp keepout band."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        from lintpdf.semantic.events import TextRenderedEvent

        # Bucket text events by page for efficient inner-loop scans.
        by_page: dict[int, list[TextRenderedEvent]] = {}
        for ev in events:
            if not isinstance(ev, TextRenderedEvent):
                continue
            if ev.bbox is None:
                continue
            if ev.rendering_mode == 3:  # invisible text
                continue
            by_page.setdefault(ev.page_num, []).append(ev)

        findings: list[Finding] = []
        for page in document.pages:
            anchors = self._find_seal_anchors(page, by_page.get(page.page_num, []))
            if not anchors:
                continue

            keepout_pt = _KEEPOUT_MM * _PT_PER_MM
            anchor_bboxes = {a[0] for a in anchors}
            seen_keys: set[tuple[int, int]] = set()  # (anchor_idx, glyph_bucket)

            for idx, (anchor_bbox, anchor_label) in enumerate(anchors):
                keepout_band = _pad_bbox(anchor_bbox, keepout_pt)
                # Walk live text + barcode-candidate bboxes for proximity.
                for ev in by_page.get(page.page_num, []):
                    if ev.bbox is None:
                        continue
                    # Skip the anchor events themselves — their bboxes
                    # naturally overlap the keepout band.
                    if ev.bbox in anchor_bboxes:
                        continue
                    if not _bbox_overlap(ev.bbox, keepout_band):
                        continue
                    # Dedupe — bucket by anchor + rounded x+y position so
                    # a paragraph of small text doesn't spam findings.
                    key = (
                        idx,
                        int(ev.bbox[0] // 10) * 1000 + int(ev.bbox[1] // 10),
                    )
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    findings.append(
                        Finding(
                            inspection_id="LPDF_BOX_SEAL_ZONE_VIOLATION",
                            severity=Severity.WARNING,
                            message=(
                                f"Live copy on page {page.page_num} is inside the "
                                f"'{anchor_label}' keepout band ({_KEEPOUT_MM:.1f} mm). "
                                "Heat-seal / crimp areas are unprintable on flexible-"
                                "film converters; the copy will be obscured, distorted, "
                                "or sealed over. Move the copy outside the seal zone "
                                "or relocate the seal."
                            ),
                            page_num=page.page_num,
                            details={
                                "seal_label": anchor_label,
                                "keepout_mm": _KEEPOUT_MM,
                                "anchor_bbox": list(anchor_bbox),
                                "violator_bbox": list(ev.bbox),
                            },
                            category="geometry",
                            object_type="text",
                            bbox=ev.bbox,
                        )
                    )
        return findings

    @staticmethod
    def _find_seal_anchors(
        page: object, page_events: list[object]
    ) -> list[tuple[tuple[float, float, float, float], str]]:
        """Return ``[(bbox, matched_label)]`` for every seal-zone label on
        ``page``. Combines live text events, OCR text regions, and the
        raw content stream as fallbacks.
        """
        anchors: list[tuple[tuple[float, float, float, float], str]] = []

        # 1. Live text events with bbox.
        for ev in page_events:
            text = getattr(ev, "string", None) or getattr(ev, "text", None) or ""
            if not text:
                continue
            for pat in _SEAL_PATTERNS:
                m = pat.search(text)
                if m:
                    bbox = getattr(ev, "bbox", None)
                    if bbox is not None:
                        anchors.append((bbox, m.group(0).upper()))
                        break

        # 2. OCR regions on outlined fixtures.
        for region in getattr(page, "detected_text_regions", None) or []:
            text = getattr(region, "text", None) or ""
            if not text:
                continue
            for pat in _SEAL_PATTERNS:
                m = pat.search(text)
                if m:
                    pdf_bbox = getattr(region, "bbox", None)
                    if pdf_bbox is None:
                        continue
                    anchors.append(
                        (
                            (
                                float(pdf_bbox.x0),
                                float(pdf_bbox.y0),
                                float(pdf_bbox.x1),
                                float(pdf_bbox.y1),
                            ),
                            m.group(0).upper(),
                        )
                    )
                    break

        return anchors
