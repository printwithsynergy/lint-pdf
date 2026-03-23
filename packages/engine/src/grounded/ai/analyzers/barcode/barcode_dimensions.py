"""Barcode dimension validation — measures X-dimension, quiet zones, and height."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Any

from grounded.ai.base import BaseAIAnalyzer
from grounded.ai.registry import register_ai_analyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.api.models import TenantAIConfig
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

try:
    from pyzbar import pyzbar as _pyzbar

    _HAS_PYZBAR = True
except ImportError:
    _HAS_PYZBAR = False
    _pyzbar = None

try:
    from PIL import Image as PILImage

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    PILImage = None  # type: ignore[assignment]

# GS1 General Specifications — EAN/UPC nominal values
_NOMINAL_X_MM = 0.330  # Nominal X-dimension for EAN/UPC at 100% magnification
_ABSOLUTE_MIN_X_MM = 0.264  # 80% of nominal — absolute minimum per GS1
_RECOMMENDED_MIN_X_MM = 0.330  # 100% recommended

# Magnification limits (GS1 General Specifications Section 5.2.4.2)
_MAG_ABSOLUTE_MIN = 0.80  # 80%
_MAG_RECOMMENDED_MIN = 1.00  # 100%
_MAG_ABSOLUTE_MAX = 2.00  # 200%

# Minimum quiet zone widths (in X-dimension multiples)
_QUIET_ZONE_MULTIPLES: dict[str, tuple[int, int]] = {
    # symbology: (left_modules, right_modules)
    "EAN13": (11, 7),
    "UPCA": (9, 9),
    "UPCE": (9, 7),
    "CODE128": (10, 10),
    "CODE39": (10, 10),
    "I25": (10, 10),  # ITF-14
}

# Minimum symbol heights (mm) at 100% magnification
_MIN_HEIGHT_MM: dict[str, float] = {
    "EAN13": 22.85,
    "UPCA": 25.91,
    "UPCE": 18.23,
    "CODE128": 5.08,  # Per application, 5.08 is typical minimum
    "I25": 31.75,  # ITF-14
}

# Symbologies that use the EAN/UPC X-dimension system
_EAN_UPC_TYPES = {"EAN13", "UPCA", "UPCE"}


def _estimate_x_dimension(
    img: Any,
    rect: Any,
    dpi: int,
    symbology: str,
) -> tuple[float | None, float | None, float | None]:
    """Estimate X-dimension (mm), symbol height (mm), and magnification factor.

    Returns (x_dim_mm, height_mm, magnification).
    """
    try:
        import numpy as np

        arr = np.array(img.convert("L"))
        left, top, width, height = rect.left, rect.top, rect.width, rect.height

        # Sample a horizontal row through the centre of the barcode
        mid_row = top + height // 2
        if mid_row >= arr.shape[0] or left + width > arr.shape[1]:
            return None, None, None

        row = arr[mid_row, left : left + width]
        if len(row) == 0:
            return None, None, None

        # Binarize
        threshold = (int(row.max()) + int(row.min())) // 2
        binary = row < threshold  # True = dark bar

        # Find run lengths
        runs: list[int] = []
        current = binary[0]
        run_len = 1
        for px in binary[1:]:
            if px == current:
                run_len += 1
            else:
                runs.append(run_len)
                current = px
                run_len = 1
        runs.append(run_len)

        if not runs:
            return None, None, None

        # X-dimension = minimum run length (narrowest bar/space)
        min_run = min(runs)
        x_dim_px = float(min_run)
        x_dim_mm = x_dim_px / dpi * 25.4

        # Symbol height in mm
        height_mm = float(height) / dpi * 25.4

        # Magnification (only meaningful for EAN/UPC)
        magnification: float | None = None
        if symbology in _EAN_UPC_TYPES:
            magnification = x_dim_mm / _NOMINAL_X_MM

        return x_dim_mm, height_mm, magnification
    except Exception:
        return None, None, None


@register_ai_analyzer
class BarcodeDimensionValidation(BaseAIAnalyzer):
    """Validate barcode dimensions against GS1 General Specifications."""

    category = "barcode"
    feature_slug = "barcode_dimension_validation"
    tier = "cpu"
    credits_per_run = 1

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        if not (_HAS_PYZBAR and _HAS_PIL):
            logger.debug("barcode_dimension_validation: pyzbar or Pillow not available — skipping")
            return []

        from grounded.ai.rendering import render_all_pages

        findings: list[Finding] = []
        dpi = 300

        try:
            page_images = render_all_pages(pdf_bytes, dpi=dpi)
        except RuntimeError:
            logger.debug("barcode_dimension_validation: PDF rendering backend unavailable")
            return []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            img = PILImage.open(io.BytesIO(png_bytes))

            decoded_items = _pyzbar.decode(img)
            for item in decoded_items:
                sym_type = item.type
                if sym_type == "QRCODE":
                    continue  # QR is handled by qr_validation

                rect = item.rect
                bbox = (
                    float(rect.left),
                    float(rect.top),
                    float(rect.left + rect.width),
                    float(rect.top + rect.height),
                )

                x_dim_mm, height_mm, magnification = _estimate_x_dimension(img, rect, dpi, sym_type)

                if x_dim_mm is None:
                    continue

                # --- X-dimension checks ---
                if sym_type in _EAN_UPC_TYPES:
                    if x_dim_mm < _ABSOLUTE_MIN_X_MM:
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_001",
                                severity=Severity.ERROR,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"X-dimension {x_dim_mm:.3f} mm is below "
                                    f"absolute minimum {_ABSOLUTE_MIN_X_MM:.3f} mm "
                                    f"(80% magnification)"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "x_dim_mm": round(x_dim_mm, 4),
                                    "absolute_min_mm": _ABSOLUTE_MIN_X_MM,
                                    "magnification": (
                                        round(magnification, 3) if magnification else None
                                    ),
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.4.2",
                                object_type="barcode",
                            )
                        )
                    elif x_dim_mm < _RECOMMENDED_MIN_X_MM:
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_001",
                                severity=Severity.WARNING,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"X-dimension {x_dim_mm:.3f} mm is below "
                                    f"recommended {_RECOMMENDED_MIN_X_MM:.3f} mm "
                                    f"(100% magnification)"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "x_dim_mm": round(x_dim_mm, 4),
                                    "recommended_min_mm": _RECOMMENDED_MIN_X_MM,
                                    "magnification": (
                                        round(magnification, 3) if magnification else None
                                    ),
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.4.2",
                                object_type="barcode",
                            )
                        )

                # --- Magnification factor ---
                if magnification is not None:
                    if magnification < _MAG_ABSOLUTE_MIN:
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_002",
                                severity=Severity.ERROR,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"magnification {magnification:.1%} is below "
                                    f"absolute minimum {_MAG_ABSOLUTE_MIN:.0%}"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "magnification": round(magnification, 3),
                                    "absolute_min": _MAG_ABSOLUTE_MIN,
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.4.2",
                                object_type="barcode",
                            )
                        )
                    elif magnification > _MAG_ABSOLUTE_MAX:
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_002",
                                severity=Severity.WARNING,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"magnification {magnification:.1%} exceeds "
                                    f"maximum {_MAG_ABSOLUTE_MAX:.0%}"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "magnification": round(magnification, 3),
                                    "absolute_max": _MAG_ABSOLUTE_MAX,
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.4.2",
                                object_type="barcode",
                            )
                        )

                # --- Symbol height ---
                if height_mm is not None and sym_type in _MIN_HEIGHT_MM:
                    min_h = _MIN_HEIGHT_MM[sym_type]
                    # Scale minimum height by magnification if available
                    effective_min_h = min_h
                    if magnification is not None:
                        effective_min_h = min_h * max(magnification, _MAG_ABSOLUTE_MIN)

                    if height_mm < effective_min_h * 0.8:
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_003",
                                severity=Severity.ERROR,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"height {height_mm:.2f} mm is critically below "
                                    f"minimum {effective_min_h:.2f} mm"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "height_mm": round(height_mm, 2),
                                    "min_height_mm": round(effective_min_h, 2),
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.4.3",
                                object_type="barcode",
                            )
                        )
                    elif height_mm < effective_min_h:
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_003",
                                severity=Severity.WARNING,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"height {height_mm:.2f} mm is below "
                                    f"recommended {effective_min_h:.2f} mm"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "height_mm": round(height_mm, 2),
                                    "min_height_mm": round(effective_min_h, 2),
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.4.3",
                                object_type="barcode",
                            )
                        )

                # --- Quiet zone check ---
                if sym_type in _QUIET_ZONE_MULTIPLES and x_dim_mm is not None:
                    left_modules, right_modules = _QUIET_ZONE_MULTIPLES[sym_type]
                    x_dim_px = x_dim_mm / 25.4 * dpi

                    required_left_px = left_modules * x_dim_px
                    required_right_px = right_modules * x_dim_px

                    actual_left_px = float(rect.left)
                    actual_right_px = float(img.width - (rect.left + rect.width))

                    if actual_left_px < required_left_px:
                        actual_left_modules = actual_left_px / x_dim_px if x_dim_px > 0 else 0
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_004",
                                severity=Severity.WARNING,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"left quiet zone ~{actual_left_modules:.1f} modules, "
                                    f"minimum {left_modules} required"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "side": "left",
                                    "actual_modules": round(actual_left_modules, 1),
                                    "required_modules": left_modules,
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.3.4",
                                object_type="barcode",
                            )
                        )

                    if actual_right_px < required_right_px:
                        actual_right_modules = actual_right_px / x_dim_px if x_dim_px > 0 else 0
                        findings.append(
                            self._make_finding(
                                inspection_id="GRD_BD_004",
                                severity=Severity.WARNING,
                                message=(
                                    f"{sym_type} barcode on page {page_num}: "
                                    f"right quiet zone ~{actual_right_modules:.1f} modules, "
                                    f"minimum {right_modules} required"
                                ),
                                page_num=page_num,
                                details={
                                    "symbology": sym_type,
                                    "side": "right",
                                    "actual_modules": round(actual_right_modules, 1),
                                    "required_modules": right_modules,
                                },
                                bbox=bbox,
                                iso_clause="GS1 General Specifications 5.2.3.4",
                                object_type="barcode",
                            )
                        )

        return findings
