"""PageGeometryAnalyzer — box hierarchy, bleed distance, dimensions.

Processes SemanticDocument page data to validate page geometry for print.

Box hierarchy (ISO 32000-2:2020 section 14.11.2):
    MediaBox >= BleedBox >= TrimBox >= ArtBox
    CropBox defaults to MediaBox
    BleedBox/TrimBox/ArtBox default to CropBox

Check IDs:
    GRD_BOX_001 — TrimBox or BleedBox missing (required for print)
    GRD_BOX_002 — Box hierarchy violated
    GRD_BOX_003 — Bleed distance inadequate
    GRD_BOX_004 — Empty page (no content stream)
    GRD_BOX_005 — Content within safety margin of trim edge
    GRD_BOX_006 — Content extends beyond bleed box
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage

# Standard minimum bleed in points (3mm = ~8.5 points)
DEFAULT_MIN_BLEED_PTS = 8.5


class PageGeometryAnalyzer(BaseAnalyzer):
    """Analyzer for page box hierarchy and bleed requirements.

    Args:
        min_bleed_pts: Minimum bleed distance in points (default 8.5 ~= 3mm).
        safety_margin_pts: Safety margin from trim edge in points (default 8.5 ~= 3mm).
    """

    def __init__(
        self,
        min_bleed_pts: float = DEFAULT_MIN_BLEED_PTS,
        safety_margin_pts: float = DEFAULT_MIN_BLEED_PTS,
    ) -> None:
        self.min_bleed_pts = min_bleed_pts
        self.safety_margin_pts = safety_margin_pts

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze page geometry for all pages."""
        from grounded.semantic.events import PathPaintingEvent, TextRenderedEvent

        findings: list[Finding] = []

        for page in document.pages:
            findings.extend(self._check_page(page))

        # GRD_BOX_005 / GRD_BOX_006: Content proximity to trim/bleed edges
        # Build page lookup for trim/bleed boxes
        page_boxes: dict[int, tuple[PdfBox | None, PdfBox | None]] = {}
        for page in document.pages:
            page_boxes[page.page_num] = (page.trim_box, page.bleed_box)

        for event in events:
            if not isinstance(event, (PathPaintingEvent, TextRenderedEvent)):
                continue
            bbox = event.bbox
            if bbox is None:
                continue
            trim_box, bleed_box = page_boxes.get(event.page_num, (None, None))
            findings.extend(
                self._check_content_proximity(event.page_num, bbox, trim_box, bleed_box)
            )

        return findings

    def _check_content_proximity(  # skipcq: PY-R1000
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        trim_box: PdfBox | None,
        bleed_box: PdfBox | None,
    ) -> list[Finding]:
        """Check if content bbox is too close to trim edge or beyond bleed."""
        findings: list[Finding] = []
        bx0, by0, bx1, by1 = bbox

        # GRD_BOX_005: Content within safety margin of trim edge
        if trim_box is not None:
            margin = self.safety_margin_pts
            in_safety = (
                bx0 < trim_box.x0 + margin
                or by0 < trim_box.y0 + margin
                or bx1 > trim_box.x1 - margin
                or by1 > trim_box.y1 - margin
            )
            # Only flag if content is inside (or overlapping) the trim box
            in_trim = (
                bx1 > trim_box.x0 and bx0 < trim_box.x1 and by1 > trim_box.y0 and by0 < trim_box.y1
            )
            if in_safety and in_trim:
                findings.append(
                    Finding(
                        inspection_id="GRD_BOX_005",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Content within {self.safety_margin_pts:.1f}pt safety margin "
                            f"of trim edge on page {page_num}"
                        ),
                        page_num=page_num,
                        details={
                            "content_bbox": list(bbox),
                            "trim_box": trim_box.as_tuple(),
                            "safety_margin_pts": self.safety_margin_pts,
                        },
                        object_type="path",
                        bbox=bbox,
                    )
                )

        # GRD_BOX_006: Content extends beyond bleed box
        if bleed_box is not None:
            beyond_bleed = (
                bx0 < bleed_box.x0 or by0 < bleed_box.y0 or bx1 > bleed_box.x1 or by1 > bleed_box.y1
            )
            if beyond_bleed:
                findings.append(
                    Finding(
                        inspection_id="GRD_BOX_006",
                        severity=Severity.SQUALL,
                        message=(f"Content extends beyond bleed box on page {page_num}"),
                        page_num=page_num,
                        details={
                            "content_bbox": list(bbox),
                            "bleed_box": bleed_box.as_tuple(),
                        },
                        object_type="path",
                        bbox=bbox,
                    )
                )

        return findings

    def _check_page(self, page: SemanticPage) -> list[Finding]:
        """Check a single page's geometry."""

        findings: list[Finding] = []

        # GRD_BOX_001: Required boxes present
        if page.trim_box is None:
            findings.append(
                Finding(
                    inspection_id="GRD_BOX_001",
                    severity=Severity.SQUALL,
                    message=f"TrimBox missing on page {page.page_num}",
                    page_num=page.page_num,
                    details={"missing_box": "TrimBox"},
                    iso_clause="ISO 15930-7:2010 6.2.1",
                )
            )

        if page.bleed_box is None:
            findings.append(
                Finding(
                    inspection_id="GRD_BOX_001",
                    severity=Severity.SQUALL,
                    message=f"BleedBox missing on page {page.page_num}",
                    page_num=page.page_num,
                    details={"missing_box": "BleedBox"},
                    iso_clause="ISO 15930-7:2010 6.2.1",
                )
            )

        # GRD_BOX_002: Box hierarchy validation
        findings.extend(self._check_hierarchy(page))

        # GRD_BOX_003: Bleed distance
        if page.trim_box is not None and page.bleed_box is not None:
            findings.extend(
                self._check_bleed_distance(page.page_num, page.trim_box, page.bleed_box)
            )

        # GRD_BOX_004: Empty page (no content stream)
        if not page.content_stream:
            findings.append(
                Finding(
                    inspection_id="GRD_BOX_004",
                    severity=Severity.ADVISORY,
                    message=f"Page {page.page_num} has no content stream (empty page)",
                    page_num=page.page_num,
                    details={"page_num": page.page_num},
                )
            )

        return findings

    @staticmethod
    def _check_hierarchy(page: SemanticPage) -> list[Finding]:
        """Validate box containment hierarchy."""

        findings: list[Finding] = []
        media = page.media_box
        crop = page.crop_box or media

        # CropBox must be within MediaBox
        if page.crop_box and not media.contains_box(page.crop_box):
            findings.append(
                Finding(
                    inspection_id="GRD_BOX_002",
                    severity=Severity.SQUALL,
                    message=(f"CropBox extends outside MediaBox on page {page.page_num}"),
                    page_num=page.page_num,
                    details={
                        "media_box": media.as_tuple(),
                        "crop_box": page.crop_box.as_tuple(),
                    },
                    iso_clause="ISO 32000-2:2020 14.11.2",
                )
            )

        # BleedBox must be within CropBox (or MediaBox)
        if page.bleed_box and not crop.contains_box(page.bleed_box):
            findings.append(
                Finding(
                    inspection_id="GRD_BOX_002",
                    severity=Severity.SQUALL,
                    message=(f"BleedBox extends outside CropBox on page {page.page_num}"),
                    page_num=page.page_num,
                    details={
                        "crop_box": crop.as_tuple(),
                        "bleed_box": page.bleed_box.as_tuple(),
                    },
                    iso_clause="ISO 32000-2:2020 14.11.2",
                )
            )

        # TrimBox must be within BleedBox (if both present)
        if page.trim_box and page.bleed_box and not page.bleed_box.contains_box(page.trim_box):
            findings.append(
                Finding(
                    inspection_id="GRD_BOX_002",
                    severity=Severity.SQUALL,
                    message=(f"TrimBox extends outside BleedBox on page {page.page_num}"),
                    page_num=page.page_num,
                    details={
                        "bleed_box": page.bleed_box.as_tuple(),
                        "trim_box": page.trim_box.as_tuple(),
                    },
                    iso_clause="ISO 32000-2:2020 14.11.2",
                )
            )

        return findings

    def _check_bleed_distance(
        self,
        page_num: int,
        trim_box: PdfBox,
        bleed_box: PdfBox,
    ) -> list[Finding]:
        """Check that bleed extends adequately beyond trim on all sides."""
        findings: list[Finding] = []

        bleed_left = trim_box.x0 - bleed_box.x0
        bleed_right = bleed_box.x1 - trim_box.x1
        bleed_bottom = trim_box.y0 - bleed_box.y0
        bleed_top = bleed_box.y1 - trim_box.y1

        bleeds = {
            "left": bleed_left,
            "right": bleed_right,
            "bottom": bleed_bottom,
            "top": bleed_top,
        }

        inadequate = {side: dist for side, dist in bleeds.items() if dist < self.min_bleed_pts}

        if inadequate:
            min_bleed_mm = self.min_bleed_pts * 0.352778
            findings.append(
                Finding(
                    inspection_id="GRD_BOX_003",
                    severity=Severity.SQUALL,
                    message=(
                        f"Inadequate bleed on page {page_num}: "
                        + ", ".join(f"{side} {dist:.1f}pt" for side, dist in inadequate.items())
                        + f" (minimum {self.min_bleed_pts:.1f}pt / {min_bleed_mm:.1f}mm)"
                    ),
                    page_num=page_num,
                    details={
                        "bleeds": bleeds,
                        "inadequate_sides": inadequate,
                        "min_bleed_pts": self.min_bleed_pts,
                    },
                    iso_clause="GWG 2022 6.1",
                )
            )

        return findings
