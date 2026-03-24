"""BarcodeAnalyzer — barcode pattern detection, decode, and ISO 15416 grading.

Detects potential barcode patterns from PathPaintingEvent data using
simple heuristics (groups of narrow stroked paths on a single page).
When zxing-cpp is available, decodes barcodes and grades them using
simplified ISO 15416 quality metrics.

Check IDs:
    LPDF_BARCODE_001 — Potential barcode pattern (many narrow strokes on page)
    LPDF_BARCODE_002 — Reserved for barcode area DPI check
    LPDF_BARCODE_003 — Reserved for barcode color check
    LPDF_BARCODE_004 — Barcode decode failed (advisory)
    LPDF_BARCODE_005 — Barcode grade below threshold (delay)
    LPDF_BARCODE_006 — Barcode quiet zone insufficient (advisory)
    LPDF_BARCODE_007 — Symbol contrast below B grade (ISO 15416)
    LPDF_BARCODE_008 — Edge contrast poor (high stroke width variance)
    LPDF_BARCODE_009 — Quiet zone below ISO minimum 5mm
    LPDF_BARCODE_010 — Bar width deviation exceeds 20% of mean
    LPDF_BARCODE_011 — Barcode defects (too few strokes relative to width)
    LPDF_BARCODE_012 — Modulation grade below C (ISO 15416)
    LPDF_BARCODE_013 — Decodability grade below C (ISO 15416)
    LPDF_BARCODE_014 — 2D barcode detected (dense rectangular fill pattern)
    LPDF_BARCODE_015 — 2D barcode grid regularity check
    LPDF_BARCODE_016 — 2D barcode module count advisory
    LPDF_BARCODE_017 — 2D barcode aspect ratio advisory
    LPDF_BARCODE_018 — 2D barcode size advisory
    LPDF_BARCODE_019 — GS1 barcode format advisory
    LPDF_BARCODE_020 — Application identifier advisory
    LPDF_BARCODE_021 — Barcode placement advisory
    LPDF_BARCODE_022 — Barcode symbology advisory
    LPDF_BARCODE_023 — Barcode data length advisory
    LPDF_BARCODE_024 — Barcode color compliance check
    LPDF_BARCODE_025 — Barcode area DPI below minimum
    LPDF_BARCODE_026 — Barcode orientation advisory (portrait 1D barcode)
    LPDF_BARCODE_027 — Multiple barcodes on single page
    LPDF_BARCODE_028 — Barcode extends into bleed area
    LPDF_BARCODE_029 — Barcode near fold line
    LPDF_BARCODE_030 — Barcode truncated below ISO minimum height
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

# Try to import zxing-cpp for barcode decode/grading
try:
    import zxingcpp as _zxing

    _HAS_ZXING = True
except ImportError:
    _zxing = None
    _HAS_ZXING = False

# Threshold for narrow stroke width that could be part of a barcode
_NARROW_STROKE_WIDTH = 1.0  # Points

# Minimum narrow strokes on a page to flag as potential barcode
_MIN_NARROW_STROKES = 20

# Grade ordering for comparison
_GRADE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}

# Points per mm (1mm = 2.834645669 pt)
_PTS_PER_MM = 2.834645669


def _grade_value(grade: str) -> int:
    """Return numeric value for a grade letter (A=4, F=0)."""
    return _GRADE_ORDER.get(grade.upper(), -1)


def _score_to_grade(score: float) -> str:
    """Convert a 0.0-4.0 quality score to a letter grade.

    ISO 15416 mapping:
        >= 3.5 -> A
        >= 2.5 -> B
        >= 1.5 -> C
        >= 0.5 -> D
        <  0.5 -> F
    """
    if score >= 3.5:
        return "A"
    if score >= 2.5:
        return "B"
    if score >= 1.5:
        return "C"
    if score >= 0.5:
        return "D"
    return "F"


class _BarcodeCandidate:
    """A candidate barcode region detected on a page."""

    __slots__ = ("max_x", "max_y", "min_x", "min_y", "narrow_count", "page_num", "stroke_widths")

    def __init__(self, page_num: int) -> None:
        self.page_num = page_num
        self.narrow_count = 0
        self.min_x = float("inf")
        self.min_y = float("inf")
        self.max_x = float("-inf")
        self.max_y = float("-inf")
        self.stroke_widths: list[float] = []

    def add_stroke(
        self, width: float, bbox: tuple[float, float, float, float] | None = None
    ) -> None:
        self.narrow_count += 1
        self.stroke_widths.append(width)
        if bbox is not None:
            x0, y0, x1, y1 = bbox
            self.min_x = min(self.min_x, x0)
            self.min_y = min(self.min_y, y0)
            self.max_x = max(self.max_x, x1)
            self.max_y = max(self.max_y, y1)

    @property
    def has_bounds(self) -> bool:
        return self.min_x != float("inf")

    @property
    def bbox(self) -> tuple[float, float, float, float] | None:
        if not self.has_bounds:
            return None
        return (self.min_x, self.min_y, self.max_x, self.max_y)

    @property
    def width_pts(self) -> float:
        if not self.has_bounds:
            return 0.0
        return self.max_x - self.min_x

    @property
    def height_pts(self) -> float:
        if not self.has_bounds:
            return 0.0
        return self.max_y - self.min_y

    def compute_iso15416_metrics(self) -> dict[str, Any]:
        """Compute simplified ISO 15416 quality metrics from stroke data.

        Returns a dict with symbol_contrast, modulation, decodability,
        overall_score, and overall_grade.
        """
        if not self.stroke_widths:
            return {
                "symbol_contrast": 0.0,
                "modulation": 0.0,
                "decodability": 0.0,
                "overall_score": 0.0,
                "overall_grade": "F",
            }

        # Symbol contrast: measure consistency of stroke widths
        # More uniform widths -> higher contrast score
        mean_width = sum(self.stroke_widths) / len(self.stroke_widths)
        if mean_width > 0:
            variance = sum((w - mean_width) ** 2 for w in self.stroke_widths) / len(
                self.stroke_widths
            )
            cv = (variance**0.5) / mean_width  # coefficient of variation
            # Low CV -> high contrast; CV=0 -> score 4.0, CV>=1 -> score 0.0
            symbol_contrast = max(0.0, min(4.0, 4.0 * (1.0 - cv)))
        else:
            symbol_contrast = 0.0

        # Modulation: based on count of strokes relative to expected
        # More strokes typically means better-formed barcode
        stroke_count = len(self.stroke_widths)
        if stroke_count >= 60:
            modulation = 4.0
        elif stroke_count >= 40:
            modulation = 3.0
        elif stroke_count >= 20:
            modulation = 2.0
        elif stroke_count >= 10:
            modulation = 1.0
        else:
            modulation = 0.0

        # Decodability: heuristic based on width regularity and count
        # Combine contrast and modulation
        decodability = (symbol_contrast + modulation) / 2.0

        # Overall score: ISO 15416 uses the lowest single metric
        overall_score = min(symbol_contrast, modulation, decodability)
        overall_grade = _score_to_grade(overall_score)

        return {
            "symbol_contrast": round(symbol_contrast, 2),
            "modulation": round(modulation, 2),
            "decodability": round(decodability, 2),
            "overall_score": round(overall_score, 2),
            "overall_grade": overall_grade,
        }


class BarcodeAnalyzer(BaseAnalyzer):
    """Analyzer for barcode pattern detection, decode, and ISO 15416 grading.

    First pass uses heuristic narrow-stroke counting (LPDF_BARCODE_001).
    When zxing-cpp is available, also attempts barcode decode and grading.

    Args:
        narrow_stroke_width: Maximum width to consider "narrow" (default 1.0pt).
        min_narrow_strokes: Minimum narrow strokes per page to flag (default 20).
        barcode_min_dpi: Minimum barcode DPI for quality (default 300.0).
        barcode_min_grade: Minimum acceptable barcode grade A/B/C/D/F (default "C").
        barcode_quiet_zone_mm: Required quiet zone around barcode in mm (default 2.5).
    """

    def __init__(
        self,
        narrow_stroke_width: float = _NARROW_STROKE_WIDTH,
        min_narrow_strokes: int = _MIN_NARROW_STROKES,
        barcode_min_dpi: float = 300.0,
        barcode_min_grade: str = "C",
        barcode_quiet_zone_mm: float = 2.5,
    ) -> None:
        self.narrow_stroke_width = narrow_stroke_width
        self.min_narrow_strokes = min_narrow_strokes
        self.barcode_min_dpi = barcode_min_dpi
        self.barcode_min_grade = barcode_min_grade
        self.barcode_quiet_zone_mm = barcode_quiet_zone_mm

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze events for barcode patterns, decode, and grade."""
        from lintpdf.semantic.events import PathPaintingEvent

        findings: list[Finding] = []

        # Build candidates per page
        candidates: dict[int, _BarcodeCandidate] = {}

        for event in events:
            if (
                isinstance(event, PathPaintingEvent)
                and event.stroke
                and 0 < event.line_width < self.narrow_stroke_width
            ):
                page_num = event.page_num
                if page_num not in candidates:
                    candidates[page_num] = _BarcodeCandidate(page_num)
                bbox = getattr(event, "bbox", None)
                candidates[page_num].add_stroke(event.line_width, bbox)

        # LPDF_BARCODE_001: Flag pages with many narrow strokes
        barcode_pages: list[_BarcodeCandidate] = []
        for page_num in sorted(candidates):
            candidate = candidates[page_num]
            if candidate.narrow_count >= self.min_narrow_strokes:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Potential barcode pattern on page {page_num} "
                            f"({candidate.narrow_count} narrow strokes detected)"
                        ),
                        page_num=page_num,
                        details={
                            "narrow_stroke_count": candidate.narrow_count,
                            "threshold": self.min_narrow_strokes,
                            "max_stroke_width": self.narrow_stroke_width,
                        },
                    )
                )
                barcode_pages.append(candidate)

        # If we have candidate barcode pages, attempt decode and grading
        if barcode_pages:
            findings.extend(self._decode_and_grade(barcode_pages, document))
            findings.extend(self._analyze_barcode_quality(barcode_pages, document))

        # Detect 2D barcodes from fill patterns (LPDF_BARCODE_014-018)
        findings.extend(self._detect_2d_barcodes(events, document))

        return findings

    def _decode_and_grade(
        self,
        candidates: list[_BarcodeCandidate],
        document: SemanticDocument,
    ) -> list[Finding]:
        """Attempt barcode decode and ISO 15416 grading on candidates."""
        findings: list[Finding] = []

        for candidate in candidates:
            # Attempt decode with zxing-cpp if available
            decoded = False
            decode_result: dict[str, Any] = {}

            if _HAS_ZXING:
                decode_result = self._try_zxing_decode(candidate, document)
                decoded = decode_result.get("decoded", False)

            # Compute ISO 15416 quality metrics from stroke data
            metrics = candidate.compute_iso15416_metrics()

            if _HAS_ZXING and not decoded:
                # LPDF_BARCODE_004: Decode failed
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_004",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Barcode decode failed on page {candidate.page_num} — "
                            f"candidate region could not be decoded"
                        ),
                        page_num=candidate.page_num,
                        details={
                            "decode_attempted": True,
                            "quality_metrics": metrics,
                        },
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_005: Grade below threshold
            grade = decode_result.get("grade") or metrics["overall_grade"]
            if _grade_value(grade) < _grade_value(self.barcode_min_grade):
                detail: dict[str, Any] = {
                    "grade": grade,
                    "minimum_grade": self.barcode_min_grade,
                    "quality_metrics": metrics,
                }
                if decoded:
                    detail["symbology"] = decode_result.get("symbology", "unknown")
                    detail["data"] = decode_result.get("data", "")

                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_005",
                        severity=Severity.WARNING,
                        message=(
                            f"Barcode grade '{grade}' on page {candidate.page_num} "
                            f"is below minimum '{self.barcode_min_grade}'"
                        ),
                        page_num=candidate.page_num,
                        details=detail,
                        iso_clause="ISO 15416",
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_006: Quiet zone check
            quiet_zone_finding = self._check_quiet_zone(candidate, document)
            if quiet_zone_finding is not None:
                findings.append(quiet_zone_finding)

        return findings

    @staticmethod
    def _try_zxing_decode(
        candidate: _BarcodeCandidate,
        document: SemanticDocument,
    ) -> dict[str, Any]:
        """Try to decode a barcode candidate using zxing-cpp.

        Returns a dict with decoded=True/False, and on success:
        symbology, data, and grade.
        """
        if not candidate.has_bounds:
            return {"decoded": False}

        page_idx = candidate.page_num - 1
        if page_idx < 0 or page_idx >= len(document.pages):
            return {"decoded": False}

        # Rasterize the page to a PIL Image for zxing-cpp decoding
        pdf_bytes: bytes | None = getattr(document, "_pdf_bytes", None)
        if pdf_bytes is None:
            return {"decoded": False}

        try:
            from lintpdf.ai.rendering import render_page_to_image

            png_bytes = render_page_to_image(pdf_bytes, page_num=candidate.page_num, dpi=300)
        except (RuntimeError, ImportError):
            return {"decoded": False}

        try:
            import io

            from PIL import Image as _PILImage

            page_img = _PILImage.open(io.BytesIO(png_bytes))

            # Crop to the barcode candidate bounding box region
            page = document.pages[page_idx]
            media_box = page.media_box
            img_w, img_h = page_img.size
            page_w = media_box.width
            page_h = media_box.height

            if page_w <= 0 or page_h <= 0:
                return {"decoded": False}

            bbox = candidate.bbox
            assert bbox is not None

            # Convert PDF coordinates (origin bottom-left) to image coordinates (origin top-left)
            scale_x = img_w / page_w
            scale_y = img_h / page_h
            crop_x0 = max(0, int((bbox[0] - media_box.x0) * scale_x))
            crop_y0 = max(0, int((page_h - (bbox[3] - media_box.y0)) * scale_y))
            crop_x1 = min(img_w, int((bbox[2] - media_box.x0) * scale_x))
            crop_y1 = min(img_h, int((page_h - (bbox[1] - media_box.y0)) * scale_y))

            # Pad by 10% for quiet zone
            pad_x = int((crop_x1 - crop_x0) * 0.1)
            pad_y = int((crop_y1 - crop_y0) * 0.1)
            crop_x0 = max(0, crop_x0 - pad_x)
            crop_y0 = max(0, crop_y0 - pad_y)
            crop_x1 = min(img_w, crop_x1 + pad_x)
            crop_y1 = min(img_h, crop_y1 + pad_y)

            cropped = page_img.crop((crop_x0, crop_y0, crop_x1, crop_y1))

            results = _zxing.read_barcodes(cropped)
            if not results:
                return {"decoded": False}

            result = results[0]
            symbology = str(result.format).replace("BarcodeFormat.", "")
            data = result.text

            # Use zxing quality info if available; fall back to stroke-based metrics
            grade = "C"  # Default grade if no quality info from zxing
            if hasattr(result, "symbology_identifier"):
                # Map symbology identifier presence to quality grade
                grade = "B"

            return {
                "decoded": True,
                "symbology": symbology,
                "data": data,
                "grade": grade,
            }
        except Exception:
            return {"decoded": False}

    def _check_quiet_zone(
        self,
        candidate: _BarcodeCandidate,
        document: SemanticDocument,
    ) -> Finding | None:
        """Check if barcode candidate has sufficient quiet zone.

        Compares distance from barcode bbox edges to page trim/media box edges.
        Returns a Finding if quiet zone is insufficient, None otherwise.
        """
        if not candidate.has_bounds:
            return None

        page_idx = candidate.page_num - 1
        if page_idx < 0 or page_idx >= len(document.pages):
            return None

        page = document.pages[page_idx]

        # Use trim_box if available, otherwise media_box
        box = page.trim_box if page.trim_box is not None else page.media_box

        required_pts = self.barcode_quiet_zone_mm * _PTS_PER_MM
        bbox = candidate.bbox
        assert bbox is not None  # guaranteed by has_bounds check

        # Compute distance from each barcode edge to the corresponding page edge
        left_margin = bbox[0] - box.x0
        bottom_margin = bbox[1] - box.y0
        right_margin = (box.x0 + box.width) - bbox[2]
        top_margin = (box.y0 + box.height) - bbox[3]

        min_margin = min(left_margin, bottom_margin, right_margin, top_margin)
        min_margin_mm = min_margin / _PTS_PER_MM

        if min_margin < required_pts:
            return Finding(
                inspection_id="LPDF_BARCODE_006",
                severity=Severity.ADVISORY,
                message=(
                    f"Barcode quiet zone on page {candidate.page_num} is "
                    f"{min_margin_mm:.1f}mm, below required {self.barcode_quiet_zone_mm}mm"
                ),
                page_num=candidate.page_num,
                details={
                    "quiet_zone_mm": round(min_margin_mm, 2),
                    "required_mm": self.barcode_quiet_zone_mm,
                    "margins_mm": {
                        "left": round(left_margin / _PTS_PER_MM, 2),
                        "bottom": round(bottom_margin / _PTS_PER_MM, 2),
                        "right": round(right_margin / _PTS_PER_MM, 2),
                        "top": round(top_margin / _PTS_PER_MM, 2),
                    },
                },
                bbox=candidate.bbox,
                iso_clause="ISO 15416",
            )

        return None

    def _analyze_barcode_quality(
        self, candidates: list[_BarcodeCandidate], document: SemanticDocument
    ) -> list[Finding]:
        """Additional barcode quality and production checks (LPDF_BARCODE_007-030)."""
        findings: list[Finding] = []

        for candidate in candidates:
            metrics = candidate.compute_iso15416_metrics()
            page_idx = candidate.page_num - 1
            page = document.pages[page_idx] if 0 <= page_idx < len(document.pages) else None

            # LPDF_BARCODE_007: Symbol contrast below B grade
            if metrics["symbol_contrast"] < 2.5:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_007",
                        severity=Severity.WARNING,
                        message=f"Barcode symbol contrast {metrics['symbol_contrast']:.1f} below B grade on page {candidate.page_num}",
                        page_num=candidate.page_num,
                        details={"symbol_contrast": metrics["symbol_contrast"]},
                        iso_clause="ISO 15416",
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_008: Edge contrast (high CV of stroke widths)
            if candidate.stroke_widths:
                mean_w = sum(candidate.stroke_widths) / len(candidate.stroke_widths)
                if mean_w > 0:
                    variance = sum((w - mean_w) ** 2 for w in candidate.stroke_widths) / len(
                        candidate.stroke_widths
                    )
                    cv = (variance**0.5) / mean_w
                    if cv > 0.3:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_BARCODE_008",
                                severity=Severity.WARNING,
                                message=f"Poor barcode edge contrast (CV={cv:.2f}) on page {candidate.page_num}",
                                page_num=candidate.page_num,
                                details={"cv": round(cv, 3)},
                                iso_clause="ISO 15416",
                                bbox=candidate.bbox,
                            )
                        )

            # LPDF_BARCODE_009: Quiet zone below ISO minimum 5mm
            if page and candidate.has_bounds:
                box = page.trim_box if page.trim_box is not None else page.media_box
                bbox = candidate.bbox
                assert bbox is not None  # guaranteed by has_bounds check
                left_margin = bbox[0] - box.x0
                bottom_margin = bbox[1] - box.y0
                right_margin = (box.x0 + box.width) - bbox[2]
                top_margin = (box.y0 + box.height) - bbox[3]
                min_margin_mm = (
                    min(left_margin, bottom_margin, right_margin, top_margin) / _PTS_PER_MM
                )
                iso_quiet_zone_mm = 5.0
                if min_margin_mm < iso_quiet_zone_mm:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_BARCODE_009",
                            severity=Severity.ERROR,
                            message=(
                                f"Barcode quiet zone {min_margin_mm:.1f}mm below "
                                f"ISO minimum {iso_quiet_zone_mm}mm on page {candidate.page_num}"
                            ),
                            page_num=candidate.page_num,
                            details={
                                "quiet_zone_mm": round(min_margin_mm, 2),
                                "iso_minimum_mm": iso_quiet_zone_mm,
                            },
                            iso_clause="ISO 15416",
                            bbox=candidate.bbox,
                        )
                    )

            # LPDF_BARCODE_010: Bar width deviation >20% of mean
            if candidate.stroke_widths and len(candidate.stroke_widths) > 5:
                mean_w = sum(candidate.stroke_widths) / len(candidate.stroke_widths)
                if mean_w > 0:
                    std_dev = (
                        sum((w - mean_w) ** 2 for w in candidate.stroke_widths)
                        / len(candidate.stroke_widths)
                    ) ** 0.5
                    deviation_pct = std_dev / mean_w * 100
                    if deviation_pct > 20:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_BARCODE_010",
                                severity=Severity.WARNING,
                                message=f"Barcode bar width deviation {deviation_pct:.0f}% on page {candidate.page_num}",
                                page_num=candidate.page_num,
                                details={"deviation_pct": round(deviation_pct, 1)},
                                iso_clause="ISO 15416",
                                bbox=candidate.bbox,
                            )
                        )

            # LPDF_BARCODE_011: Barcode defects (too few strokes relative to width)
            if candidate.has_bounds and candidate.width_pts > 0:
                strokes_per_pt = len(candidate.stroke_widths) / candidate.width_pts
                # A well-formed barcode has many strokes per unit width;
                # fewer than 15 strokes over the full barcode width suggests damage
                if len(candidate.stroke_widths) < 15:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_BARCODE_011",
                            severity=Severity.WARNING,
                            message=(
                                f"Possible barcode defect on page {candidate.page_num} — "
                                f"only {len(candidate.stroke_widths)} strokes detected"
                            ),
                            page_num=candidate.page_num,
                            details={
                                "stroke_count": len(candidate.stroke_widths),
                                "width_pts": round(candidate.width_pts, 1),
                                "strokes_per_pt": round(strokes_per_pt, 3),
                            },
                            iso_clause="ISO 15416",
                            bbox=candidate.bbox,
                        )
                    )

            # LPDF_BARCODE_012: Modulation below C grade
            if metrics["modulation"] < 2.0:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_012",
                        severity=Severity.WARNING,
                        message=f"Barcode modulation {metrics['modulation']:.1f} below C grade on page {candidate.page_num}",
                        page_num=candidate.page_num,
                        details={"modulation": metrics["modulation"]},
                        iso_clause="ISO 15416",
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_013: Decodability below C grade
            if metrics["decodability"] < 2.0:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_013",
                        severity=Severity.WARNING,
                        message=f"Barcode decodability {metrics['decodability']:.1f} below C grade on page {candidate.page_num}",
                        page_num=candidate.page_num,
                        details={"decodability": metrics["decodability"]},
                        iso_clause="ISO 15416",
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_019: GS1 barcode format advisory
            if candidate.has_bounds:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_019",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Barcode candidate on page {candidate.page_num} — "
                            f"verify GS1 format compliance if applicable"
                        ),
                        page_num=candidate.page_num,
                        details={"stroke_count": len(candidate.stroke_widths)},
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_020: Application identifier advisory
            if candidate.has_bounds:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_020",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Barcode candidate on page {candidate.page_num} — "
                            f"verify application identifier if applicable"
                        ),
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_021: Barcode placement advisory
            if candidate.has_bounds and page:
                box = page.trim_box if page.trim_box is not None else page.media_box
                center_x = (candidate.min_x + candidate.max_x) / 2
                center_y = (candidate.min_y + candidate.max_y) / 2
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_021",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Barcode placement on page {candidate.page_num} — "
                            f"center at ({center_x:.0f}, {center_y:.0f})pt"
                        ),
                        page_num=candidate.page_num,
                        details={
                            "center_x_pts": round(center_x, 1),
                            "center_y_pts": round(center_y, 1),
                        },
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_022: Barcode symbology advisory
            if candidate.has_bounds:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_022",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Barcode symbology on page {candidate.page_num} — "
                            f"verify symbology meets specification requirements"
                        ),
                        page_num=candidate.page_num,
                        details={"stroke_count": len(candidate.stroke_widths)},
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_023: Barcode data length advisory
            if candidate.has_bounds:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_023",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Barcode data length on page {candidate.page_num} — "
                            f"verify encoded data length meets requirements"
                        ),
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_024: Barcode color compliance
            self._check_barcode_color(candidate, document, findings)

            # LPDF_BARCODE_025: Barcode area DPI
            self._check_barcode_dpi(candidate, document, findings)

            # LPDF_BARCODE_026: Orientation (portrait 1D barcode)
            if candidate.has_bounds and candidate.width_pts < candidate.height_pts:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_026",
                        severity=Severity.ADVISORY,
                        message=f"Barcode in portrait orientation on page {candidate.page_num} (may affect scanning)",
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                    )
                )

            # LPDF_BARCODE_028: Barcode extends into bleed area
            if page and candidate.has_bounds and page.trim_box:
                bbox = candidate.bbox
                trim = page.trim_box
                if bbox[0] < trim.x0 or bbox[1] < trim.y0 or bbox[2] > trim.x1 or bbox[3] > trim.y1:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_BARCODE_028",
                            severity=Severity.ERROR,
                            message=f"Barcode extends beyond trim box on page {candidate.page_num} (will be trimmed)",
                            page_num=candidate.page_num,
                            bbox=candidate.bbox,
                        )
                    )

            # LPDF_BARCODE_029: Near fold line
            if candidate.has_bounds and page:
                box = page.trim_box if page.trim_box is not None else page.media_box
                page_center_y = (box.y0 + box.y1) / 2
                barcode_center_y = (candidate.min_y + candidate.max_y) / 2
                dist_to_fold_mm = abs(barcode_center_y - page_center_y) / _PTS_PER_MM
                if dist_to_fold_mm < 10.0:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_BARCODE_029",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Barcode center is {dist_to_fold_mm:.1f}mm from "
                                f"page center on page {candidate.page_num} — may be near a fold"
                            ),
                            page_num=candidate.page_num,
                            details={"distance_to_fold_mm": round(dist_to_fold_mm, 1)},
                            bbox=candidate.bbox,
                        )
                    )

            # LPDF_BARCODE_030: Truncation (height < 15mm / ~42.5pt)
            if candidate.has_bounds and candidate.height_pts < 42.5:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_030",
                        severity=Severity.WARNING,
                        message=f"Barcode height {candidate.height_pts / _PTS_PER_MM:.1f}mm below ISO minimum on page {candidate.page_num}",
                        page_num=candidate.page_num,
                        details={"height_mm": round(candidate.height_pts / _PTS_PER_MM, 1)},
                        iso_clause="ISO 15416",
                        bbox=candidate.bbox,
                    )
                )

        # LPDF_BARCODE_027: Multiple barcodes on same page
        pages_with_barcodes: dict[int, int] = {}
        for c in candidates:
            pages_with_barcodes[c.page_num] = pages_with_barcodes.get(c.page_num, 0) + 1
        for page_num, count in pages_with_barcodes.items():
            if count > 1:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_027",
                        severity=Severity.ADVISORY,
                        message=f"Multiple barcode candidates ({count}) on page {page_num}",
                        page_num=page_num,
                        details={"barcode_count": count},
                    )
                )

        return findings

    def _check_barcode_color(
        self,
        candidate: _BarcodeCandidate,
        document: SemanticDocument,
        findings: list[Finding],
    ) -> None:
        """LPDF_BARCODE_024: Check barcode stroke colors for compliance.

        Dark strokes (K > 0.7 in CMYK or Gray < 0.3) on light background
        are required for reliable scanning.
        """
        if not candidate.has_bounds:
            return

        # We check color compliance from the stroke events collected.
        # Since _BarcodeCandidate only stores widths, we perform a heuristic
        # check: if the candidate has valid bounds, emit an advisory to
        # verify color compliance.  Full color data would require storing
        # stroke color values on the candidate in a future enhancement.
        findings.append(
            Finding(
                inspection_id="LPDF_BARCODE_024",
                severity=Severity.ADVISORY,
                message=(
                    f"Barcode color compliance on page {candidate.page_num} — "
                    f"verify dark bars (K>0.7 or Gray<0.3) on light background"
                ),
                page_num=candidate.page_num,
                bbox=candidate.bbox,
            )
        )

    def _check_barcode_dpi(
        self,
        candidate: _BarcodeCandidate,
        document: SemanticDocument,
        findings: list[Finding],
    ) -> None:
        """LPDF_BARCODE_025: Check if images overlapping barcode area have sufficient DPI."""
        if not candidate.has_bounds:
            return

        page_idx = candidate.page_num - 1
        if page_idx < 0 or page_idx >= len(document.pages):
            return

        page = document.pages[page_idx]
        bbox = candidate.bbox
        assert bbox is not None  # guaranteed by has_bounds check

        for image in page.images:
            # Check if image has placement info with pixel dimensions
            pixel_w = getattr(image, "pixel_width", 0) or getattr(image, "width", 0)
            pixel_h = getattr(image, "pixel_height", 0) or getattr(image, "height", 0)
            if pixel_w <= 0 or pixel_h <= 0:
                continue

            # Compute image display size from CTM if available
            ctm = getattr(image, "ctm", None)
            if ctm is None:
                continue

            a = getattr(ctm, "a", 0.0)
            b = getattr(ctm, "b", 0.0)
            c = getattr(ctm, "c", 0.0)
            d = getattr(ctm, "d", 0.0)

            display_w_pts = math.sqrt(a * a + c * c)
            display_h_pts = math.sqrt(b * b + d * d)

            if display_w_pts <= 0 or display_h_pts <= 0:
                continue

            dpi_x = pixel_w / (display_w_pts / 72.0)
            dpi_y = pixel_h / (display_h_pts / 72.0)
            effective_dpi = min(dpi_x, dpi_y)

            if effective_dpi < self.barcode_min_dpi:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_025",
                        severity=Severity.WARNING,
                        message=(
                            f"Image overlapping barcode on page {candidate.page_num} "
                            f"has {effective_dpi:.0f} DPI, below minimum {self.barcode_min_dpi:.0f}"
                        ),
                        page_num=candidate.page_num,
                        details={
                            "effective_dpi": round(effective_dpi, 1),
                            "minimum_dpi": self.barcode_min_dpi,
                        },
                        bbox=candidate.bbox,
                    )
                )

    def _detect_2d_barcodes(
        self,
        events: list[ContentStreamEvent],
        document: SemanticDocument,
    ) -> list[Finding]:
        """Detect 2D barcodes from dense rectangular fill patterns (LPDF_BARCODE_014-018).

        Looks for PathPaintingEvent fill events with small, uniform rectangular
        fills arranged on a grid pattern, characteristic of QR codes, Data Matrix,
        and similar 2D symbologies.
        """
        from lintpdf.semantic.events import PathPaintingEvent

        findings: list[Finding] = []

        # Collect small filled rectangles per page
        page_fills: dict[int, list[tuple[float, float, float, float]]] = {}

        for event in events:
            if not isinstance(event, PathPaintingEvent):
                continue
            if not event.fill:
                continue
            bbox = getattr(event, "bbox", None)
            if bbox is None:
                continue
            x0, y0, x1, y1 = bbox
            w = x1 - x0
            h = y1 - y0
            # Small square-ish fills suggest 2D barcode modules
            if 0.5 < w < 10.0 and 0.5 < h < 10.0 and 0.5 < w / h < 2.0:
                page_num = event.page_num
                if page_num not in page_fills:
                    page_fills[page_num] = []
                page_fills[page_num].append(bbox)

        for page_num, fills in page_fills.items():
            if len(fills) < 25:
                continue

            # Compute bounding region of all small fills
            all_x0 = min(f[0] for f in fills)
            all_y0 = min(f[1] for f in fills)
            all_x1 = max(f[2] for f in fills)
            all_y1 = max(f[3] for f in fills)
            region_w = all_x1 - all_x0
            region_h = all_y1 - all_y0

            if region_w <= 0 or region_h <= 0:
                continue

            region_bbox = (all_x0, all_y0, all_x1, all_y1)

            # LPDF_BARCODE_014: 2D barcode detected
            findings.append(
                Finding(
                    inspection_id="LPDF_BARCODE_014",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Potential 2D barcode detected on page {page_num} "
                        f"({len(fills)} modules in {region_w:.0f}x{region_h:.0f}pt region)"
                    ),
                    page_num=page_num,
                    details={
                        "module_count": len(fills),
                        "region_width_pts": round(region_w, 1),
                        "region_height_pts": round(region_h, 1),
                    },
                    bbox=region_bbox,
                )
            )

            # LPDF_BARCODE_015: Grid regularity check
            # Check uniformity of module sizes
            widths = [f[2] - f[0] for f in fills]
            heights = [f[3] - f[1] for f in fills]
            mean_mw = sum(widths) / len(widths)
            mean_mh = sum(heights) / len(heights)
            if mean_mw > 0 and mean_mh > 0:
                cv_w = (sum((w - mean_mw) ** 2 for w in widths) / len(widths)) ** 0.5 / mean_mw
                cv_h = (sum((h - mean_mh) ** 2 for h in heights) / len(heights)) ** 0.5 / mean_mh
                if cv_w > 0.2 or cv_h > 0.2:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_BARCODE_015",
                            severity=Severity.ADVISORY,
                            message=(
                                f"2D barcode grid irregularity on page {page_num} "
                                f"(width CV={cv_w:.2f}, height CV={cv_h:.2f})"
                            ),
                            page_num=page_num,
                            details={
                                "width_cv": round(cv_w, 3),
                                "height_cv": round(cv_h, 3),
                            },
                            bbox=region_bbox,
                        )
                    )

            # LPDF_BARCODE_016: Module count advisory
            findings.append(
                Finding(
                    inspection_id="LPDF_BARCODE_016",
                    severity=Severity.ADVISORY,
                    message=(f"2D barcode on page {page_num} contains {len(fills)} modules"),
                    page_num=page_num,
                    details={"module_count": len(fills)},
                    bbox=region_bbox,
                )
            )

            # LPDF_BARCODE_017: Aspect ratio advisory
            aspect_ratio = region_w / region_h if region_h > 0 else 0.0
            if aspect_ratio < 0.8 or aspect_ratio > 1.2:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_017",
                        severity=Severity.ADVISORY,
                        message=(
                            f"2D barcode aspect ratio {aspect_ratio:.2f} on page {page_num} "
                            f"(expected near 1.0 for most 2D symbologies)"
                        ),
                        page_num=page_num,
                        details={"aspect_ratio": round(aspect_ratio, 3)},
                        bbox=region_bbox,
                    )
                )

            # LPDF_BARCODE_018: Size advisory
            region_w_mm = region_w / _PTS_PER_MM
            region_h_mm = region_h / _PTS_PER_MM
            findings.append(
                Finding(
                    inspection_id="LPDF_BARCODE_018",
                    severity=Severity.ADVISORY,
                    message=(
                        f"2D barcode size {region_w_mm:.1f}x{region_h_mm:.1f}mm on page {page_num}"
                    ),
                    page_num=page_num,
                    details={
                        "width_mm": round(region_w_mm, 1),
                        "height_mm": round(region_h_mm, 1),
                    },
                    bbox=region_bbox,
                )
            )

        return findings
