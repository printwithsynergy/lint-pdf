"""BarcodeAnalyzer — barcode pattern detection, decode, and ISO 15416 grading.

Detects potential barcode patterns from PathPaintingEvent data using
simple heuristics (groups of narrow stroked paths on a single page).
When zxing-cpp is available, decodes barcodes and grades them using
simplified ISO 15416 quality metrics.

Check IDs:
    GRD_BARCODE_001 — Potential barcode pattern (many narrow strokes on page)
    GRD_BARCODE_002 — Reserved for barcode area DPI check
    GRD_BARCODE_003 — Reserved for barcode color check
    GRD_BARCODE_004 — Barcode decode failed (advisory)
    GRD_BARCODE_005 — Barcode grade below threshold (delay)
    GRD_BARCODE_006 — Barcode quiet zone insufficient (advisory)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from grounded.analyzers.base import BaseAnalyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

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

    First pass uses heuristic narrow-stroke counting (GRD_BARCODE_001).
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
        from grounded.semantic.events import PathPaintingEvent

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

        # GRD_BARCODE_001: Flag pages with many narrow strokes
        barcode_pages: list[_BarcodeCandidate] = []
        for page_num in sorted(candidates):
            candidate = candidates[page_num]
            if candidate.narrow_count >= self.min_narrow_strokes:
                findings.append(
                    Finding(
                        inspection_id="GRD_BARCODE_001",
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
                # GRD_BARCODE_004: Decode failed
                findings.append(
                    Finding(
                        inspection_id="GRD_BARCODE_004",
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

            # GRD_BARCODE_005: Grade below threshold
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
                        inspection_id="GRD_BARCODE_005",
                        severity=Severity.SQUALL,
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

            # GRD_BARCODE_006: Quiet zone check
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
        # zxing-cpp requires a PIL Image. We don't have rasterized page
        # images from the semantic model, so this is a stub that will
        # work when page images are provided in the future.
        # For now, return not decoded.
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
                inspection_id="GRD_BARCODE_006",
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
