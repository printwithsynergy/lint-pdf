"""QR code validation analyzer — checks structural quality of QR codes."""

from __future__ import annotations

import io
import logging
import re
from typing import TYPE_CHECKING, Any

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

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

# ISO 18004 minimum quiet zone is 4 modules on all sides
_MIN_QUIET_ZONE_MODULES = 4

# GS1 Digital Link pattern
_GS1_DIGITAL_LINK_RE = re.compile(
    r"https?://(?:[a-z0-9.-]+)/(?:01|gtin)/(\d{13,14})", re.IGNORECASE
)


def _estimate_module_size_and_quiet_zone(
    img: Any,
    rect: Any,
) -> tuple[float | None, float | None, float | None]:
    """Estimate the QR module size (px) and quiet zone widths from the image.

    Returns (module_size_px, quiet_zone_left_px, quiet_zone_top_px).
    """
    try:
        import numpy as np

        arr = np.array(img.convert("L"))
        left, top, width, height = rect.left, rect.top, rect.width, rect.height

        # Estimate module size from finder pattern:
        # The top-left finder pattern is 7 modules wide — roughly 1/5 of total width
        # for version 1 (21 modules). For larger versions, use the version formula.
        # Quick heuristic: find runs of black/white in the top row of the barcode.
        row = arr[top + height // 6, left : left + width]
        if len(row) == 0:
            return None, None, None

        # Binarize
        threshold = (int(row.max()) + int(row.min())) // 2
        binary = row < threshold

        # Find first run of dark pixels (start of finder pattern)
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

        if len(runs) < 5:
            return None, None, None

        # Finder pattern is B-W-B-W-B with ratio 1:1:3:1:1 (7 modules total)
        finder_px = sum(runs[:5])
        module_size = finder_px / 7.0

        # Quiet zone: distance from image edge (or detectable content) to barcode rect
        quiet_left = float(left)
        quiet_top = float(top)

        return module_size, quiet_left, quiet_top
    except Exception:
        return None, None, None


def _detect_error_correction(_data: str) -> str | None:
    """Heuristic: we cannot read EC level from pyzbar, return None."""
    return None


@register_ai_analyzer
class QRValidation(BaseAIAnalyzer):
    """Validate QR code structural quality per ISO 18004."""

    category = "barcode"
    feature_slug = "qr_validation"
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
            logger.debug("qr_validation: pyzbar or Pillow not available — skipping")
            return []

        from lintpdf.ai.rendering import render_all_pages

        findings: list[Finding] = []

        try:
            page_images = render_all_pages(pdf_bytes, dpi=300)
        except RuntimeError:
            logger.debug("qr_validation: PDF rendering backend unavailable")
            return []

        # Track decoded QR data for duplicate detection across all pages
        seen_qr: dict[str, list[int]] = {}  # data -> list of page numbers

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            img = PILImage.open(io.BytesIO(png_bytes))

            decoded_items = _pyzbar.decode(img)
            qr_items = [d for d in decoded_items if d.type == "QRCODE"]

            for item in qr_items:
                data = item.data.decode("utf-8", errors="replace")
                rect = item.rect
                bbox = (
                    float(rect.left),
                    float(rect.top),
                    float(rect.left + rect.width),
                    float(rect.top + rect.height),
                )

                # Track for duplicate detection
                seen_qr.setdefault(data, []).append(page_num)

                # --- Module size and quiet zone check ---
                module_size, quiet_left, quiet_top = _estimate_module_size_and_quiet_zone(img, rect)

                if module_size is not None and module_size > 0:
                    min_quiet_px = _MIN_QUIET_ZONE_MODULES * module_size

                    if quiet_left is not None and quiet_left < min_quiet_px:
                        quiet_modules = quiet_left / module_size
                        findings.append(
                            self._make_finding(
                                inspection_id="LPDF_QR_001",
                                severity=Severity.WARNING,
                                message=(
                                    f"QR code on page {page_num} has insufficient "
                                    f"left quiet zone: {quiet_modules:.1f} modules "
                                    f"(minimum {_MIN_QUIET_ZONE_MODULES} per ISO 18004)"
                                ),
                                page_num=page_num,
                                details={
                                    "quiet_zone_modules": round(quiet_modules, 2),
                                    "required_modules": _MIN_QUIET_ZONE_MODULES,
                                    "module_size_px": round(module_size, 2),
                                },
                                bbox=bbox,
                                iso_clause="ISO 18004:2015 7.3.7",
                                object_type="barcode",
                            )
                        )

                    if quiet_top is not None and quiet_top < min_quiet_px:
                        quiet_modules = quiet_top / module_size
                        findings.append(
                            self._make_finding(
                                inspection_id="LPDF_QR_001",
                                severity=Severity.WARNING,
                                message=(
                                    f"QR code on page {page_num} has insufficient "
                                    f"top quiet zone: {quiet_modules:.1f} modules "
                                    f"(minimum {_MIN_QUIET_ZONE_MODULES} per ISO 18004)"
                                ),
                                page_num=page_num,
                                details={
                                    "quiet_zone_modules": round(quiet_modules, 2),
                                    "required_modules": _MIN_QUIET_ZONE_MODULES,
                                    "module_size_px": round(module_size, 2),
                                },
                                bbox=bbox,
                                iso_clause="ISO 18004:2015 7.3.7",
                                object_type="barcode",
                            )
                        )

                    # Report module size as advisory
                    dpi = 300
                    module_size_mm = module_size / dpi * 25.4
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_QR_002",
                            severity=Severity.ADVISORY,
                            message=(
                                f"QR code on page {page_num}: module size "
                                f"{module_size_mm:.3f} mm "
                                f"({module_size:.1f} px at {dpi} DPI)"
                            ),
                            page_num=page_num,
                            details={
                                "module_size_mm": round(module_size_mm, 4),
                                "module_size_px": round(module_size, 2),
                                "dpi": dpi,
                            },
                            bbox=bbox,
                            object_type="barcode",
                        )
                    )

                # --- GS1 Digital Link validation ---
                gs1_match = _GS1_DIGITAL_LINK_RE.match(data)
                if gs1_match:
                    gtin = gs1_match.group(1)
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_QR_003",
                            severity=Severity.ADVISORY,
                            message=(
                                f"QR code on page {page_num} contains GS1 Digital "
                                f"Link with GTIN {gtin}"
                            ),
                            page_num=page_num,
                            details={
                                "gs1_digital_link": data,
                                "gtin": gtin,
                            },
                            bbox=bbox,
                            object_type="barcode",
                        )
                    )

        # --- Duplicate QR code detection ---
        for data, pages in seen_qr.items():
            if len(pages) > 1:
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_QR_004",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Duplicate QR code found on pages "
                            f"{', '.join(str(p) for p in pages)}: "
                            f"'{data[:80]}{'...' if len(data) > 80 else ''}'"
                        ),
                        details={
                            "decoded_data": data,
                            "pages": pages,
                            "count": len(pages),
                        },
                        object_type="barcode",
                    )
                )

        return findings
