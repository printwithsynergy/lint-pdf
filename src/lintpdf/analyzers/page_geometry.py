"""PageGeometryAnalyzer — box hierarchy, bleed distance, dimensions.

Processes SemanticDocument page data to validate page geometry for print.

Box hierarchy (ISO 32000-2:2020 section 14.11.2):
    MediaBox >= BleedBox >= TrimBox >= ArtBox
    CropBox defaults to MediaBox
    BleedBox/TrimBox/ArtBox default to CropBox

Check IDs:
    LPDF_BOX_001 — TrimBox or BleedBox missing (required for print)
    LPDF_BOX_002 — Box hierarchy violated
    LPDF_BOX_003 — Bleed distance inadequate
    LPDF_BOX_004 — Empty page (no content stream)
    LPDF_BOX_005 — Content within safety margin of trim edge
    LPDF_BOX_006 — Content extends beyond bleed box
    LPDF_BOX_007 — UserUnit scaling detected
    LPDF_BOX_008 — Non-standard page orientation
    LPDF_BOX_009 — Inconsistent page sizes
    LPDF_BOX_010 — Page size doesn't match expected product dimensions (T1-STR04)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.primitives import geometry as geom_primitives

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage

# Standard minimum bleed in points (3mm = ~8.5 points)
DEFAULT_MIN_BLEED_PTS = 8.5


def _aabb_union(
    rects: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float] | None:
    """Axis-aligned-bbox union over a list of non-empty rects.

    Empty input -> ``None``. Used by the violation-region helpers
    so a content object that crosses multiple margin strips emits
    a single tightest-enclosing AABB rather than one finding per
    strip (the viewer draws one highlight, not four).
    """
    if not rects:
        return None
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[2] for r in rects)
    y1 = max(r[3] for r in rects)
    return (x0, y0, x1, y1)


def _intersect(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> tuple[float, float, float, float] | None:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix0 >= ix1 or iy0 >= iy1:
        return None
    return (ix0, iy0, ix1, iy1)


def _safety_margin_violation(
    content_bbox: tuple[float, float, float, float],
    trim: PdfBox,
    margin: float,
) -> tuple[float, float, float, float] | None:
    """Return the portion of ``content_bbox`` that sits inside the
    safety-margin ring (the N-pt strip around the inside of the
    trim box). ``None`` when content is entirely inside the inner
    safe zone or entirely outside the trim box (those aren't
    safety-margin violations)."""
    trim_rect = (trim.x0, trim.y0, trim.x1, trim.y1)
    # Content must be at least partially inside the trim to count.
    in_trim = _intersect(content_bbox, trim_rect)
    if in_trim is None:
        return None
    # The inner "safe" zone: trim minus margin on every side.
    if margin <= 0 or (trim.x1 - trim.x0) <= 2 * margin or (trim.y1 - trim.y0) <= 2 * margin:
        # Degenerate: the whole trim is a margin. Report the
        # trim intersection verbatim.
        return in_trim
    inner_rect = (
        trim.x0 + margin,
        trim.y0 + margin,
        trim.x1 - margin,
        trim.y1 - margin,
    )
    # Four margin strips (left, right, bottom, top) that make up
    # the ring between trim and inner_rect.
    strips = [
        (trim.x0, trim.y0, inner_rect[0], trim.y1),  # left
        (inner_rect[2], trim.y0, trim.x1, trim.y1),  # right
        (inner_rect[0], trim.y0, inner_rect[2], inner_rect[1]),  # bottom
        (inner_rect[0], inner_rect[3], inner_rect[2], trim.y1),  # top
    ]
    parts = [p for p in (_intersect(in_trim, s) for s in strips) if p is not None]
    return _aabb_union(parts)


def _beyond_bleed_violation(
    content_bbox: tuple[float, float, float, float],
    bleed: PdfBox,
) -> tuple[float, float, float, float] | None:
    """Return the portion of ``content_bbox`` that sits outside the
    bleed box. ``None`` when all of the content fits inside bleed."""
    bleed_rect = (bleed.x0, bleed.y0, bleed.x1, bleed.y1)
    inside = _intersect(content_bbox, bleed_rect)
    if inside == content_bbox:
        # Fully inside the bleed.
        return None
    # Four external strips (the whole PDF page plane beyond bleed).
    # Clip content against each side individually and take the
    # AABB of non-empty pieces.
    cx0, cy0, cx1, cy1 = content_bbox
    strips = [
        (cx0, cy0, min(cx1, bleed.x0), cy1),  # left of bleed
        (max(cx0, bleed.x1), cy0, cx1, cy1),  # right of bleed
        (cx0, cy0, cx1, min(cy1, bleed.y0)),  # below bleed
        (cx0, max(cy0, bleed.y1), cx1, cy1),  # above bleed
    ]
    valid: list[tuple[float, float, float, float]] = []
    for s in strips:
        if s[0] < s[2] and s[1] < s[3]:
            valid.append(s)
    return _aabb_union(valid)


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
        expected_page_width_mm: float | None = None,
        expected_page_height_mm: float | None = None,
        expected_page_size_tolerance_mm: float = 0.5,
    ) -> None:
        self.min_bleed_pts = min_bleed_pts
        self.safety_margin_pts = safety_margin_pts
        self.expected_page_width_mm = expected_page_width_mm
        self.expected_page_height_mm = expected_page_height_mm
        self.expected_page_size_tolerance_mm = expected_page_size_tolerance_mm

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze page geometry for all pages."""
        from lintpdf.semantic.events import PathPaintingEvent, TextRenderedEvent

        findings: list[Finding] = []

        for page in document.pages:
            findings.extend(self._check_page(page))

        # LPDF_BOX_008 (document-level): Mixed page orientations
        if len(document.pages) > 1:
            orientations: set[str] = set()
            for page in document.pages:
                ref_box = page.trim_box or page.media_box
                width = ref_box.x1 - ref_box.x0
                height = ref_box.y1 - ref_box.y0
                orientations.add("landscape" if width > height else "portrait")
            if len(orientations) > 1:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BOX_008",
                        severity=Severity.ADVISORY,
                        message=(
                            "Document has mixed page orientations "
                            "(both portrait and landscape pages detected)"
                        ),
                        details={"orientations": sorted(orientations)},
                        iso_clause="ISO 32000-2:2020 14.11.2",
                    )
                )

        # LPDF_BOX_009: Inconsistent page sizes
        if len(document.pages) > 1:
            page_sizes: dict[tuple[float, float], list[int]] = {}
            for page in document.pages:
                ref_box = page.trim_box or page.media_box
                width = round(ref_box.x1 - ref_box.x0, 0)
                height = round(ref_box.y1 - ref_box.y0, 0)
                size_key = (width, height)
                page_sizes.setdefault(size_key, []).append(page.page_num)
            if len(page_sizes) > 1:
                unique_sizes = [
                    {"width_pt": w, "height_pt": h, "pages": pages}
                    for (w, h), pages in page_sizes.items()
                ]
                findings.append(
                    Finding(
                        inspection_id="LPDF_BOX_009",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Document has inconsistent page sizes "
                            f"({len(page_sizes)} unique sizes found "
                            f"across {len(document.pages)} pages)"
                        ),
                        details={"unique_sizes": unique_sizes},
                    )
                )

        # LPDF_BOX_010: Page size doesn't match expected (T1-STR04)
        findings.extend(self._check_expected_page_size(document))

        # LPDF_BOX_005 / LPDF_BOX_006: Content proximity to trim/bleed edges
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

        # PR C Slot 3C: same proximity check against OUTLINED text. The
        # event loop above only sees TextRenderedEvents — for fixtures
        # whose ingredient panel is converted to vector paths the only
        # signal we have is page.detected_text_regions populated by the
        # shared OCR pass (PR #295). Reuse the same _check_content_
        # proximity helper; mark details.from_ocr so reviewers can tell
        # the two paths apart in the report.
        for page in document.pages:
            regions = getattr(page, "detected_text_regions", None)
            if not regions:
                continue
            trim_box, bleed_box = page_boxes.get(page.page_num, (None, None))
            for region in regions:
                bbox_obj = getattr(region, "bbox", None)
                if bbox_obj is None:
                    continue
                try:
                    bbox = (
                        float(bbox_obj.x0),
                        float(bbox_obj.y0),
                        float(bbox_obj.x1),
                        float(bbox_obj.y1),
                    )
                except (AttributeError, TypeError, ValueError):
                    continue
                for f in self._check_content_proximity(page.page_num, bbox, trim_box, bleed_box):
                    # Finding is frozen — rebuild via dataclasses.replace
                    # to add the OCR provenance flag.
                    import dataclasses

                    extra = dict(f.details or {})
                    extra["from_ocr"] = True
                    extra["region_text"] = (getattr(region, "text", None) or "")[:60]
                    findings.append(dataclasses.replace(f, details=extra))

        return findings

    def _check_content_proximity(  # skipcq: PY-R1000
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        trim_box: PdfBox | None,
        bleed_box: PdfBox | None,
    ) -> list[Finding]:
        """Check if content bbox is too close to trim edge or beyond bleed.

        WS-9: the emitted ``bbox`` / ``details`` report the
        *violation region* (the sliver of content that actually
        sits inside the safety margin or outside the bleed), not
        the whole content bbox. Content that only touches the
        offending zone on one edge now shows a narrow strip in
        the viewer instead of the entire object.
        """
        findings: list[Finding] = []

        # LPDF_BOX_005: Content within safety margin of trim edge.
        if trim_box is not None:
            violation = _safety_margin_violation(bbox, trim_box, self.safety_margin_pts)
            if violation is not None:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BOX_005",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Content within {self.safety_margin_pts:.1f}pt safety margin "
                            f"of trim edge on page {page_num}"
                        ),
                        page_num=page_num,
                        details={
                            "violation_bbox": list(violation),
                            "content_bbox": list(bbox),
                            "trim_box": trim_box.as_tuple(),
                            "safety_margin_pts": self.safety_margin_pts,
                        },
                        object_type="path",
                        bbox=violation,
                    )
                )

        # LPDF_BOX_006: Content extends beyond bleed box.
        if bleed_box is not None:
            violation = _beyond_bleed_violation(bbox, bleed_box)
            if violation is not None:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BOX_006",
                        severity=Severity.WARNING,
                        message=(f"Content extends beyond bleed box on page {page_num}"),
                        page_num=page_num,
                        details={
                            "violation_bbox": list(violation),
                            "content_bbox": list(bbox),
                            "bleed_box": bleed_box.as_tuple(),
                        },
                        object_type="path",
                        bbox=violation,
                    )
                )

        return findings

    def _check_expected_page_size(self, document: SemanticDocument) -> list[Finding]:
        """LPDF_BOX_010 — page dimensions don't match expected (T1-STR04).

        Gated: fires only when BOTH ``expected_page_width_mm`` and
        ``expected_page_height_mm`` are set on the profile. Silently
        no-ops otherwise, so profiles that don't declare an expected
        size never emit this finding.

        Compares the page's trim-box dimensions (or media-box fallback)
        in mm, accounting for rotation and UserUnit via the existing
        ``effective_width_mm`` / ``effective_height_mm`` properties.
        Tolerance defaults to 0.5mm — PitStop-compatible.

        Both orientations are accepted: (expected_width, expected_height)
        and (expected_height, expected_width). A tenant expecting a
        210x297 A4 portrait page shouldn't get a finding on a 297x210
        A4 landscape page of the same product.
        """
        if self.expected_page_width_mm is None or self.expected_page_height_mm is None:
            return []

        tol = self.expected_page_size_tolerance_mm
        exp_w = self.expected_page_width_mm
        exp_h = self.expected_page_height_mm

        findings: list[Finding] = []
        for page in document.pages:
            # Prefer trim box dimensions for product-size check — the
            # media box includes bleed + slug and isn't the product.
            ref = page.trim_box or page.media_box
            actual_w_pts = ref.x1 - ref.x0
            actual_h_pts = ref.y1 - ref.y0
            # Rotation-aware: rotated pages swap width/height.
            if page.rotate in (90, 270):
                actual_w_pts, actual_h_pts = actual_h_pts, actual_w_pts
            actual_w_mm = actual_w_pts * page.user_unit * 0.352778
            actual_h_mm = actual_h_pts * page.user_unit * 0.352778

            # Accept either orientation (portrait vs landscape of same product).
            matches_portrait = abs(actual_w_mm - exp_w) <= tol and abs(actual_h_mm - exp_h) <= tol
            matches_landscape = abs(actual_w_mm - exp_h) <= tol and abs(actual_h_mm - exp_w) <= tol
            if matches_portrait or matches_landscape:
                continue

            findings.append(
                Finding(
                    inspection_id="LPDF_BOX_010",
                    severity=Severity.WARNING,
                    message=(
                        f"Page {page.page_num} is {actual_w_mm:.2f}x{actual_h_mm:.2f}mm, "
                        f"expected {exp_w:.2f}x{exp_h:.2f}mm "
                        f"(+/- {tol}mm tolerance)"
                    ),
                    page_num=page.page_num,
                    details={
                        "actual_width_mm": round(actual_w_mm, 3),
                        "actual_height_mm": round(actual_h_mm, 3),
                        "expected_width_mm": exp_w,
                        "expected_height_mm": exp_h,
                        "tolerance_mm": tol,
                    },
                    iso_clause="ISO 15930-7:2010 6.2.4",
                )
            )
        return findings

    def _check_page(self, page: SemanticPage) -> list[Finding]:
        """Check a single page's geometry."""

        findings: list[Finding] = []

        # LPDF_BOX_001: Required boxes present
        if page.trim_box is None:
            findings.append(
                Finding(
                    inspection_id="LPDF_BOX_001",
                    severity=Severity.WARNING,
                    message=f"TrimBox missing on page {page.page_num}",
                    page_num=page.page_num,
                    details={"missing_box": "TrimBox"},
                    iso_clause="ISO 15930-7:2010 6.2.1",
                )
            )

        if geom_primitives.bleed_box(page) is None:
            findings.append(
                Finding(
                    inspection_id="LPDF_BOX_001",
                    severity=Severity.WARNING,
                    message=f"BleedBox missing on page {page.page_num}",
                    page_num=page.page_num,
                    details={"missing_box": "BleedBox"},
                    iso_clause="ISO 15930-7:2010 6.2.1",
                )
            )

        # LPDF_BOX_002: Box hierarchy validation
        findings.extend(self._check_hierarchy(page))

        # LPDF_BOX_003: Bleed distance
        if page.trim_box is not None and page.bleed_box is not None:
            findings.extend(
                self._check_bleed_distance(page.page_num, page.trim_box, page.bleed_box)
            )

        # LPDF_BOX_004: Empty page (no content stream)
        # On the codex ingest path content_stream is always b""; guard against false
        # positives by also checking structural evidence (fonts, images, annotations)
        # and codex content_ops (catches vector-only pages with no text or raster content).
        _codex = page.resources.get("codex_analysis") if isinstance(page.resources, dict) else None
        _has_codex_ops = bool(isinstance(_codex, dict) and _codex.get("content_ops"))
        if (
            not page.content_stream
            and not page.fonts
            and not page.images
            and not page.annotations
            and not _has_codex_ops
        ):
            findings.append(
                Finding(
                    inspection_id="LPDF_BOX_004",
                    severity=Severity.ADVISORY,
                    message=f"Page {page.page_num} has no content stream (empty page)",
                    page_num=page.page_num,
                    details={"page_num": page.page_num},
                )
            )

        # LPDF_BOX_007: UserUnit scaling detected
        user_unit = getattr(page, "user_unit", 1.0)
        if user_unit != 1.0:
            findings.append(
                Finding(
                    inspection_id="LPDF_BOX_007",
                    severity=Severity.WARNING,
                    message=(
                        f"Page {page.page_num} uses UserUnit={user_unit} "
                        f"(coordinates scaled — may cause output issues in some RIPs)"
                    ),
                    page_num=page.page_num,
                    details={"user_unit": user_unit},
                    iso_clause="ISO 32000-2:2020 14.11.2",
                )
            )

        # LPDF_BOX_008: Non-standard page orientation
        rotate = getattr(page, "rotate", 0) or 0
        if rotate not in (0, 90, 180, 270):
            findings.append(
                Finding(
                    inspection_id="LPDF_BOX_008",
                    severity=Severity.ADVISORY,
                    message=(f"Page {page.page_num} has non-standard rotation ({rotate}\u00b0)"),
                    page_num=page.page_num,
                    details={"rotate": rotate},
                    iso_clause="ISO 32000-2:2020 14.11.2",
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
                    inspection_id="LPDF_BOX_002",
                    severity=Severity.WARNING,
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
                    inspection_id="LPDF_BOX_002",
                    severity=Severity.WARNING,
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
                    inspection_id="LPDF_BOX_002",
                    severity=Severity.WARNING,
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
                    inspection_id="LPDF_BOX_003",
                    severity=Severity.WARNING,
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
                    # TrimBox rectangle: shows the cut line in Lens so
                    # the viewer can draw the bleed-gap outline on canvas.
                    bbox=trim_box.as_tuple(),
                    object_type="page",
                )
            )

        return findings
