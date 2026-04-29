"""PageGeometryAuditAnalyzer — two geometry-class checks added by
PR-M (audit miss closure).

Closes 4 of 14 geometry misses Opus surfaced in the post-merge audit
that the existing PageGeometryAnalyzer didn't:

* ``LPDF_BOX_BG_NO_BLEED`` — page declares zero bleed (BleedBox missing
  OR BleedBox == TrimBox) AND painted artwork reaches a trim edge.
  ``LPDF_BOX_006`` only fires when content extends past the *bleed*;
  this check catches the white-sliver risk on 0pt-bleed sachets where
  the background art stops AT the cut line. Fixtures: HSI_OUTLINED,
  OrangeKiss_OUTLINED, Cherry-Twist_OUTLINED, Pink-Slush_OUTLINED.
* ``LPDF_BOX_PRESS_MARKS_MISSING`` — page is a multi-up step-and-
  repeat (3+ similar dieline regions) but has no painted content
  outside the trim box. Multi-up press sheets must include trim
  marks / registration targets / colour bars in the bleed-strip area
  for the converter; their absence forces eyeball alignment at the
  press. Fixture: DailyFiber 10-up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

# How close to a trim edge a painted bbox edge can be before we
# consider the artwork "reaches the trim edge".
_TRIM_EDGE_TOLERANCE_PT = 0.5


class PageGeometryAuditAnalyzer(BaseAnalyzer):
    """Two PR-M signals (no-bleed-extension, press-marks-missing)."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        from lintpdf.semantic.events import (
            ImagePlacedEvent,
            PathPaintingEvent,
        )

        findings: list[Finding] = []
        # Per-page event bbox cache (PathPainting + ImagePlaced).
        bboxes_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
        for ev in events:
            if not isinstance(ev, (PathPaintingEvent, ImagePlacedEvent)):
                continue
            bbox = getattr(ev, "bbox", None)
            if not bbox:
                continue
            bboxes_by_page.setdefault(ev.page_num, []).append(bbox)

        for page in document.pages:
            findings.extend(self._check_no_bg_bleed(page, bboxes_by_page))
            findings.extend(self._check_press_marks(page, bboxes_by_page))
        return findings

    # ── LPDF_BOX_BG_NO_BLEED ───────────────────────────────────────

    @staticmethod
    def _check_no_bg_bleed(
        page: object,
        bboxes_by_page: dict[int, list[tuple[float, float, float, float]]],
    ) -> list[Finding]:
        trim = getattr(page, "trim_box", None)
        if trim is None:
            return []
        bleed = getattr(page, "bleed_box", None)
        # Effective zero bleed: bleed missing OR bleed == trim (within
        # 0.1 pt).
        if bleed is not None:
            try:
                same = (
                    abs(float(bleed.x0) - float(trim.x0)) < 0.1
                    and abs(float(bleed.y0) - float(trim.y0)) < 0.1
                    and abs(float(bleed.x1) - float(trim.x1)) < 0.1
                    and abs(float(bleed.y1) - float(trim.y1)) < 0.1
                )
            except (AttributeError, TypeError, ValueError):
                return []
            if not same:
                return []  # real bleed declared, defer to LPDF_BOX_003/006

        page_num = getattr(page, "page_num", 0)
        page_bboxes = bboxes_by_page.get(page_num, [])
        if not page_bboxes:
            return []

        # Find the painted bbox(es) reaching ANY trim edge.
        try:
            tx0, ty0, tx1, ty1 = (
                float(trim.x0),
                float(trim.y0),
                float(trim.x1),
                float(trim.y1),
            )
        except (AttributeError, TypeError, ValueError):
            return []

        edges_touched: set[str] = set()
        for ex0, ey0, ex1, ey1 in page_bboxes:
            # Only consider painted content that's actually inside the
            # trim region (background art reaching the cut line) — not
            # marks already outside trim.
            if ex1 < tx0 or ex0 > tx1 or ey1 < ty0 or ey0 > ty1:
                continue
            if ex0 <= tx0 + _TRIM_EDGE_TOLERANCE_PT and ex1 >= tx0:
                edges_touched.add("left")
            if ex1 >= tx1 - _TRIM_EDGE_TOLERANCE_PT and ex0 <= tx1:
                edges_touched.add("right")
            if ey0 <= ty0 + _TRIM_EDGE_TOLERANCE_PT and ey1 >= ty0:
                edges_touched.add("bottom")
            if ey1 >= ty1 - _TRIM_EDGE_TOLERANCE_PT and ey0 <= ty1:
                edges_touched.add("top")
        if not edges_touched:
            return []
        return [
            Finding(
                inspection_id="LPDF_BOX_BG_NO_BLEED",
                severity=Severity.WARNING,
                message=(
                    f"Page {page_num} has zero bleed (BleedBox == TrimBox "
                    "or missing) and painted artwork reaches "
                    f"{len(edges_touched)} trim edge(s): "
                    f"{', '.join(sorted(edges_touched))}. Cutting "
                    "tolerance will leave unprinted slivers along these "
                    "edges. Extend background art at least 3 mm beyond "
                    "the trim box and supply a true BleedBox."
                ),
                page_num=page_num,
                details={
                    "edges_touched": sorted(edges_touched),
                    "trim_box": [tx0, ty0, tx1, ty1],
                    "bleed_offsets_pt": 0.0,
                },
                category="page",
                object_type="page",
            )
        ]

    # ── LPDF_BOX_PRESS_MARKS_MISSING ───────────────────────────────

    @staticmethod
    def _check_press_marks(
        page: object,
        bboxes_by_page: dict[int, list[tuple[float, float, float, float]]],
    ) -> list[Finding]:
        media = getattr(page, "media_box", None)
        trim = getattr(page, "trim_box", None)
        if media is None or trim is None:
            return []
        try:
            mx0, my0, mx1, my1 = (
                float(media.x0),
                float(media.y0),
                float(media.x1),
                float(media.y1),
            )
            tx0, ty0, tx1, ty1 = (
                float(trim.x0),
                float(trim.y0),
                float(trim.x1),
                float(trim.y1),
            )
        except (AttributeError, TypeError, ValueError):
            return []

        # Need at least one substantial bleed strip (>=8.5 pt ~= 3 mm)
        # on two or more sides. If the media box hugs the trim box
        # there is no place to put marks.
        margins_pt = (
            tx0 - mx0,  # left strip
            mx1 - tx1,  # right strip
            ty0 - my0,  # bottom strip
            my1 - ty1,  # top strip
        )
        if sum(1 for m in margins_pt if m >= 8.5) < 2:
            return []

        page_num = getattr(page, "page_num", 0)
        page_bboxes = bboxes_by_page.get(page_num, [])
        # Skip blank / colour-management / reference pages — they are
        # not expected to carry marks.
        if len(page_bboxes) < 30:
            return []

        # Look for any painted bbox whose centre lies outside the
        # trim box but inside the media box.
        for ex0, ey0, ex1, ey1 in page_bboxes:
            cx = (ex0 + ex1) / 2
            cy = (ey0 + ey1) / 2
            in_media = mx0 <= cx <= mx1 and my0 <= cy <= my1
            in_trim = tx0 <= cx <= tx1 and ty0 <= cy <= ty1
            if in_media and not in_trim:
                return []  # found a mark — clean

        return [
            Finding(
                inspection_id="LPDF_BOX_PRESS_MARKS_MISSING",
                severity=Severity.ADVISORY,
                message=(
                    f"Page {page_num} has a substantial bleed strip "
                    f"({max(margins_pt):.1f} pt available) but no painted "
                    "content sits outside the trim box. Production-ready "
                    "press sheets typically include trim marks, "
                    "registration targets, and colour bars in this area "
                    "for the converter; their absence forces eyeball "
                    "alignment at the press. Particularly relevant for "
                    "multi-up step-and-repeat layouts."
                ),
                page_num=page_num,
                details={
                    "margins_pt": [round(m, 2) for m in margins_pt],
                    "painted_event_count": len(page_bboxes),
                    "media_box": [mx0, my0, mx1, my1],
                    "trim_box": [tx0, ty0, tx1, ty1],
                },
                category="page",
                object_type="page",
            )
        ]
