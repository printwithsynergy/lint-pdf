"""LegalCopyMinSizeAnalyzer — small printed copy below regulatory minima.

PR-X (audit miss closure): the existing :class:`LegibilityCompositeAnalyzer`
only fires for sub-6 pt text rotated >45 deg off horizontal. The 2026-04-28
Opus audit caught five misses where the offending copy was **axis-aligned**
ingredient panels at 4-5 pt — not rotated, so the legibility rule didn't
trigger, but well below the FDA 21 CFR 101.2 / CFIA SOR/2003-11 minimums
(roughly 1.5 mm x-height ≈ 4.5 pt body size).

This rule is jurisdiction-agnostic and substrate-agnostic by design. It
complements :class:`LegibilityCompositeAnalyzer` (rotated, advisory) and
the AI regulatory analyzers (``AI_PHARMA_001`` / ``AI_EU1169_001``) which
gate on a specific regulatory market.

Check ID:
    LPDF_LEGALCOPY_001 — Text below FDA / CFIA legal-copy minimum size
        (composed font size or measured glyph height < 5.0 pt). Severity:
        ADVISORY. Per-page dedupe by (font_name, rounded size) so an
        ingredient block doesn't fan out into hundreds of findings.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# FDA 21 CFR 101.2(c) requires letters at least 1/16" tall (≈ 4.53 pt).
# CFIA SOR/2003-11 §B.01.012 mirrors that minimum. We round up to 5.0 pt
# as the practical threshold so anti-aliased renders still print legibly.
_LEGAL_MIN_PT = 5.0

# Reject sub-2pt sizes as degenerate (matches LegibilityComposite + WCAG_001
# calibration in PR #278). These are stray glyphs from outlined paths,
# transform artefacts, or one-off footnote markers — not body copy.
_DEGENERATE_PT = 2.0


def _composed_font_size_pt(event) -> float:  # type: ignore[no-untyped-def]
    """Effective on-page font size after ctm * text-matrix scale.

    Identical to the helper in ``analyzers.legibility_composite`` — the
    Y-axis basis vector magnitude (hypot of the composed second column)
    stays correct at 90 / 270 deg rotation where ``d=0``.
    """
    base = abs(event.font_size)
    if not event.ctm or not event.text_matrix:
        return base
    ctm = event.ctm
    tm = event.text_matrix
    cx = ctm.a * tm.c + ctm.c * tm.d
    cy = ctm.b * tm.c + ctm.d * tm.d
    return base * math.hypot(cx, cy)


class LegalCopyMinSizeAnalyzer(BaseAnalyzer):
    """Flag printed text whose composed size falls below the FDA / CFIA
    minimum body-copy threshold."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        from lintpdf.semantic.events import TextRenderedEvent

        findings: list[Finding] = []
        # Dedupe by (page, font_name, rounded size). One ingredient
        # block at 4.2 pt should produce one finding, not one per glyph.
        seen: set[tuple[int, str, float]] = set()

        for event in events:
            if not isinstance(event, TextRenderedEvent):
                continue
            # Invisible text (rendering mode 3) doesn't print, so no
            # legibility concern.
            if event.rendering_mode == 3:
                continue
            size_pt = _composed_font_size_pt(event)
            if size_pt < _DEGENERATE_PT:
                continue
            if size_pt >= _LEGAL_MIN_PT:
                continue
            size_bucket = round(size_pt, 1)
            key = (event.page_num, event.font_name, size_bucket)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    inspection_id="LPDF_LEGALCOPY_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Text at {size_pt:.1f} pt (font {event.font_name}) on page "
                        f"{event.page_num} falls below the FDA / CFIA legal-copy "
                        f"minimum of {_LEGAL_MIN_PT:.0f} pt (≈ 1.5 mm x-height per "
                        "FDA 21 CFR 101.2 / CFIA SOR/2003-11 §B.01.012). Verify "
                        "the panel against jurisdictional minimums or step the "
                        "type up to the regulatory threshold."
                    ),
                    page_num=event.page_num,
                    details={
                        "font_size_pt": round(size_pt, 2),
                        "font_name": event.font_name,
                        "min_legal_pt": _LEGAL_MIN_PT,
                    },
                    category="text",
                    object_type="text",
                    bbox=event.bbox,
                )
            )

        # PR-GG: outlined-fixture coverage. ``detected_text_regions``
        # is populated by the shared OCR pass on outlined / image-heavy
        # pages. Emit one finding per offending region with its bbox so
        # Lens can circle each instance on the canvas. Capped at 5 per
        # page to keep the findings panel manageable on dense panels.
        _MAX_PER_PAGE = 5
        for page in getattr(document, "pages", None) or []:
            regions = getattr(page, "detected_text_regions", None) or []
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
                if h < _DEGENERATE_PT:
                    continue
                if h >= _LEGAL_MIN_PT:
                    continue
                text_preview = (getattr(region, "text", None) or "")[:60]
                findings.append(
                    Finding(
                        inspection_id="LPDF_LEGALCOPY_001",
                        severity=Severity.ADVISORY,
                        message=(
                            "Outlined text ~%.1f pt on page %d" % (h, page.page_num)
                            + " is below FDA / CFIA minimum of %.0f pt" % _LEGAL_MIN_PT
                            + (" \u2014 \"%s\"" % text_preview if text_preview else "")
                            + ". Confirm FDA 21 CFR 101.2 / CFIA SOR/2003-11."
                        ),
                        page_num=page.page_num,
                        details={
                            "apparent_height_pt": round(h, 2),
                            "min_legal_pt": _LEGAL_MIN_PT,
                            "text_preview": text_preview,
                            "source": "ocr",
                        },
                        category="text",
                        object_type="text",
                        bbox=(x0, y0, x1, y1),
                    )
                )
                emitted += 1
        return findings
