"""EPM v2 Tier-B analyzer — soft-rejection checks.

Five detection-only analyzers backing the v2 IDs registered in
:mod:`lintpdf.epm.codes`. A single Tier-B finding lands the job in
"marginal"; two or more reject (per
:func:`lintpdf.epm.scoring.score_epm_candidacy`).

Codes:

* **EPM-B1** ``LPDF_EPM_PROCESS_COUNT_REJECT`` — process color count
  exceeds 4 (additional plates blow throughput advantage).
* **EPM-B3** ``LPDF_EPM_BLEED_REJECT`` — bleed below the per-page
  digital-press minimum.
* **EPM-B4** ``LPDF_EPM_PAGE_COUNT_REJECT`` — page count below
  economic break-even for an EPM run.
* **EPM-B5** ``LPDF_EPM_IMAGE_RES_REJECT`` — image resolution below
  digital-press minimum.
* **EPM-B6** ``LPDF_EPM_TRIM_REJECT`` — trim/bleed boxes inconsistent
  across pages (finishing risk).

Detection-only, no document mutation. Threshold tuning lives in the
``epm_thresholds`` toggle defaults; the analyzer accepts overrides
via constructor arguments so tenant-resolved values land cleanly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.epm import codes

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Defaults — keep under-tuned; the corpus regression PR re-tunes against
# real fixtures.
_DEFAULT_PROCESS_COLOR_LIMIT = 4
_DEFAULT_MIN_BLEED_PT = 8.5  # ~3 mm at 72 dpi
_DEFAULT_PAGE_COUNT_MIN = 4
_DEFAULT_IMAGE_DPI_MIN = 200.0
_DEFAULT_TRIM_TOLERANCE_PT = 0.5  # round-trip noise from PDF parser


class EpmTierBAnalyzer(BaseAnalyzer):
    """Tier-B EPM analyzer — fans out to the five B-tier detectors."""

    def __init__(
        self,
        *,
        process_color_limit: int = _DEFAULT_PROCESS_COLOR_LIMIT,
        min_bleed_pt: float = _DEFAULT_MIN_BLEED_PT,
        page_count_min: int = _DEFAULT_PAGE_COUNT_MIN,
        image_dpi_min: float = _DEFAULT_IMAGE_DPI_MIN,
        trim_tolerance_pt: float = _DEFAULT_TRIM_TOLERANCE_PT,
    ) -> None:
        self._process_color_limit = process_color_limit
        self._min_bleed_pt = min_bleed_pt
        self._page_count_min = page_count_min
        self._image_dpi_min = image_dpi_min
        self._trim_tolerance_pt = trim_tolerance_pt

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(detect_b1_process_color_count(document, limit=self._process_color_limit))
        findings.extend(detect_b3_bleed_below_min(document, min_bleed_pt=self._min_bleed_pt))
        findings.extend(detect_b4_page_count_below_min(document, min_pages=self._page_count_min))
        findings.extend(detect_b5_image_resolution_below_min(events, min_dpi=self._image_dpi_min))
        findings.extend(detect_b6_trim_inconsistent(document, tolerance_pt=self._trim_tolerance_pt))
        return findings


# ---- B1: process color count -------------------------------------------


def detect_b1_process_color_count(document: SemanticDocument, *, limit: int) -> list[Finding]:
    """Fire EPM-B1 when the document's distinct process color spaces
    exceed the EPM throughput limit.

    "Process colors" here means the canonical CMYK plates plus any
    Separation/DeviceN spot color names used as standalone plates. CMYK
    components inside a DeviceN are *not* counted separately.
    """
    spot_names: set[str] = set()
    has_cmyk = False
    has_rgb = False
    has_gray = False

    for page in document.pages:
        for cs in page.color_spaces.values():
            cs_type = (getattr(cs, "cs_type", "") or "").lower()
            colorant_names: tuple[str, ...] = getattr(cs, "colorant_names", None) or ()
            if "cmyk" in cs_type:
                has_cmyk = True
            elif "rgb" in cs_type:
                has_rgb = True
            elif "gray" in cs_type:
                has_gray = True
            elif "iccbased" in cs_type:
                # ICC-based with 4 components is CMYK; 3 is RGB; 1 is gray.
                components = getattr(cs, "components", 0)
                if components == 4:
                    has_cmyk = True
                elif components == 3:
                    has_rgb = True
                elif components == 1:
                    has_gray = True
            elif "separation" in cs_type or "devicen" in cs_type:
                for c in colorant_names:
                    if c and c.lower() not in {
                        "cyan",
                        "magenta",
                        "yellow",
                        "black",
                        "all",
                        "none",
                    }:
                        spot_names.add(c)

    process_count = sum([has_cmyk, has_rgb, has_gray]) + len(spot_names)
    if process_count <= limit:
        return []
    return [
        Finding(
            inspection_id=codes.EPM_PROCESS_COLOR_COUNT,
            severity=Severity.WARNING,
            message=(
                f"Document uses {process_count} process colors "
                f"(limit {limit}). Extra plates negate EPM throughput "
                "advantage."
            ),
            page_num=0,
            category="color",
            details={
                "process_count": process_count,
                "limit": limit,
                "spot_names": sorted(spot_names),
                "has_cmyk": has_cmyk,
                "has_rgb": has_rgb,
                "has_gray": has_gray,
            },
        )
    ]


# ---- B3: bleed below minimum -------------------------------------------


def detect_b3_bleed_below_min(document: SemanticDocument, *, min_bleed_pt: float) -> list[Finding]:
    """Fire EPM-B3 when any page's bleed margin is below ``min_bleed_pt``.

    Bleed margin = max distance from BleedBox edge to TrimBox edge across
    all four sides. When BleedBox or TrimBox is missing, falls back to
    MediaBox vs CropBox.
    """
    findings: list[Finding] = []

    for page in document.pages:
        bleed = page.bleed_box or page.media_box
        trim = page.trim_box or page.crop_box or page.media_box
        # Negative margin means trim is OUTSIDE bleed — broken geometry,
        # but treat it as zero-margin for this check.
        margins = [
            max(0.0, trim.x0 - bleed.x0),
            max(0.0, trim.y0 - bleed.y0),
            max(0.0, bleed.x1 - trim.x1),
            max(0.0, bleed.y1 - trim.y1),
        ]
        worst = min(margins)
        if worst >= min_bleed_pt:
            continue
        findings.append(
            Finding(
                inspection_id=codes.EPM_BLEED_BELOW_MIN,
                severity=Severity.WARNING,
                message=(
                    f"Page bleed {worst:.1f}pt is below the EPM minimum "
                    f"{min_bleed_pt:.1f}pt — finishing risk."
                ),
                page_num=page.page_num,
                category="geometry",
                details={
                    "bleed_pt": round(worst, 2),
                    "min_bleed_pt": min_bleed_pt,
                    "trim_box": trim.as_tuple(),
                    "bleed_box": bleed.as_tuple(),
                },
            )
        )
    return findings


# ---- B4: page count below economic break-even -------------------------


def detect_b4_page_count_below_min(document: SemanticDocument, *, min_pages: int) -> list[Finding]:
    """Fire EPM-B4 once at document scope when page count < min_pages."""
    if document.page_count >= min_pages:
        return []
    return [
        Finding(
            inspection_id=codes.EPM_PAGE_COUNT_BELOW_ECONOMIC,
            severity=Severity.WARNING,
            message=(
                f"Page count {document.page_count} is below the EPM "
                f"economic break-even ({min_pages})."
            ),
            page_num=0,
            category="document",
            details={
                "page_count": document.page_count,
                "min_pages": min_pages,
            },
        )
    ]


# ---- B5: image resolution below digital-press minimum ------------------


def detect_b5_image_resolution_below_min(
    events: list[ContentStreamEvent], *, min_dpi: float
) -> list[Finding]:
    """Fire EPM-B5 for every image placement whose effective DPI is
    below the digital-press minimum.

    Effective DPI is computed from the placement CTM scale times pixel
    dimension: ``dpi_x = pixel_width / (sx_pt / 72)`` and similarly for
    Y. The lower of the two axes wins (worst-case fidelity).
    """
    from lintpdf.semantic.events import ImagePlacedEvent

    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()

    for ev in events:
        if not isinstance(ev, ImagePlacedEvent):
            continue
        sx, sy = ev.ctm.extract_scale()
        if sx <= 0 or sy <= 0 or ev.pixel_width <= 0 or ev.pixel_height <= 0:
            continue
        dpi_x = ev.pixel_width / (sx / 72.0)
        dpi_y = ev.pixel_height / (sy / 72.0)
        worst = min(dpi_x, dpi_y)
        if worst >= min_dpi:
            continue
        key = (ev.page_num, ev.image_name)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                inspection_id=codes.EPM_IMAGE_RES_BELOW_DIGITAL,
                severity=Severity.WARNING,
                message=(
                    f"Image {ev.image_name} placed at "
                    f"{worst:.0f} DPI is below the digital-press "
                    f"minimum {min_dpi:.0f} DPI."
                ),
                page_num=ev.page_num,
                category="images",
                object_type="image",
                object_id=ev.image_name,
                details={
                    "dpi_x": round(dpi_x, 1),
                    "dpi_y": round(dpi_y, 1),
                    "min_dpi": min_dpi,
                    "pixel_width": ev.pixel_width,
                    "pixel_height": ev.pixel_height,
                },
            )
        )
    return findings


# ---- B6: trim/bleed inconsistent across pages --------------------------


def detect_b6_trim_inconsistent(
    document: SemanticDocument, *, tolerance_pt: float
) -> list[Finding]:
    """Fire EPM-B6 when trim or bleed boxes vary across pages by more
    than ``tolerance_pt`` on any edge.

    Pages with a missing TrimBox (i.e. defaulting to CropBox) are
    compared at their resolved value. A document with all pages
    converging on the same trim+bleed never fires — the finding is
    aimed at finishing-risk batches.
    """
    if document.page_count < 2:
        return []

    trim_boxes: list[tuple[int, tuple[float, float, float, float]]] = []
    bleed_boxes: list[tuple[int, tuple[float, float, float, float]]] = []

    for page in document.pages:
        trim = page.trim_box or page.crop_box or page.media_box
        bleed = page.bleed_box or page.crop_box or page.media_box
        trim_boxes.append((page.page_num, trim.as_tuple()))
        bleed_boxes.append((page.page_num, bleed.as_tuple()))

    def _max_edge_delta(
        rows: list[tuple[int, tuple[float, float, float, float]]],
    ) -> float:
        x0s = [r[1][0] for r in rows]
        y0s = [r[1][1] for r in rows]
        x1s = [r[1][2] for r in rows]
        y1s = [r[1][3] for r in rows]
        return max(
            max(x0s) - min(x0s),
            max(y0s) - min(y0s),
            max(x1s) - min(x1s),
            max(y1s) - min(y1s),
        )

    trim_delta = _max_edge_delta(trim_boxes)
    bleed_delta = _max_edge_delta(bleed_boxes)
    if trim_delta <= tolerance_pt and bleed_delta <= tolerance_pt:
        return []
    return [
        Finding(
            inspection_id=codes.EPM_TRIM_INCONSISTENT,
            severity=Severity.WARNING,
            message=(
                f"Trim/bleed inconsistent across pages — "
                f"trim Δ {trim_delta:.1f}pt, bleed Δ {bleed_delta:.1f}pt "
                f"(tolerance {tolerance_pt:.1f}pt)."
            ),
            page_num=0,
            category="geometry",
            details={
                "trim_delta_pt": round(trim_delta, 2),
                "bleed_delta_pt": round(bleed_delta, 2),
                "tolerance_pt": tolerance_pt,
                "page_count": document.page_count,
            },
        )
    ]


__all__ = [
    "EpmTierBAnalyzer",
    "detect_b1_process_color_count",
    "detect_b3_bleed_below_min",
    "detect_b4_page_count_below_min",
    "detect_b5_image_resolution_below_min",
    "detect_b6_trim_inconsistent",
]
