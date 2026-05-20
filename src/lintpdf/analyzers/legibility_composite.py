"""LegibilityCompositeAnalyzer — small-and-rotated text legibility risk.

The 2026-04-27 Opus audit flagged 16 misses across 7 fixtures with the
shape *"ingredient/usage legal copy is set at very small point size and
rotated 90 deg on a flexible-film stick-pack panel"*. Examples:

* AN-Energy_StickPack: ingredient blocks ~4.9-5.4 pt rotated 90 deg
* Cherry-Twist: ingredient panel rotated 90 deg at ~5 pt
* OrangeKiss: bilingual ingredients rotated 90 deg hard against trim edge

The shape is real and consistent: small font + non-axis-aligned rotation
+ packaging substrate = a press-side legibility risk, even when the
finding is below the EU FIR 1169 / FDA OTC threshold lines that already
have dedicated rules.

Check ID:
    LPDF_LEGIBILITY_001 — Composite legibility risk (small + rotated
        text). Severity: ADVISORY. Conservative threshold + per-page
        dedupe to keep false-positive volume low.

Calibration:
* Font-size threshold: ``< 6.0 pt`` (composed). Below this, even
  axis-aligned text is at the edge of practical legibility on most
  presses; rotation amplifies that risk because head registration
  drift is highest perpendicular to web direction.
* Rotation threshold: ``|sin(angle)| > 0.7`` — i.e. rotated more
  than ≈45 deg off the horizontal. Catches 90 deg / 270 deg rotation
  (the dominant case) without firing on trivially-skewed text.
* Per-page dedupe: at most one finding per (page, font_name,
  rounded font_size, rotation bucket) tuple.
* Existing ``AI_PHARMA_001`` / ``AI_EU1169_001`` rules cover the
  un-rotated jurisdiction-specific cases; this rule complements
  them with substrate-agnostic, jurisdiction-agnostic coverage.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Composed font-size threshold for the legibility risk. Below this we
# flag rotated text. 6 pt = standard FDA OTC body minimum; below it
# even un-rotated text needs scrutiny.
_MIN_LEGIBLE_PT = 6.0

# Rotation magnitude threshold, expressed as |sin(angle)|. 0.7 ≈ 45 deg.
# At or above this, text is closer to vertical than horizontal.
_ROTATION_THRESHOLD = 0.7


def _composed_font_size_pt(event) -> float:  # type: ignore[no-untyped-def]
    """Effective on-page font size after ctm x text-matrix scale.

    PDF font size is the design-space height. On-page size is the
    composed Y-axis scale of (ctm * text_matrix). We extract that
    via the *length of the Y-axis basis vector* -- ``hypot(b, d)``
    of the composed top-left 2x2 -- rather than ``|d|`` alone, so the
    calculation stays correct at 90 / 270 degree rotation (where
    ``d=0`` but the on-page size is still the magnitude of the
    rotated basis).
    """
    base = abs(event.font_size)
    if not event.ctm or not event.text_matrix:
        return base
    ctm = event.ctm
    tm = event.text_matrix
    # Composed top-left 2x2:
    #   [ ctm.a*tm.a + ctm.c*tm.b   ctm.a*tm.c + ctm.c*tm.d ]
    #   [ ctm.b*tm.a + ctm.d*tm.b   ctm.b*tm.c + ctm.d*tm.d ]
    # Y-axis basis vector after composition is column 2: (cx, cy)
    cx = ctm.a * tm.c + ctm.c * tm.d
    cy = ctm.b * tm.c + ctm.d * tm.d
    return base * math.hypot(cx, cy)


def _rotation_magnitude(event) -> float:  # type: ignore[no-untyped-def]
    """Return ``|sin(rotation_angle)|`` of the text's effective
    orientation: 0 for axis-aligned, 1 for ±90 deg.

    Combines ``ctm`` and ``text_matrix`` (text orientation = ctm * Tm
    in the standard PDF text-rendering pipeline). We extract the
    rotation from the composed top-left 2x2 block.

    ``b`` and ``a`` are read off the composed matrix; the rotation
    angle is ``atan2(b, a)`` (this also works when scale is non-uniform --
    we only care about the orientation, not magnitude).
    """
    if not event.ctm or not event.text_matrix:
        return 0.0
    # Compose ctm * text_matrix manually for the 2x2 block. We only
    # need a, b of the result.
    ctm = event.ctm
    tm = event.text_matrix
    # Composed top-left 2x2 = [[ctm.a*tm.a + ctm.c*tm.b, ctm.a*tm.c + ctm.c*tm.d],
    #                          [ctm.b*tm.a + ctm.d*tm.b, ctm.b*tm.c + ctm.d*tm.d]]
    # rotation = atan2(b, a) where (a, b) is the first column of the composed matrix.
    a = ctm.a * tm.a + ctm.c * tm.b
    b = ctm.b * tm.a + ctm.d * tm.b
    norm = math.hypot(a, b)
    if norm < 1e-9:
        return 0.0
    # |sin(angle)| = |b| / hypot(a, b)
    return abs(b) / norm


class LegibilityCompositeAnalyzer(BaseAnalyzer):
    """Flag small text rotated >45 deg off horizontal as a legibility risk.

    Complements jurisdiction-specific rules (``AI_PHARMA_001``,
    ``AI_EU1169_001``) which gate on regulatory market — this rule
    fires regardless of jurisdiction whenever the geometry signals
    a press-side legibility concern.
    """

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        from lintpdf.semantic.events import TextRenderedEvent

        findings: list[Finding] = []
        # Dedupe key: (page, font_name, rounded font size, rotation bucket).
        seen: set[tuple[int, str, float, int]] = set()

        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue
            # Invisible text — rendering mode 3 is "neither stroke nor
            # fill"; the text doesn't render and so doesn't carry a
            # legibility risk.
            if event.rendering_mode == 3:
                continue

            font_size_pt = _composed_font_size_pt(event)
            if font_size_pt <= 0:
                continue
            # Skip degenerate sub-2pt sizes — same calibration as
            # AI_WCAG_001 (PR #278). These are stray glyphs from
            # outlined paths or transform artefacts.
            if font_size_pt < 2.0:
                continue
            if font_size_pt >= _MIN_LEGIBLE_PT:
                continue

            rotation_mag = _rotation_magnitude(event)
            if rotation_mag < _ROTATION_THRESHOLD:
                continue

            # Quantize for dedupe so a paragraph of small rotated text
            # doesn't emit dozens of findings.
            size_bucket = round(font_size_pt, 1)
            rot_bucket = 1 if rotation_mag > 0.95 else 0  # 90 deg-ish vs ~45 deg
            key = (event.page_num, event.font_name, size_bucket, rot_bucket)
            if key in seen:
                continue
            seen.add(key)

            angle_deg = math.degrees(math.asin(min(1.0, rotation_mag)))

            findings.append(
                Finding(
                    inspection_id="LPDF_LEGIBILITY_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Small rotated text at {font_size_pt:.1f} pt "
                        f"(font {event.font_name}) rotated ≈{angle_deg:.0f} deg "
                        f"on page {event.page_num} — combination of sub-{_MIN_LEGIBLE_PT:.0f} pt "
                        "size and off-axis orientation is a press-side "
                        "legibility risk, especially on flexible-film "
                        "substrates where head-registration drift is "
                        "highest perpendicular to web direction."
                    ),
                    page_num=event.page_num,
                    details={
                        "font_size_pt": round(font_size_pt, 2),
                        "font_name": event.font_name,
                        "rotation_deg_approx": round(angle_deg, 1),
                        "min_legible_pt": _MIN_LEGIBLE_PT,
                    },
                    category="text",
                    object_type="text",
                    bbox=event.bbox,
                )
            )

        # PR C Slot 3B: complementary pass for OUTLINED text. The
        # event-based loop above only sees live ``TextRenderedEvent``s;
        # on stick-pack / pouch fixtures the ingredient panel is
        # frequently converted to vector paths and never emits text
        # events. The shared OCR pass (PR #295) populates
        # ``page.detected_text_regions`` with PDF-point bboxes from
        # PaddleOCR — measured glyph height comes straight from the
        # bbox dimension. Apparent height < 6 pt is the same legibility
        # signal we'd raise on live small copy; emit a distinct
        # ``LPDF_TEXT_OUTLINED_SMALL`` so reviewers can tell the two
        # paths apart.
        findings.extend(self._scan_outlined_small_text(document))
        return findings

    @staticmethod
    def _scan_outlined_small_text(document: SemanticDocument) -> list[Finding]:
        """Walk ``page.detected_text_regions`` and emit one ADVISORY per
        offending outlined-text region with its bbox so Lens can circle
        each instance on the canvas. Capped at 5 per page to keep the
        findings panel manageable on dense ingredient panels."""
        _MAX_PER_PAGE = 5
        out: list[Finding] = []
        for page in getattr(document, "pages", None) or []:
            regions = getattr(page, "detected_text_regions", None)
            if not regions:
                continue
            emitted = 0
            for region in regions:
                if emitted >= _MAX_PER_PAGE:
                    break
                bbox_obj = getattr(region, "bbox", None)
                if bbox_obj is None:
                    continue
                try:
                    x0 = float(bbox_obj.x0)
                    y0 = float(bbox_obj.y0)
                    x1 = float(bbox_obj.x1)
                    y1 = float(bbox_obj.y1)
                    h = y1 - y0
                except (AttributeError, TypeError, ValueError):
                    continue
                # Sub-pixel regions are scanner noise.
                if h < 1.0:
                    continue
                if h >= _MIN_LEGIBLE_PT:
                    continue
                text_preview = (getattr(region, "text", None) or "")[:60]
                out.append(
                    Finding(
                        inspection_id="LPDF_TEXT_OUTLINED_SMALL",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Outlined text ≈{h:.1f} pt on page {page.page_num} "
                            f"is below the {_MIN_LEGIBLE_PT:.0f} pt legibility threshold"
                            + (f' — "{text_preview}"' if text_preview else "")
                            + ". Verify against FDA/CFIA minimums (≈ 1.5 mm x-height)."
                        ),
                        page_num=page.page_num,
                        details={
                            "apparent_height_pt": round(h, 2),
                            "min_legible_pt": _MIN_LEGIBLE_PT,
                            "text_preview": text_preview,
                            "source": "ocr",
                        },
                        category="text",
                        object_type="text",
                        bbox=(x0, y0, x1, y1),
                    )
                )
                emitted += 1
        return out
