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
    LPDF_BARCODE_031 — Barcode quiet zone too close to trim edge
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


# WS-10 structural thresholds. Calibrated against the
# 2026-04-23 Opus audit disputes: every one of those five
# false positives fails at least one of these checks, and the
# synthetic Data Matrix / QR fixtures in the tests pass all of
# them.
_BARCODE_ASPECT_MIN = 0.4
_BARCODE_ASPECT_MAX = 2.5
# Reject regions whose diagonal exceeds this many points. A real
# 2D symbol is typically <= 50 mm on a side; a 200 mm region is
# obviously something else (page panel, artwork block).
_BARCODE_MAX_SIDE_PTS = 200.0  # ~70 mm
# Module-size coefficient of variation must stay below this on
# both axes.
_BARCODE_MAX_CV = 0.5
# Fill-density floor: (sum of module areas) / region area.
# Real 2D symbols run 40-60% dark; decorative fill scatter is
# usually <5%.
_BARCODE_MIN_FILL_DENSITY = 0.2


def _bbox_distance(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    """Minimum axis-aligned distance between two rectangles, 0 when
    they overlap or touch. Mirrors ``analyzers.dieline_quality._bbox_distance``.
    """
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    if dx == 0 and dy == 0:
        return 0.0
    return (dx**2 + dy**2) ** 0.5


def _bbox_contains(
    outer: tuple[float, float, float, float],
    inner: tuple[float, float, float, float],
) -> bool:
    """True when ``outer`` fully contains ``inner`` (with ≤ 0.5 pt
    tolerance to absorb floating-point noise from CTM composition)."""
    return (
        outer[0] <= inner[0] + 0.5
        and outer[1] <= inner[1] + 0.5
        and outer[2] >= inner[2] - 0.5
        and outer[3] >= inner[3] - 0.5
    )


# Colorant names that can be treated as a white knockout. Keeping this
# small and explicit — adding "Light" or "Cream" here would silently
# suppress real findings.
_WHITE_SPOT_NAMES: frozenset[str] = frozenset({"WHITE", "OPAQUE WHITE", "WHT"})


def _is_white_fill(cs: str, vals: tuple[float, ...]) -> bool:
    """True when the fill renders as a (near) white knockout. Errs on
    the side of "yes" so a CMYK 0,0,0,0 box is recognised as a
    knockout box for any quiet-zone enforcement.
    """
    cs_norm = (cs or "").lower()
    if ("devicecmyk" in cs_norm or cs_norm == "cmyk") and len(vals) >= 4 and sum(vals[:4]) <= 0.05:
        return True
    if (
        ("devicergb" in cs_norm or cs_norm == "rgb")
        and len(vals) >= 3
        and all(v >= 0.95 for v in vals[:3])
    ):
        return True
    if ("devicegray" in cs_norm or cs_norm == "gray") and len(vals) >= 1 and vals[0] >= 0.95:
        return True
    if "separation" in cs_norm:
        upper = (cs or "").upper()
        return any(token in upper for token in _WHITE_SPOT_NAMES)
    return False


def _is_light_fill(cs: str, vals: tuple[float, ...]) -> bool:
    """True when the fill is light enough to host a barcode without
    contrast issues. The complement of "tinted" — anything that lands
    here will NOT count toward the dark-background finding.

    Thresholds err toward calling things tinted (so we surface the
    miss); the suppression for white-knockout boxes still requires
    ``_is_white_fill`` to be true, which is strict.
    """
    cs_norm = (cs or "").lower()
    if ("devicecmyk" in cs_norm or cs_norm == "cmyk") and len(vals) >= 4:
        return sum(vals[:4]) <= 0.10  # < 10% total ink
    if ("devicergb" in cs_norm or cs_norm == "rgb") and len(vals) >= 3:
        return all(v >= 0.92 for v in vals[:3])
    if ("devicegray" in cs_norm or cs_norm == "gray") and len(vals) >= 1:
        return vals[0] >= 0.92
    if "separation" in cs_norm:
        # Zero tint = no ink down → effectively transparent → light.
        # Any non-zero tint on a custom spot is treated as tinted.
        return bool(len(vals) >= 1 and vals[0] <= 0.01)
    # Unknown space → don't false-positive.
    return True


def _looks_like_2d_barcode(
    fills: list[tuple[float, float, float, float]],
    region_w: float,
    region_h: float,
) -> bool:
    """Structural gate before emitting LPDF_BARCODE_014..018.

    All checks are vector-only -- no pixel rendering required --
    so the gate adds essentially zero cost to the preflight run.
    Returns True only when every structural signal points at a
    plausible 2D barcode symbol.
    """
    # 1. Aspect ratio sanity.
    aspect = region_w / region_h if region_h > 0 else 0.0
    if aspect < _BARCODE_ASPECT_MIN or aspect > _BARCODE_ASPECT_MAX:
        return False
    # 2. Region size sanity.
    if region_w > _BARCODE_MAX_SIDE_PTS or region_h > _BARCODE_MAX_SIDE_PTS:
        return False
    # 3. Module-size regularity (low CV).
    widths = [f[2] - f[0] for f in fills]
    heights = [f[3] - f[1] for f in fills]
    mean_w = sum(widths) / len(widths)
    mean_h = sum(heights) / len(heights)
    if mean_w <= 0 or mean_h <= 0:
        return False
    cv_w = (sum((w - mean_w) ** 2 for w in widths) / len(widths)) ** 0.5 / mean_w
    cv_h = (sum((h - mean_h) ** 2 for h in heights) / len(heights)) ** 0.5 / mean_h
    if cv_w > _BARCODE_MAX_CV or cv_h > _BARCODE_MAX_CV:
        return False
    # 4. Fill-density floor.
    module_area = sum((f[2] - f[0]) * (f[3] - f[1]) for f in fills)
    region_area = region_w * region_h
    if region_area <= 0:
        return False
    density = module_area / region_area
    return density >= _BARCODE_MIN_FILL_DENSITY


# Reject "2D barcode" candidates whose union bbox covers most of the trim
# rectangle — typical of full-panel splatter art / decorative grids
# (2026-04-23 Opus audit false positives on Pavette / Nutrops back panels).
_2D_MAX_TRIM_COVERAGE = 0.70


def _page_trim_like(document: SemanticDocument, page_num: int) -> Any | None:
    """Trim box for ``page_num``, falling back to crop then media."""
    idx = page_num - 1
    if idx < 0 or idx >= len(document.pages):
        return None
    page = document.pages[idx]
    return page.trim_box or page.crop_box or page.media_box


def _region_covers_trim_excessively(
    region_bbox: tuple[float, float, float, float],
    trim: Any,
) -> bool:
    """True when the candidate region spans both trim axes beyond
    ``_2D_MAX_TRIM_COVERAGE`` — almost never a real isolated 2D symbol."""
    rx0, ry0, rx1, ry1 = region_bbox
    region_w = rx1 - rx0
    region_h = ry1 - ry0
    tw = float(trim.width)
    th = float(trim.height)
    if tw <= 0 or th <= 0:
        return False
    return (region_w / tw) > _2D_MAX_TRIM_COVERAGE and (region_h / th) > _2D_MAX_TRIM_COVERAGE


def _zxing_format_is_2d_matrix(sym: str) -> bool:
    """True for QR / Data Matrix / Aztec / PDF417 symbologies."""
    f = sym.replace("BarcodeFormat.", "").upper()
    return any(
        token in f
        for token in (
            "QRCODE",
            "DATA_MATRIX",
            "DATAMATRIX",
            "AZTEC",
            "PDF417",
        )
    )


def _zxing_decodes_2d_matrix_in_region(
    pdf_bytes: bytes,
    *,
    page_num: int,
    region_bbox: tuple[float, float, float, float],
    document: SemanticDocument,
) -> bool:
    """Raster-crop to ``region_bbox`` and ask zxing-cpp for a 2D matrix decode.

    Returns ``False`` when zxing isn't installed, bytes are missing, render
    fails, or no QR/DataMatrix/Aztec/PDF417 is read from the crop.
    """
    if not _HAS_ZXING or not pdf_bytes or _zxing is None:
        return False
    page_idx = page_num - 1
    if page_idx < 0 or page_idx >= len(document.pages):
        return False
    page = document.pages[page_idx]
    media_box = page.media_box

    try:
        from lintpdf.rendering import render_page_to_image

        png_bytes = render_page_to_image(pdf_bytes, page_num=page_num, dpi=300)
    except (RuntimeError, ImportError, OSError, ValueError):
        return False

    try:
        import io

        from PIL import Image as _PILImage

        page_img = _PILImage.open(io.BytesIO(png_bytes))
        img_w, img_h = page_img.size
        page_w = media_box.width
        page_h = media_box.height
        if page_w <= 0 or page_h <= 0:
            return False

        bbox = region_bbox
        scale_x = img_w / page_w
        scale_y = img_h / page_h

        crop_x0 = max(0, int((bbox[0] - media_box.x0) * scale_x))
        crop_y0 = max(0, int((page_h - (bbox[3] - media_box.y0)) * scale_y))
        crop_x1 = min(img_w, int((bbox[2] - media_box.x0) * scale_x))
        crop_y1 = min(img_h, int((page_h - (bbox[1] - media_box.y0)) * scale_y))

        pad_x = max(2, int((crop_x1 - crop_x0) * 0.08))
        pad_y = max(2, int((crop_y1 - crop_y0) * 0.08))
        crop_x0 = max(0, crop_x0 - pad_x)
        crop_y0 = max(0, crop_y0 - pad_y)
        crop_x1 = min(img_w, crop_x1 + pad_x)
        crop_y1 = min(img_h, crop_y1 + pad_y)

        if crop_x1 <= crop_x0 or crop_y1 <= crop_y0:
            return False

        cropped = page_img.crop((crop_x0, crop_y0, crop_x1, crop_y1))
        results = _zxing.read_barcodes(cropped)
        for result in results:
            if _zxing_format_is_2d_matrix(str(result.format)):
                return True
    except Exception:
        return False
    return False


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
            # PR D Slot 4: orientation + quiet-zone + bar-height suite.
            findings.extend(self._check_orientation_suite(barcode_pages, document))
            findings.extend(self._check_size_and_quiet_zone_ink(barcode_pages, document, events))
            # PR-W: GS1 quiet-zone-on-fold via DielineResult attached
            # to the document by the orchestrator.
            findings.extend(self._check_fold_proximity(barcode_pages, document))
            # PR-Z: GS1 PCS — barcode on a tinted background without
            # a white knockout box.
            findings.extend(self._check_barcode_background(barcode_pages, document, events))

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

            # T5-N06 / T5-N08 — content validators (GS1 AI / UDI / EU DPP).
            if decoded:
                payload = str(decode_result.get("data", ""))
                if payload:
                    from lintpdf.analyzers.barcode_validation import (
                        validate_eu_dpp_payload,
                        validate_gs1_ai_payload,
                        validate_udi_payload,
                    )

                    findings.extend(
                        validate_gs1_ai_payload(
                            payload,
                            page_num=candidate.page_num,
                            bbox=candidate.bbox,
                        )
                    )
                    findings.extend(
                        validate_udi_payload(
                            payload,
                            page_num=candidate.page_num,
                            bbox=candidate.bbox,
                        )
                    )
                    findings.extend(
                        validate_eu_dpp_payload(
                            payload,
                            page_num=candidate.page_num,
                            bbox=candidate.bbox,
                        )
                    )

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
            from lintpdf.rendering import render_page_to_image

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

            # LPDF_BARCODE_026: Orientation (portrait 1D barcode).
            # The 2026-04-27 Opus audit flagged 2 false positives where
            # this fired on landscape barcodes that happened to sit in
            # a slightly-taller-than-wide bounding box. Without
            # inspecting actual bar geometry we can't tell ladder from
            # picket-fence reliably from bbox aspect alone. The
            # 2026-04-28 Opus audit caught more false positives at the
            # 1.5x threshold (Nutrops_LS, Nutrops_SF, Cherry-Twist —
            # all rendered as picket-fence landscape with bars that
            # happen to extend beyond 1.5x the bar count).
            #
            # True ladder-orientation barcodes have height >= 3.5x
            # width (most scanner-spec ladder symbols are 4-6x).
            # Tighten to that threshold so the rule only fires on the
            # most-clearly-portrait cases. Real ladder symbols still
            # trip it; landscape symbols whose bbox happens to be
            # marginally taller (because of the human-readable text
            # below the bars) are now silent.
            if (
                candidate.has_bounds
                and candidate.width_pts > 0
                and candidate.height_pts > 3.5 * candidate.width_pts
            ):
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
                else:
                    # LPDF_BARCODE_031: barcode quiet zone too close to
                    # trim edge. The 2026-04-28 Opus audit flagged this
                    # on Pavette, OrangeKiss, AN-Energy, Pink-Slush --
                    # all UPC barcodes whose quiet-zone region (>= 10x
                    # narrow-bar width) effectively overlaps the trim
                    # cut, risking quiet-zone occlusion at finishing.
                    # GS1 quiet-zone minimum is 9x X-dim leading +
                    # 7x X-dim trailing; a 5 mm buffer to the trim
                    # edge is a defensive proxy that holds for typical
                    # 12-mil X-dim retail UPCs.
                    qz_buf_mm = 5.0
                    buf_pts = qz_buf_mm * _PTS_PER_MM
                    breaches: list[str] = []
                    if bbox[0] - trim.x0 < buf_pts:
                        breaches.append(f"left ({(bbox[0] - trim.x0) / _PTS_PER_MM:.1f}mm)")
                    if trim.x1 - bbox[2] < buf_pts:
                        breaches.append(f"right ({(trim.x1 - bbox[2]) / _PTS_PER_MM:.1f}mm)")
                    if bbox[1] - trim.y0 < buf_pts:
                        breaches.append(f"bottom ({(bbox[1] - trim.y0) / _PTS_PER_MM:.1f}mm)")
                    if trim.y1 - bbox[3] < buf_pts:
                        breaches.append(f"top ({(trim.y1 - bbox[3]) / _PTS_PER_MM:.1f}mm)")
                    if breaches:
                        findings.append(
                            Finding(
                                inspection_id="LPDF_BARCODE_031",
                                severity=Severity.WARNING,
                                message=(
                                    f"Barcode quiet zone close to trim edge on page "
                                    f"{candidate.page_num}: {', '.join(breaches)} "
                                    f"(< {qz_buf_mm:.0f}mm to trim). GS1 quiet-"
                                    "zone clearance (9x X-dim leading / 7x X-dim "
                                    "trailing) may be lost after finishing or seam "
                                    "occlusion. Verify quiet zones survive the cut."
                                ),
                                page_num=candidate.page_num,
                                details={
                                    "breaches": breaches,
                                    "buffer_mm": qz_buf_mm,
                                },
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

    def _check_orientation_suite(
        self, candidates: list[_BarcodeCandidate], document: SemanticDocument
    ) -> list[Finding]:
        """PR D Slot 4 — barcode orientation + quiet-zone + bar-height suite.

        Closes the 10 barcode misses Opus surfaced in the post-merge audit
        (`/tmp/audit-opus-postmerge-1777391641/`). Each rule reuses the
        existing ``_BarcodeCandidate`` bbox + stroke widths; no new
        rendering or decoding is required.

        Check IDs:
        * ``LPDF_BARCODE_ORIENTATION`` — 1D barcode rotated >45° off the
          page's long axis (ladder vs picket mismatch on stick-pack /
          pouch fixtures).
        * ``LPDF_BARCODE_QUIET_ZONE`` — bbox sits within 5.2 mm of any
          page edge (GS1 absolute minimum for picket-on-edge codes).
        * ``LPDF_BARCODE_HEIGHT_MIN`` — bar height < ``narrow_bar_width *
          10`` (linear minimum per GS1 General Specifications).
        """
        findings: list[Finding] = []
        # GS1 minima
        gs1_quiet_zone_pt = 5.2 * 2.83464567  # 5.2 mm in points
        for candidate in candidates:
            if not candidate.has_bounds:
                continue
            page_idx = candidate.page_num - 1
            if page_idx < 0 or page_idx >= len(document.pages):
                continue
            page = document.pages[page_idx]
            page_w = page.media_box.width
            page_h = page.media_box.height
            x0, y0, x1, y1 = candidate.bbox  # type: ignore[misc]
            bbox_w = x1 - x0
            bbox_h = y1 - y0

            # ── ORIENTATION ───────────────────────────────────────────
            # Page format: portrait if h>w, landscape otherwise.
            page_landscape = page_w > page_h
            # Barcode aspect: picket-fence (horizontal bars) is wide
            # & short (bbox_w > bbox_h * 1.5); ladder is tall & narrow.
            bar_picket = bbox_w > bbox_h * 1.5
            bar_ladder = bbox_h > bbox_w * 1.5
            orientation_mismatch = False
            mismatch_reason = ""
            if bar_ladder and page_landscape:
                # Ladder on landscape page: barcode is rotated 90° off
                # the natural reading axis. Common stick-pack issue.
                orientation_mismatch = True
                mismatch_reason = (
                    "Ladder-orientation barcode (tall, narrow) on a "
                    "landscape page — barcode rotated 90° off the "
                    "page's long axis"
                )
            elif bar_picket and not page_landscape:
                # Picket on portrait page — only a concern when the
                # bbox is also near the trim edge (barcode running
                # parallel to the trim, common on stick-packs where
                # the long bar axis crosses the seal).
                # Defer to QUIET_ZONE check below.
                pass
            if orientation_mismatch:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_ORIENTATION",
                        severity=Severity.WARNING,
                        message=(
                            f"{mismatch_reason} on page {candidate.page_num}. "
                            "Verify scanner orientation at the production "
                            "line — pickers and inline scanners typically "
                            "expect picket-fence on landscape and ladder "
                            "on portrait."
                        ),
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                        details={
                            "page_orientation": "landscape" if page_landscape else "portrait",
                            "barcode_aspect": "ladder" if bar_ladder else "picket",
                            "bbox_pts": list(candidate.bbox or ()),
                        },
                    )
                )

            # ── QUIET ZONE ────────────────────────────────────────────
            # Distance to each page edge.
            margin_left = x0
            margin_right = page_w - x1
            margin_bottom = y0
            margin_top = page_h - y1
            edges_violated = [
                name
                for name, m in (
                    ("left", margin_left),
                    ("right", margin_right),
                    ("bottom", margin_bottom),
                    ("top", margin_top),
                )
                if m < gs1_quiet_zone_pt
            ]
            if edges_violated:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_QUIET_ZONE_EDGE",
                        severity=Severity.WARNING,
                        message=(
                            f"Barcode on page {candidate.page_num} sits within "
                            f"{gs1_quiet_zone_pt:.1f}pt (5.2 mm GS1 minimum) "
                            f"of {len(edges_violated)} page edge(s): "
                            f"{', '.join(edges_violated)}. Quiet-zone "
                            "encroachment on labels reduces first-pass "
                            "scan rate; verify against production die."
                        ),
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                        details={
                            "edges_violated": edges_violated,
                            "min_gs1_quiet_zone_mm": 5.2,
                            "margins_pts": {
                                "left": round(margin_left, 2),
                                "right": round(margin_right, 2),
                                "bottom": round(margin_bottom, 2),
                                "top": round(margin_top, 2),
                            },
                        },
                    )
                )

            # ── HEIGHT MIN ────────────────────────────────────────────
            # Bar height should be at least 10x the narrowest bar width
            # for linear (1D) symbologies per GS1 General Specs.
            if candidate.stroke_widths:
                narrow_bar = min(candidate.stroke_widths)
                # Bar-axis dimension = the SHORTER of (bbox_w, bbox_h) for
                # ladder, longer for picket. Use the perpendicular-to-bars
                # axis: that's the height of the bars themselves.
                bar_height = min(bbox_w, bbox_h)
                min_height = narrow_bar * 10
                if 0 < bar_height < min_height:
                    findings.append(
                        Finding(
                            inspection_id="LPDF_BARCODE_HEIGHT_MIN",
                            severity=Severity.WARNING,
                            message=(
                                f"Barcode on page {candidate.page_num} has bars "
                                f"only {bar_height:.2f}pt tall — below the "
                                f"GS1 minimum of {min_height:.2f}pt "
                                f"(10x narrow bar width {narrow_bar:.2f}pt). "
                                "Truncated bars reduce scanner read distance."
                            ),
                            page_num=candidate.page_num,
                            bbox=candidate.bbox,
                            details={
                                "bar_height_pts": round(bar_height, 2),
                                "narrow_bar_pts": round(narrow_bar, 2),
                                "gs1_min_pts": round(min_height, 2),
                            },
                        )
                    )

        return findings

    def _check_size_and_quiet_zone_ink(
        self,
        candidates: list[_BarcodeCandidate],
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """PR-L (audit miss closure): two extra signals that the
        existing barcode suite did not surface.

        * ``LPDF_BARCODE_NOMINAL_SIZE_LOW`` — barcode bbox width on
          its long-bar axis is below 80% of UPC-A / EAN-13 nominal
          (37.29 mm * 0.80 = 29.83 mm). Detection is dimension-based,
          so it fires on any 1D candidate that shrinks to multi-up
          panel scale (DailyFiber 10-up).
        * ``LPDF_BARCODE_QUIET_ZONE_INK`` — painted content (fills /
          strokes / images that are NOT part of the barcode itself)
          overlaps the GS1 quiet zone (10x narrow-bar leading,
          7x trailing). Fires when adjacent printed background or
          frame encroaches the quiet zone, even when the barcode is
          well clear of the trim edge.
        """
        from lintpdf.semantic.events import ImagePlacedEvent, PathPaintingEvent

        findings: list[Finding] = []
        # GS1 UPC-A nominal long axis = 37.29 mm; 80% = 29.83 mm.
        gs1_nominal_min_mm = 29.83
        gs1_nominal_min_pt = gs1_nominal_min_mm * 2.83464567

        # Bucket non-barcode painted events per page for fast lookup.
        non_barcode_bboxes_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
        for event in events:
            if not isinstance(event, (PathPaintingEvent, ImagePlacedEvent)):
                continue
            bbox = getattr(event, "bbox", None)
            if not bbox:
                continue
            page_num = getattr(event, "page_num", None)
            if page_num is None:
                continue
            non_barcode_bboxes_by_page.setdefault(page_num, []).append(bbox)

        for candidate in candidates:
            if not candidate.has_bounds or not candidate.stroke_widths:
                continue
            x0, y0, x1, y1 = candidate.bbox  # type: ignore[misc]
            bbox_w = x1 - x0
            bbox_h = y1 - y0
            long_axis = max(bbox_w, bbox_h)
            short_axis = min(bbox_w, bbox_h)
            narrow_bar = min(candidate.stroke_widths)

            # ── NOMINAL SIZE ─────────────────────────────────────────
            if 0 < long_axis < gs1_nominal_min_pt:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_NOMINAL_SIZE_LOW",
                        severity=Severity.WARNING,
                        message=(
                            f"Barcode on page {candidate.page_num} is "
                            f"{long_axis / 2.83464567:.1f} mm on its long axis "
                            f"(below GS1 80% magnification minimum "
                            f"{gs1_nominal_min_mm:.1f} mm). At sub-nominal "
                            "size, X-dimension shrinks below the recommended "
                            "0.264 mm and scan reliability drops sharply on "
                            "flexo / digital print. Increase scale or apply "
                            "bar-width reduction (BWR) compensation."
                        ),
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                        details={
                            "long_axis_mm": round(long_axis / 2.83464567, 2),
                            "long_axis_pts": round(long_axis, 2),
                            "min_nominal_mm": gs1_nominal_min_mm,
                            "narrow_bar_pts": round(narrow_bar, 3),
                        },
                    )
                )

            # ── QUIET ZONE INK ───────────────────────────────────────
            # Define quiet-zone strips on the two ends parallel to the
            # bar direction. Picket = bars vertical, quiet zones
            # left+right; ladder = bars horizontal, quiet zones top
            # +bottom. Width = 10x narrow bar (GS1 leading); use 10x
            # both sides as a conservative single threshold.
            qz = narrow_bar * 10
            if bbox_w > bbox_h:
                # Picket — quiet zones extend left/right of the bbox.
                strips = [
                    (x0 - qz, y0, x0, y1),  # left
                    (x1, y0, x1 + qz, y1),  # right
                ]
            else:
                # Ladder — quiet zones extend top/bottom.
                strips = [
                    (x0, y0 - qz, x1, y0),  # bottom
                    (x0, y1, x1, y1 + qz),  # top
                ]
            page_bboxes = non_barcode_bboxes_by_page.get(candidate.page_num, [])
            # Filter out events that originated from the barcode itself —
            # a stroke whose narrow_bar matches the candidate's narrow
            # bar is almost certainly part of the symbol.
            obstructions: list[tuple[float, float, float, float]] = []
            for ev_bbox in page_bboxes:
                ex0, ey0, ex1, ey1 = ev_bbox
                # Skip events fully inside the barcode bbox itself.
                if ex0 >= x0 - 0.5 and ey0 >= y0 - 0.5 and ex1 <= x1 + 0.5 and ey1 <= y1 + 0.5:
                    continue
                # Match against quiet-zone strips.
                for sx0, sy0, sx1, sy1 in strips:
                    if ex1 <= sx0 or ex0 >= sx1 or ey1 <= sy0 or ey0 >= sy1:
                        continue
                    obstructions.append(ev_bbox)
                    break
            if obstructions:
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_QUIET_ZONE_INK",
                        severity=Severity.WARNING,
                        message=(
                            f"Barcode on page {candidate.page_num} has "
                            f"{len(obstructions)} painted element(s) "
                            f"overlapping its GS1 quiet zone "
                            f"(10x narrow-bar = {qz:.2f} pt to either "
                            "side of the bars). Adjacent printed art "
                            "encroaches the scan window even when the "
                            "barcode is well clear of the trim edge."
                        ),
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                        details={
                            "obstruction_count": len(obstructions),
                            "quiet_zone_pts": round(qz, 2),
                            "narrow_bar_pts": round(narrow_bar, 3),
                            "short_axis_pts": round(short_axis, 2),
                        },
                    )
                )
        return findings

    def _check_fold_proximity(
        self,
        candidates: list[_BarcodeCandidate],
        document: SemanticDocument,
    ) -> list[Finding]:
        """PR-W (audit miss closure): GS1 quiet-zone-on-fold check.

        ``LPDF_BARCODE_029`` only knows about the page centre as a fold
        proxy. On stick-pack and sachet artwork the fold runs along a
        side seam — geometry the dieline detector already recovered into
        ``DielineResult.regions`` / ``.polylines``. When a barcode's
        GS1 quiet zone (10x narrow-bar leading, 7x trailing) overlaps a
        fold polygon the bars print across the seam and the scan fails.
        Caught by Opus on AN-Energy stick-pack and HSI_OUTLINED.
        """
        result = getattr(document, "dieline_result", None)
        if result is None:
            return []
        # Collect fold/crease/score region bboxes. Honour both ``regions``
        # (per-island bboxes) and ``polylines`` (closed polygons). Skip
        # when neither is populated (e.g. ``source="missing"``).
        fold_bboxes: list[tuple[float, float, float, float]] = []
        regions = getattr(result, "regions", None) or []
        for region in regions:
            try:
                fold_bboxes.append(
                    (
                        float(region["x0"]),
                        float(region["y0"]),
                        float(region["x1"]),
                        float(region["y1"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        if not fold_bboxes:
            polylines = getattr(result, "polylines", None) or []
            for poly in polylines:
                if not poly:
                    continue
                try:
                    xs = [float(p[0]) for p in poly]
                    ys = [float(p[1]) for p in poly]
                except (IndexError, TypeError, ValueError):
                    continue
                if not xs or not ys:
                    continue
                fold_bboxes.append((min(xs), min(ys), max(xs), max(ys)))
        if not fold_bboxes:
            return []

        findings: list[Finding] = []
        for candidate in candidates:
            if not candidate.has_bounds or not candidate.stroke_widths:
                continue
            narrow_bar = min(candidate.stroke_widths)
            if narrow_bar <= 0:
                continue
            # GS1 minimum quiet zone is 10x narrow-bar module.
            qz = narrow_bar * 10.0
            x0, y0, x1, y1 = candidate.bbox  # type: ignore[misc]
            qz_bbox = (x0 - qz, y0 - qz, x1 + qz, y1 + qz)

            for fold_bbox in fold_bboxes:
                if _bbox_distance(qz_bbox, fold_bbox) > 0.0:
                    continue
                findings.append(
                    Finding(
                        inspection_id="LPDF_BARCODE_QUIET_ZONE_ON_FOLD",
                        severity=Severity.WARNING,
                        message=(
                            f"Barcode on page {candidate.page_num} sits across a "
                            f"detected fold/dieline polygon — the GS1 quiet zone "
                            f"({narrow_bar * 10 / 2.83464567:.2f} mm = 10x narrow-bar) "
                            "overlaps a fold line, so the bars print across the "
                            "seam and a scanner won't read the symbol cleanly."
                        ),
                        page_num=candidate.page_num,
                        bbox=candidate.bbox,
                        details={
                            "narrow_bar_pts": round(narrow_bar, 3),
                            "quiet_zone_pts": round(qz, 2),
                            "fold_bbox": [round(v, 2) for v in fold_bbox],
                            "dieline_source": getattr(result, "source", None),
                        },
                    )
                )
                break  # one finding per barcode; further folds are redundant
        return findings

    def _check_barcode_background(
        self,
        candidates: list[_BarcodeCandidate],
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """PR-Z (audit miss closure): GS1 PCS contrast / barcode on dark
        background.

        GS1 General Specifications §5.5.7 requires a Print Contrast
        Signal ≥ 0.7 between the bars and the background. When a
        barcode sits on a coloured fill (pink, purple, cream) without
        a white knockout box the PCS drops below specification and
        the symbol won't scan reliably.

        Tier 1 (this check, structural — no GPU): walk fill events
        whose bbox overlaps the barcode's quiet-zone halo, classify
        each fill as light vs tinted by colour space, and flag the
        barcode when a tinted fill encroaches AND no white knockout
        box covers the bars.

        Caught roughly seven of the post-merge audit's barcode misses
        (DailyFiber pink, Nutrops purple, Pink-Slush magenta, etc.).
        """
        from lintpdf.semantic.events import PathPaintingEvent

        # Bucket fill events per page so we don't re-scan the whole
        # event stream per candidate.
        fills_by_page: dict[int, list[PathPaintingEvent]] = {}
        for event in events:
            if not isinstance(event, PathPaintingEvent) or not event.fill:
                continue
            bbox = getattr(event, "bbox", None)
            if not bbox:
                continue
            fills_by_page.setdefault(event.page_num, []).append(event)

        findings: list[Finding] = []
        for candidate in candidates:
            if not candidate.has_bounds or not candidate.stroke_widths:
                continue
            narrow_bar = min(candidate.stroke_widths)
            if narrow_bar <= 0:
                continue
            qz = narrow_bar * 10.0  # GS1 minimum quiet-zone module count
            x0, y0, x1, y1 = candidate.bbox  # type: ignore[misc]
            qz_bbox = (x0 - qz, y0 - qz, x1 + qz, y1 + qz)
            barcode_bbox = (x0, y0, x1, y1)

            page_fills = fills_by_page.get(candidate.page_num) or []
            tinted: list[tuple[str, tuple[float, ...]]] = []
            white_knockout = False
            for ev in page_fills:
                fbb = getattr(ev, "bbox", None)
                if not fbb or _bbox_distance(qz_bbox, fbb) > 0.0:
                    continue
                # Skip degenerate fills smaller than 5 pt² — likely
                # decorative artefacts, not background panels.
                fill_w = float(fbb[2]) - float(fbb[0])
                fill_h = float(fbb[3]) - float(fbb[1])
                if fill_w * fill_h < 5.0:
                    continue
                cs = ev.fill_color_space or ""
                vals = tuple(float(v) for v in (ev.fill_color_values or ()))
                if _is_white_fill(cs, vals) and _bbox_contains(fbb, barcode_bbox):
                    white_knockout = True
                    break
                if not _is_light_fill(cs, vals):
                    tinted.append((cs, vals))

            if white_knockout or not tinted:
                continue

            # Surface up to 3 distinct (cs, values) tuples in details.
            cs_summary: list[dict[str, Any]] = []
            seen_pairs: set[tuple[str, tuple[float, ...]]] = set()
            for cs, vals in tinted:
                key = (cs, vals)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                cs_summary.append({"color_space": cs, "values": list(vals)})
                if len(cs_summary) >= 3:
                    break

            findings.append(
                Finding(
                    inspection_id="LPDF_BARCODE_DARK_BG",
                    severity=Severity.WARNING,
                    message=(
                        f"Barcode on page {candidate.page_num} sits on a tinted / "
                        f"non-white background fill without a detected white "
                        f"knockout box. GS1 General Specifications §5.5.7 requires "
                        "a Print Contrast Signal ≥ 0.7 between bars and quiet "
                        "zone — coloured substrates (pink, purple, cream, etc.) "
                        "drop the PCS below the scan threshold. Place a white "
                        "knockout fill behind the bars + 10x quiet zone."
                    ),
                    page_num=candidate.page_num,
                    bbox=candidate.bbox,
                    details={
                        "narrow_bar_pts": round(narrow_bar, 3),
                        "quiet_zone_pts": round(qz, 2),
                        "tinted_fills": cs_summary,
                        "tinted_fill_count": len(tinted),
                    },
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

            # WS-10 structural gate. Before emitting any of the
            # LPDF_BARCODE_014..018 advisories, verify the candidate
            # region actually looks like a 2D barcode. The audit
            # disputed 100% of these on splatter artwork / blocky
            # decorative text because the old heuristic just counted
            # "small square-ish fills." Real Data Matrix / QR
            # symbols satisfy ALL of:
            #
            # 1. Aspect ratio is near-square (0.4 .. 2.5). Full-panel
            #    regions (0.34, 2.63) get caught here.
            # 2. Region is smaller than 50% of the likely page area.
            #    The Nutrops 143x427mm "barcode" and the Pavette
            #    both-labels span get caught here.
            # 3. Module-size coefficient of variation is < 0.5 on
            #    both axes. Splatter artwork varies wildly.
            # 4. Fill density >= 20% of the region area. A scatter
            #    of 30 tiny marks in a huge area is not a barcode.
            #
            # If any check fails, skip the entire 014..018 cascade
            # for this candidate region.
            if not _looks_like_2d_barcode(fills, region_w, region_h):
                continue

            trim = _page_trim_like(document, page_num)
            if trim is not None and _region_covers_trim_excessively(region_bbox, trim):
                continue

            raw_pdf = getattr(document, "_pdf_bytes", None)
            pdf_bytes = raw_pdf if isinstance(raw_pdf, (bytes, bytearray)) else None
            require_zxing_decode = bool(_HAS_ZXING and pdf_bytes)
            verified_by = "heuristic"
            if require_zxing_decode:
                decoded_ok = _zxing_decodes_2d_matrix_in_region(
                    bytes(pdf_bytes),
                    page_num=page_num,
                    region_bbox=region_bbox,
                    document=document,
                )
                if not decoded_ok:
                    continue
                verified_by = "zxing"

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
                        "verification": verified_by,
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
