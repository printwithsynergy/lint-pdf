"""PageGeometryExtraAnalyzer — additional geometry checks added by
PR-S and PR-BB to close audit-surfaced misses on test-sample,
Amalgam_Catalyst, Pavette_Pride_v99, and Pink-Slush.

* ``LPDF_BOX_TRIMBOX_DEFAULTED`` (advisory) — page declares no
  explicit TrimBox; the parser defaulted it to MediaBox. Production
  workflows expect an explicit TrimBox so the press knows the final
  cut size. The engine's existing ``LPDF_BOX_001`` doesn't fire
  because the semantic builder hides the gap by defaulting upstream.
* ``LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT`` (warning) — declared
  BleedBox provides less than the configured minimum AND painted
  content extends past the BleedBox by >0pt. Combined-context
  finding that the existing ``LPDF_BOX_003`` (inadequate bleed) and
  ``LPDF_BOX_006`` (content beyond bleed) emit separately — the
  combination is the press-blocking case.
* ``LPDF_BOX_MULTI_LABEL_PAGE`` (warning) — page contains 2+
  disjoint content clusters separated by a meaningful empty band
  (>30pt). Most label workflows expect each die-cut artwork on
  its own page or with explicit dieline separation. Caught by
  Opus on Pavette_Pride (front circular + back rectangular labels
  on a single page).
* ``LPDF_BOX_TRIMBOX_UNDERSIZED`` (warning, PR-BB) — TrimBox is
  explicitly declared but painted artwork extends FAR past it
  (>2x normal bleed allowance). Indicates the TrimBox covers only
  one panel of a multi-panel layout while artwork covers the
  whole sheet — downstream imposition will crop critical regulatory
  copy. Caught by Opus on Pink-Slush p2 (TrimBox defined only the
  left/front panel while turquoise foot-panel + crimp areas extend
  to the right).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# ISO standard min bleed in points (~3 mm).
_DEFAULT_MIN_BLEED_PT = 8.5
# Minimum empty-band width (in points) before two clusters count as
# disjoint. ~10 mm — tight enough to detect real dual-label layouts
# without false-firing on single-label artwork with internal
# whitespace.
_MULTI_LABEL_GAP_PT = 30.0
# Smallest page dimension (in inches) where TrimBox==MediaBox is
# plausibly a single-up label (no false positive). Below this we
# don't fire LPDF_BOX_TRIMBOX_DEFAULTED.
_SMALL_PAGE_INCHES = 5.0
# Minimum artwork-past-TrimBox distance (points) before we treat the
# overhang as "undersized TrimBox" rather than "normal bleed". 2x the
# default min bleed (~6 mm = 17 pt) — anything beyond that is far past
# what a reasonable bleed allowance would explain.
_TRIMBOX_UNDERSIZE_PT = 17.0


class PageGeometryExtraAnalyzer(BaseAnalyzer):
    """PR-S: three additional geometry checks."""

    def __init__(self, min_bleed_pts: float = _DEFAULT_MIN_BLEED_PT) -> None:
        self._min_bleed_pts = min_bleed_pts

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        from lintpdf.semantic.events import ImagePlacedEvent, PathPaintingEvent

        bboxes_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
        for ev in events:
            if not isinstance(ev, (PathPaintingEvent, ImagePlacedEvent)):
                continue
            bbox = getattr(ev, "bbox", None)
            if bbox:
                bboxes_by_page.setdefault(ev.page_num, []).append(bbox)

        findings: list[Finding] = []
        for page in document.pages:
            findings.extend(self._check_trimbox_defaulted(page))
            findings.extend(self._check_bleed_too_thin_vs_content(page, bboxes_by_page))
            findings.extend(self._check_multi_label_page(page, bboxes_by_page))
            findings.extend(self._check_trimbox_undersized(page, bboxes_by_page))
        return findings

    @staticmethod
    def _check_trimbox_defaulted(page: object) -> list[Finding]:
        media = getattr(page, "media_box", None)
        trim = getattr(page, "trim_box", None)
        if media is None or trim is None:
            return []
        try:
            if not (
                abs(float(trim.x0) - float(media.x0)) < 0.5
                and abs(float(trim.y0) - float(media.y0)) < 0.5
                and abs(float(trim.x1) - float(media.x1)) < 0.5
                and abs(float(trim.y1) - float(media.y1)) < 0.5
            ):
                return []  # explicit TrimBox declared
            mw_in = (float(media.x1) - float(media.x0)) / 72.0
            mh_in = (float(media.y1) - float(media.y0)) / 72.0
        except (AttributeError, TypeError, ValueError):
            return []

        # Skip very small pages (label-shaped) where TrimBox==MediaBox
        # is plausibly intentional.
        if mw_in < _SMALL_PAGE_INCHES and mh_in < _SMALL_PAGE_INCHES:
            return []

        page_num = getattr(page, "page_num", 0)
        return [
            Finding(
                inspection_id="LPDF_BOX_TRIMBOX_DEFAULTED",
                severity=Severity.ADVISORY,
                message=(
                    f"Page {page_num} has no explicit TrimBox; the engine "
                    "defaulted it to the MediaBox. Production workflows "
                    "expect an explicit TrimBox so the press knows the "
                    "final cut size, distinct from any bleed area."
                ),
                page_num=page_num,
                details={
                    "page_size_inches": [round(mw_in, 2), round(mh_in, 2)],
                    "trim_equals_media": True,
                },
                category="page",
                object_type="page",
                iso_clause="ISO 15930-7:2010 6.2.1",
            )
        ]

    def _check_bleed_too_thin_vs_content(
        self,
        page: object,
        bboxes_by_page: dict[int, list[tuple[float, float, float, float]]],
    ) -> list[Finding]:
        trim = getattr(page, "trim_box", None)
        bleed = getattr(page, "bleed_box", None)
        if trim is None or bleed is None:
            return []
        try:
            tx0, ty0, tx1, ty1 = (
                float(trim.x0),
                float(trim.y0),
                float(trim.x1),
                float(trim.y1),
            )
            bx0, by0, bx1, by1 = (
                float(bleed.x0),
                float(bleed.y0),
                float(bleed.x1),
                float(bleed.y1),
            )
        except (AttributeError, TypeError, ValueError):
            return []

        bleed_offsets = (tx0 - bx0, by1 - ty1, bx1 - tx1, ty0 - by0)
        min_offset = min(bleed_offsets)
        # Suppress when bleed is either fully zero (LPDF_BOX_BG_NO_BLEED
        # owns that case) or already at/above the configured minimum.
        if min_offset <= 0.0 or min_offset >= self._min_bleed_pts:
            return []

        page_num = getattr(page, "page_num", 0)
        page_bboxes = bboxes_by_page.get(page_num, [])
        # Look for any painted bbox extending past the BleedBox by
        # >0.5pt on any side.
        for ex0, ey0, ex1, ey1 in page_bboxes:
            past_bleed = ex0 < bx0 - 0.5 or ex1 > bx1 + 0.5 or ey0 < by0 - 0.5 or ey1 > by1 + 0.5
            if past_bleed:
                return [
                    Finding(
                        inspection_id="LPDF_BOX_BLEED_TOO_THIN_VS_CONTENT",
                        severity=Severity.WARNING,
                        message=(
                            f"Page {page_num}: declared BleedBox provides only "
                            f"{min_offset:.1f} pt of bleed (minimum "
                            f"{self._min_bleed_pts:.1f} pt) AND painted "
                            "artwork extends past the BleedBox. The press has "
                            "no working margin: any cut variance will reveal "
                            "either unprinted substrate or trimmed artwork."
                        ),
                        page_num=page_num,
                        details={
                            "bleed_offsets_pt": [round(o, 2) for o in bleed_offsets],
                            "min_bleed_pt": self._min_bleed_pts,
                        },
                        category="page",
                        object_type="page",
                    )
                ]
        return []

    @staticmethod
    def _check_multi_label_page(
        page: object,
        bboxes_by_page: dict[int, list[tuple[float, float, float, float]]],
    ) -> list[Finding]:
        page_num = getattr(page, "page_num", 0)
        bboxes = bboxes_by_page.get(page_num, [])
        if len(bboxes) < 30:
            return []  # not enough painted content to reason about clusters

        media = getattr(page, "media_box", None)
        if media is None:
            return []

        # Naive cluster detection: find a horizontal or vertical band
        # of >= _MULTI_LABEL_GAP_PT of empty space spanning the entire
        # painted content extent. If found, page is multi-label.
        min_x = min(b[0] for b in bboxes)
        max_x = max(b[2] for b in bboxes)
        min_y = min(b[1] for b in bboxes)
        max_y = max(b[3] for b in bboxes)

        # Sweep a coarse grid (1pt step would be O(N×W) — too slow).
        # Sample at 5pt intervals.
        gap_axis = _largest_empty_band(bboxes, axis="y", lo=min_y, hi=max_y)
        if gap_axis is None or gap_axis < _MULTI_LABEL_GAP_PT:
            gap_axis = _largest_empty_band(bboxes, axis="x", lo=min_x, hi=max_x)
        if gap_axis is None or gap_axis < _MULTI_LABEL_GAP_PT:
            return []

        return [
            Finding(
                inspection_id="LPDF_BOX_MULTI_LABEL_PAGE",
                severity=Severity.WARNING,
                message=(
                    f"Page {page_num} appears to contain multiple distinct "
                    f"label artworks separated by a {gap_axis:.0f} pt empty "
                    "band. Most label workflows expect each die-cut artwork "
                    "on its own page or with explicit dieline separation. "
                    "Confirm imposition is intentional and dielines are "
                    "supplied for each label."
                ),
                page_num=page_num,
                details={
                    "empty_band_pt": round(gap_axis, 1),
                    "painted_extent_pt": [
                        round(min_x, 1),
                        round(min_y, 1),
                        round(max_x, 1),
                        round(max_y, 1),
                    ],
                },
                category="page",
                object_type="page",
            )
        ]

    @staticmethod
    def _check_trimbox_undersized(
        page: object,
        bboxes_by_page: dict[int, list[tuple[float, float, float, float]]],
    ) -> list[Finding]:
        """Fire when artwork extends far past TrimBox — beyond what any
        reasonable bleed allowance would explain. Indicates the TrimBox
        was set too small (e.g., only one panel of a multi-panel layout)
        and downstream imposition will crop the rest.
        """
        media = getattr(page, "media_box", None)
        trim = getattr(page, "trim_box", None)
        if media is None or trim is None:
            return []
        try:
            tx0, ty0, tx1, ty1 = (
                float(trim.x0),
                float(trim.y0),
                float(trim.x1),
                float(trim.y1),
            )
            mx0, my0, mx1, my1 = (
                float(media.x0),
                float(media.y0),
                float(media.x1),
                float(media.y1),
            )
        except (AttributeError, TypeError, ValueError):
            return []

        # Suppress if TrimBox==MediaBox (LPDF_BOX_TRIMBOX_DEFAULTED owns
        # that case) — the audit miss only applies when the designer
        # explicitly set a smaller TrimBox.
        if (
            abs(tx0 - mx0) < 0.5
            and abs(ty0 - my0) < 0.5
            and abs(tx1 - mx1) < 0.5
            and abs(ty1 - my1) < 0.5
        ):
            return []

        page_num = getattr(page, "page_num", 0)
        page_bboxes = bboxes_by_page.get(page_num, [])
        if not page_bboxes:
            return []

        # Find the worst painted-content overhang past TrimBox on any side.
        max_overhang = 0.0
        worst_side: str | None = None
        for ex0, ey0, ex1, ey1 in page_bboxes:
            for side, dist in (
                ("left", tx0 - ex0),
                ("right", ex1 - tx1),
                ("bottom", ty0 - ey0),
                ("top", ey1 - ty1),
            ):
                if dist > max_overhang:
                    max_overhang = dist
                    worst_side = side

        if max_overhang < _TRIMBOX_UNDERSIZE_PT:
            return []

        return [
            Finding(
                inspection_id="LPDF_BOX_TRIMBOX_UNDERSIZED",
                severity=Severity.WARNING,
                message=(
                    f"Page {page_num}: painted artwork extends {max_overhang:.1f} pt "
                    f"past the TrimBox on the {worst_side} side — far beyond a "
                    "normal bleed allowance. The TrimBox likely covers only one "
                    "panel of a multi-panel layout; downstream imposition will "
                    "crop the rest. Either expand the TrimBox to encompass the "
                    "full artwork or supply per-panel TrimBoxes."
                ),
                page_num=page_num,
                details={
                    "overhang_pt": round(max_overhang, 2),
                    "worst_side": worst_side,
                    "trim_box": [tx0, ty0, tx1, ty1],
                },
                category="page",
                object_type="page",
            )
        ]


def _largest_empty_band(
    bboxes: list[tuple[float, float, float, float]],
    *,
    axis: str,
    lo: float,
    hi: float,
) -> float | None:
    """Return the width of the largest empty band perpendicular to ``axis``.

    Sweeps at 5pt increments. ``axis="y"`` finds horizontal empty
    bands (gaps in y); ``axis="x"`` finds vertical empty bands.
    Returns None when fewer than 2 cluster transitions exist.
    """
    step = 5.0
    if hi - lo < step * 4:
        return None
    occupied: list[bool] = []
    pos = lo
    while pos <= hi:
        # Cell midpoint at pos+step/2; "occupied" if any bbox covers
        # this axis position.
        cell_lo = pos
        cell_hi = pos + step
        is_occ = False
        for ex0, ey0, ex1, ey1 in bboxes:
            if axis == "y":
                if ey0 < cell_hi and ey1 > cell_lo:
                    is_occ = True
                    break
            else:
                if ex0 < cell_hi and ex1 > cell_lo:
                    is_occ = True
                    break
        occupied.append(is_occ)
        pos += step

    largest_gap = 0.0
    current_gap = 0.0
    for occ in occupied:
        if occ:
            largest_gap = max(largest_gap, current_gap)
            current_gap = 0.0
        else:
            current_gap += step
    largest_gap = max(largest_gap, current_gap)
    # Reject leading/trailing empty bands (they're just margins, not
    # between-cluster gaps). Require the gap to be flanked by occupied
    # cells on both sides.
    if not occupied or not occupied[0] or not occupied[-1]:
        # Strip trailing/leading false runs by recomputing on the
        # interior only.
        first_occ = next((i for i, o in enumerate(occupied) if o), None)
        last_occ = next(
            (len(occupied) - 1 - i for i, o in enumerate(reversed(occupied)) if o),
            None,
        )
        if first_occ is None or last_occ is None or last_occ <= first_occ:
            return None
        interior = occupied[first_occ : last_occ + 1]
        largest_gap = 0.0
        current_gap = 0.0
        for occ in interior:
            if occ:
                largest_gap = max(largest_gap, current_gap)
                current_gap = 0.0
            else:
                current_gap += step
    return largest_gap if largest_gap > 0 else None
