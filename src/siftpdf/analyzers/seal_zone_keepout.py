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

from siftpdf.analyzers.base import BaseAnalyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument


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
        from siftpdf.semantic.events import TextRenderedEvent

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
        ``page``. ``TextRenderedEvent`` doesn't carry decoded string
        content, so live-text detection runs against the raw content
        stream (mirroring ``placeholder_text._flatten_tj_operands``) and
        anchors fall back to top/bottom MediaBox edge bands when the
        phrase is found but no per-event bbox is available.
        """
        anchors: list[tuple[tuple[float, float, float, float], str]] = []
        matched_labels: set[str] = set()

        # 1. OCR regions (best signal on outlined fixtures: real bbox + text).
        for region in getattr(page, "detected_text_regions", None) or []:
            text = getattr(region, "text", None) or ""
            if not text:
                continue
            for pat in _SEAL_PATTERNS:
                m = pat.search(text)
                if not m:
                    continue
                pdf_bbox = getattr(region, "bbox", None)
                if pdf_bbox is None:
                    continue
                label = m.group(0).upper()
                anchors.append(
                    (
                        (
                            float(pdf_bbox.x0),
                            float(pdf_bbox.y0),
                            float(pdf_bbox.x1),
                            float(pdf_bbox.y1),
                        ),
                        label,
                    )
                )
                matched_labels.add(label)
                break

        # 2. Raw content stream — Tj-flattened text + literal substring
        # match. No bbox per match, so we synthesise a "MediaBox top OR
        # bottom 5 mm band" anchor for each phrase found. Stick-pack and
        # pouch artwork put END SEAL / OVERLAP IN SEAL labels at the top
        # / bottom edges of the panel; the band picks up live copy that
        # crowds those edges.
        media = getattr(page, "media_box", None)
        if media is None:
            return anchors

        flat = _flatten_tj_text(getattr(page, "content_stream", None))
        for pat in _SEAL_PATTERNS:
            m = pat.search(flat)
            if not m:
                continue
            label = m.group(0).upper()
            if label in matched_labels:
                continue
            matched_labels.add(label)
            band_pt = _KEEPOUT_MM * _PT_PER_MM
            try:
                mx0, my0, mx1, my1 = (
                    float(media.x0),
                    float(media.y0),
                    float(media.x1),
                    float(media.y1),
                )
            except (AttributeError, TypeError, ValueError):
                continue
            # Top edge band:
            anchors.append(((mx0, my1 - band_pt, mx1, my1), label))
            # Bottom edge band:
            anchors.append(((mx0, my0, mx1, my0 + band_pt), label))

        return anchors


def _flatten_tj_text(stream: object) -> str:
    """Return concatenated Tj operand text from a content stream.

    Mirrors :func:`siftpdf.analyzers.placeholder_text.PlaceholderTextAnalyzer._flatten_tj_operands`
    but returns a single space-joined string. Best-effort — handles
    unescaped literal strings only; hex strings and CID encodings are
    skipped.
    """
    if not stream:
        return ""
    if isinstance(stream, (bytes, bytearray)):
        try:
            text = stream.decode("latin-1", errors="ignore")
        except Exception:
            return ""
    else:
        text = str(stream)
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "(":
            i += 1
            continue
        j = i + 1
        depth = 1
        buf: list[str] = []
        while j < n and depth > 0:
            c = text[j]
            if c == "\\" and j + 1 < n:
                buf.append(text[j + 1])
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
        while k < n and text[k] in " \t\r\n":
            k += 1
        is_tj = k + 1 < n and text[k] == "T" and text[k + 1] in ("j", "J")
        if is_tj:
            out.append("".join(buf))
        i = j
    return " ".join(out)
