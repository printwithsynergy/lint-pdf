"""Barcode decode analyzer — scans PDF pages for 1D and 2D barcodes."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Optional barcode libraries
try:
    from pyzbar import pyzbar as _pyzbar
    from pyzbar.pyzbar import ZBarSymbol

    _HAS_PYZBAR = True
except ImportError:
    _HAS_PYZBAR = False
    _pyzbar = None
    ZBarSymbol = None

try:
    from pylibdmtx import pylibdmtx as _dmtx

    _HAS_DMTX = True
except ImportError:
    _HAS_DMTX = False
    _dmtx = None

try:
    from PIL import Image as PILImage

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    PILImage = None  # type: ignore[assignment]

# Symbology type names recognised by pyzbar
_1D_TYPES = {"EAN13", "UPCA", "UPCE", "CODE128", "CODE39", "I25"}
_2D_TYPES = {"QRCODE"}

# Friendly display names
_SYMBOLOGY_NAMES: dict[str, str] = {
    "EAN13": "EAN-13",
    "UPCA": "UPC-A",
    "UPCE": "UPC-E",
    "CODE128": "Code 128",
    "CODE39": "Code 39",
    "I25": "ITF-14",
    "QRCODE": "QR Code",
    "DATAMATRIX": "DataMatrix",
}


@register_ai_analyzer
class BarcodeDecode(BaseAIAnalyzer):
    """Scan PDF pages for 1D and 2D barcodes and decode their content."""

    category = "barcode"
    feature_slug = "barcode_decode"
    tier = "cpu"
    credits_per_run = 1

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        if not (_HAS_PYZBAR and _HAS_PIL):
            logger.debug("barcode_decode: pyzbar or Pillow not available — skipping")
            return []

        from lintpdf.ai.rendering import render_all_pages

        findings: list[Finding] = []

        try:
            page_images = render_all_pages(pdf_bytes, dpi=300)
        except RuntimeError:
            logger.debug("barcode_decode: PDF rendering backend unavailable")
            return []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            img = PILImage.open(io.BytesIO(png_bytes))

            # --- 1D / QR via pyzbar ---
            decoded_items = _pyzbar.decode(img)
            for item in decoded_items:
                sym_type = item.type
                display_type = _SYMBOLOGY_NAMES.get(sym_type, sym_type)
                data = item.data.decode("utf-8", errors="replace")
                rect = item.rect  # Rect(left, top, width, height)
                bbox = (
                    float(rect.left),
                    float(rect.top),
                    float(rect.left + rect.width),
                    float(rect.top + rect.height),
                )

                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_BC_001",
                        severity=Severity.ADVISORY,
                        message=(f"Decoded {display_type} barcode on page {page_num}: '{data}'"),
                        page_num=page_num,
                        details={
                            "symbology": display_type,
                            "decoded_data": data,
                            "bbox_px": list(bbox),
                            "dpi": 300,
                        },
                        bbox=bbox,
                        object_type="barcode",
                    )
                )

            # --- DataMatrix via pylibdmtx ---
            if _HAS_DMTX:
                dm_items = _dmtx.decode(img)
                for item in dm_items:
                    data = item.data.decode("utf-8", errors="replace")
                    rect = item.rect  # Rect(left, top, width, height)
                    bbox = (
                        float(rect.left),
                        float(rect.top),
                        float(rect.left + rect.width),
                        float(rect.top + rect.height),
                    )

                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_BC_001",
                            severity=Severity.ADVISORY,
                            message=(f"Decoded DataMatrix barcode on page {page_num}: '{data}'"),
                            page_num=page_num,
                            details={
                                "symbology": "DataMatrix",
                                "decoded_data": data,
                                "bbox_px": list(bbox),
                                "dpi": 300,
                            },
                            bbox=bbox,
                            object_type="barcode",
                        )
                    )

        if not findings:
            findings.append(
                self._make_finding(
                    inspection_id="LPDF_BC_001",
                    severity=Severity.ADVISORY,
                    message="No barcodes detected in document",
                )
            )

        return findings
