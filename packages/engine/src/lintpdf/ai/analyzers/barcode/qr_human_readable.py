"""QR human-readable matching — verifies text near QR codes matches decoded data."""

from __future__ import annotations

import contextlib
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

try:
    import pytesseract as _pytesseract

    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False
    _pytesseract = None

# Margin (in pixels at 300 DPI) to expand around QR bounding box for OCR
_OCR_MARGIN_PX = 150

# Minimum similarity ratio to consider text a "match"
_MATCH_THRESHOLD = 0.7


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip whitespace/punctuation."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9:/._\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _similarity(a: str, b: str) -> float:
    """Compute simple token-overlap similarity between two strings.

    Returns a value between 0.0 and 1.0.
    """
    if not a or not b:
        return 0.0

    tokens_a = set(a.split())
    tokens_b = set(b.split())

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union)


def _extract_text_near_bbox(  # skipcq: PY-R1000
    img: Any,
    bbox: tuple[int, int, int, int],
    margin: int = _OCR_MARGIN_PX,
) -> str:
    """Extract text from the region surrounding a bounding box using OCR.

    Args:
        img: PIL Image.
        bbox: (left, top, right, bottom) in pixels.
        margin: Pixel margin to expand around the bbox.

    Returns:
        Extracted text string (may be empty).
    """
    if not _HAS_TESSERACT:
        return ""

    width, height = img.size
    left = max(0, bbox[0] - margin)
    top = max(0, bbox[1] - margin)
    right = min(width, bbox[2] + margin)
    bottom = min(height, bbox[3] + margin)

    # Crop the surrounding region, excluding the QR code itself
    # We create strips around the QR: above, below, left, right
    text_parts: list[str] = []

    # Region above QR
    if bbox[1] - margin > 0:
        region_above = img.crop((left, top, right, bbox[1]))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region_above).strip())

    # Region below QR
    if bbox[3] + margin < height:
        region_below = img.crop((left, bbox[3], right, bottom))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region_below).strip())

    # Region left of QR
    if bbox[0] - margin > 0:
        region_left = img.crop((left, bbox[1], bbox[0], bbox[3]))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region_left).strip())

    # Region right of QR
    if bbox[2] + margin < width:
        region_right = img.crop((bbox[2], bbox[1], right, bbox[3]))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region_right).strip())

    return " ".join(part for part in text_parts if part)


@register_ai_analyzer
class QRHumanReadableMatching(BaseAIAnalyzer):
    """Verify that human-readable text near QR codes matches the decoded data."""

    category = "barcode"
    feature_slug = "qr_human_readable_matching"
    tier = "cpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        if not (_HAS_PYZBAR and _HAS_PIL):
            logger.debug("qr_human_readable_matching: pyzbar or Pillow not available — skipping")
            return []

        if not _HAS_TESSERACT:
            logger.debug("qr_human_readable_matching: pytesseract not available — skipping")
            return []

        from lintpdf.ai.rendering import render_all_pages

        findings: list[Finding] = []

        try:
            page_images = render_all_pages(pdf_bytes, dpi=300)
        except RuntimeError:
            logger.debug("qr_human_readable_matching: PDF rendering backend unavailable")
            return []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            img = PILImage.open(io.BytesIO(png_bytes))

            decoded_items = _pyzbar.decode(img)
            qr_items = [d for d in decoded_items if d.type == "QRCODE"]

            for item in qr_items:
                data = item.data.decode("utf-8", errors="replace")
                rect = item.rect
                bbox_px = (
                    rect.left,
                    rect.top,
                    rect.left + rect.width,
                    rect.top + rect.height,
                )
                bbox_float = (
                    float(bbox_px[0]),
                    float(bbox_px[1]),
                    float(bbox_px[2]),
                    float(bbox_px[3]),
                )

                # Extract nearby text via OCR
                nearby_text = _extract_text_near_bbox(img, bbox_px)

                if not nearby_text.strip():
                    findings.append(
                        self._make_finding(
                            inspection_id="GRD_QHR_001",
                            severity=Severity.ADVISORY,
                            message=(
                                f"No human-readable text detected near QR code on page {page_num}"
                            ),
                            page_num=page_num,
                            details={
                                "qr_data": data,
                            },
                            bbox=bbox_float,
                            object_type="barcode",
                        )
                    )
                    continue

                # Compare decoded data with nearby text
                norm_data = _normalize_text(data)
                norm_nearby = _normalize_text(nearby_text)

                sim = _similarity(norm_data, norm_nearby)

                # For URLs, also check if the URL appears as a substring
                is_url = data.startswith("http://") or data.startswith("https://")
                url_found_in_text = is_url and data.lower() in nearby_text.lower()

                if url_found_in_text or sim >= _MATCH_THRESHOLD:
                    findings.append(
                        self._make_finding(
                            inspection_id="GRD_QHR_002",
                            severity=Severity.ADVISORY,
                            message=(
                                f"QR code on page {page_num}: human-readable text "
                                f"matches decoded data (similarity {sim:.0%})"
                            ),
                            page_num=page_num,
                            details={
                                "qr_data": data,
                                "nearby_text": nearby_text[:200],
                                "similarity": round(sim, 3),
                            },
                            bbox=bbox_float,
                            object_type="barcode",
                        )
                    )
                else:
                    findings.append(
                        self._make_finding(
                            inspection_id="GRD_QHR_003",
                            severity=Severity.WARNING,
                            message=(
                                f"QR code on page {page_num}: human-readable text "
                                f"does not match decoded data (similarity {sim:.0%}). "
                                f"QR contains '{data[:60]}{'...' if len(data) > 60 else ''}', "
                                f"nearby text: '{nearby_text[:60]}{'...' if len(nearby_text) > 60 else ''}'"
                            ),
                            page_num=page_num,
                            details={
                                "qr_data": data,
                                "nearby_text": nearby_text[:500],
                                "similarity": round(sim, 3),
                                "threshold": _MATCH_THRESHOLD,
                            },
                            bbox=bbox_float,
                            object_type="barcode",
                        )
                    )

        return findings
