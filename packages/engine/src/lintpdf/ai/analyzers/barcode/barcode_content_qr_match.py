"""Combined barcode content and QR human-readable matching analyzer."""

from __future__ import annotations

import contextlib
import io
import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
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

try:
    import pytesseract as _pytesseract

    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False
    _pytesseract = None


# --- Check digit helpers ---


def _compute_check_digit(digits: str) -> int:
    """Compute GS1 check digit for a numeric string (without check digit)."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        total += d * (3 if i % 2 == 0 else 1)
    return (10 - (total % 10)) % 10


def _validate_url(url: str) -> tuple[bool, str]:  # skipcq: PY-R1000
    """Validate a URL. Returns (is_valid, reason)."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            return False, "missing scheme (http/https)"
        if parsed.scheme not in ("http", "https", "ftp", "ftps", "mailto"):
            return False, f"unsupported scheme '{parsed.scheme}'"
        if not parsed.netloc and parsed.scheme not in ("mailto",):
            return False, "missing host/domain"
        host = parsed.hostname or ""
        if (
            host
            and not re.match(r"^[a-zA-Z0-9._-]+\.[a-zA-Z]{2,}$", host)
            and not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host)
        ):
            return False, f"invalid hostname '{host}'"
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9:/._\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _similarity(a: str, b: str) -> float:
    """Token-overlap similarity between two strings."""
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
    margin: int = 150,
) -> str:
    """Extract text from the region surrounding a bounding box using OCR."""
    if not _HAS_TESSERACT:
        return ""

    width, height = img.size
    left = max(0, bbox[0] - margin)
    top = max(0, bbox[1] - margin)
    right = min(width, bbox[2] + margin)
    bottom = min(height, bbox[3] + margin)

    text_parts: list[str] = []

    # Above
    if bbox[1] - margin > 0:
        region = img.crop((left, top, right, bbox[1]))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region).strip())

    # Below
    if bbox[3] + margin < height:
        region = img.crop((left, bbox[3], right, bottom))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region).strip())

    # Left
    if bbox[0] - margin > 0:
        region = img.crop((left, bbox[1], bbox[0], bbox[3]))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region).strip())

    # Right
    if bbox[2] + margin < width:
        region = img.crop((bbox[2], bbox[1], right, bbox[3]))
        with contextlib.suppress(Exception):
            text_parts.append(_pytesseract.image_to_string(region).strip())

    return " ".join(part for part in text_parts if part)


# GS1 AI spec for validation
_GS1_AI_SPECS: dict[str, tuple[str, int | None]] = {
    "00": ("SSCC", 18),
    "01": ("GTIN", 14),
    "02": ("Content GTIN", 14),
    "10": ("Batch/Lot", None),
    "11": ("Production Date", 6),
    "17": ("Expiry Date", 6),
    "21": ("Serial Number", None),
}

_GTIN_TYPES = {"EAN13", "UPCA", "UPCE"}
_MATCH_THRESHOLD = 0.7


@register_ai_analyzer
class BarcodeContentAndQRMatching(BaseAIAnalyzer):
    """Combined barcode content validation and QR human-readable matching.

    Runs both content validation (check digits, URLs, GS1 AIs) and
    QR-to-human-readable text matching in a single pass over the pages.
    """

    category = "barcode"
    feature_slug = "barcode_content_and_qr_matching"
    tier = "cpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        if not (_HAS_PIL and _HAS_PYZBAR):
            logger.debug(
                "barcode_content_and_qr_matching: pyzbar or Pillow not available — skipping"
            )
            return []

        from lintpdf.ai.rendering import render_all_pages

        findings: list[Finding] = []

        try:
            page_images = render_all_pages(pdf_bytes, dpi=300)
        except RuntimeError:
            logger.debug("barcode_content_and_qr_matching: PDF rendering backend unavailable")
            return []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            img = PILImage.open(io.BytesIO(png_bytes))

            decoded_items = _pyzbar.decode(img)

            for item in decoded_items:
                sym_type = item.type
                data = item.data.decode("utf-8", errors="replace")
                rect = item.rect
                bbox = (
                    float(rect.left),
                    float(rect.top),
                    float(rect.left + rect.width),
                    float(rect.top + rect.height),
                )

                # ==========================================
                # Part 1: Content validation (check digits)
                # ==========================================
                if sym_type in _GTIN_TYPES:
                    findings.extend(self._validate_check_digit(sym_type, data, page_num, bbox))

                # URL validation for QR codes
                if sym_type == "QRCODE" and data.startswith(("http://", "https://")):
                    is_valid, reason = _validate_url(data)
                    if not is_valid:
                        findings.append(
                            self._make_finding(
                                inspection_id="LPDF_BCQM_002",
                                severity=Severity.WARNING,
                                message=(
                                    f"QR code on page {page_num} contains invalid URL: {reason}"
                                ),
                                page_num=page_num,
                                details={
                                    "url": data,
                                    "validation_error": reason,
                                },
                                bbox=bbox,
                                object_type="barcode",
                            )
                        )

                # ==========================================
                # Part 2: QR human-readable matching
                # ==========================================
                if sym_type == "QRCODE" and _HAS_TESSERACT:
                    bbox_px = (
                        rect.left,
                        rect.top,
                        rect.left + rect.width,
                        rect.top + rect.height,
                    )

                    nearby_text = _extract_text_near_bbox(img, bbox_px)

                    if not nearby_text.strip():
                        findings.append(
                            self._make_finding(
                                inspection_id="LPDF_BCQM_003",
                                severity=Severity.ADVISORY,
                                message=(
                                    f"No human-readable text detected near QR code "
                                    f"on page {page_num}"
                                ),
                                page_num=page_num,
                                details={"qr_data": data},
                                bbox=bbox,
                                object_type="barcode",
                            )
                        )
                    else:
                        norm_data = _normalize_text(data)
                        norm_nearby = _normalize_text(nearby_text)
                        sim = _similarity(norm_data, norm_nearby)

                        is_url = data.startswith(("http://", "https://"))
                        url_found = is_url and data.lower() in nearby_text.lower()

                        if not (url_found or sim >= _MATCH_THRESHOLD):
                            findings.append(
                                self._make_finding(
                                    inspection_id="LPDF_BCQM_004",
                                    severity=Severity.WARNING,
                                    message=(
                                        f"QR code on page {page_num}: human-readable "
                                        f"text does not match decoded data "
                                        f"(similarity {sim:.0%})"
                                    ),
                                    page_num=page_num,
                                    details={
                                        "qr_data": data,
                                        "nearby_text": nearby_text[:500],
                                        "similarity": round(sim, 3),
                                    },
                                    bbox=bbox,
                                    object_type="barcode",
                                )
                            )

            # DataMatrix GS1 AI validation
            if _HAS_DMTX:
                dm_items = _dmtx.decode(img)
                for item in dm_items:
                    data = item.data.decode("utf-8", errors="replace")
                    rect = item.rect
                    bbox = (
                        float(rect.left),
                        float(rect.top),
                        float(rect.left + rect.width),
                        float(rect.top + rect.height),
                    )

                    # Check for GS1 DataMatrix
                    if data.startswith("]d2") or re.search(r"01\d{14}", data):
                        # Validate GTIN check digit from AI 01
                        m = re.search(r"01(\d{14})", data)
                        if m:
                            gtin = m.group(1)
                            expected = _compute_check_digit(gtin[:13])
                            if expected != int(gtin[13]):
                                findings.append(
                                    self._make_finding(
                                        inspection_id="LPDF_BCQM_001",
                                        severity=Severity.ERROR,
                                        message=(
                                            f"DataMatrix on page {page_num}: "
                                            f"GTIN {gtin} has invalid check digit "
                                            f"(expected {expected}, got {gtin[13]})"
                                        ),
                                        page_num=page_num,
                                        details={
                                            "gtin": gtin,
                                            "expected_check": expected,
                                            "actual_check": int(gtin[13]),
                                        },
                                        bbox=bbox,
                                        iso_clause="GS1 General Specifications 7.9",
                                        object_type="barcode",
                                    )
                                )

        return findings

    def _validate_check_digit(
        self,
        sym_type: str,
        data: str,
        page_num: int,
        bbox: tuple[float, float, float, float],
    ) -> list[Finding]:
        """Validate GTIN/EAN/UPC check digits."""
        findings: list[Finding] = []

        if sym_type == "EAN13" and len(data) == 13 and data.isdigit():
            expected = _compute_check_digit(data[:12])
            if expected != int(data[12]):
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_BCQM_001",
                        severity=Severity.ERROR,
                        message=(
                            f"EAN-13 on page {page_num}: invalid check digit "
                            f"(expected {expected}, got {data[12]})"
                        ),
                        page_num=page_num,
                        details={
                            "barcode_data": data,
                            "expected_check": expected,
                            "actual_check": int(data[12]),
                        },
                        bbox=bbox,
                        iso_clause="GS1 General Specifications 7.9",
                        object_type="barcode",
                    )
                )

        elif sym_type == "UPCA" and len(data) == 12 and data.isdigit():
            expected = _compute_check_digit(data[:11])
            if expected != int(data[11]):
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_BCQM_001",
                        severity=Severity.ERROR,
                        message=(
                            f"UPC-A on page {page_num}: invalid check digit "
                            f"(expected {expected}, got {data[11]})"
                        ),
                        page_num=page_num,
                        details={
                            "barcode_data": data,
                            "expected_check": expected,
                            "actual_check": int(data[11]),
                        },
                        bbox=bbox,
                        iso_clause="GS1 General Specifications 7.9",
                        object_type="barcode",
                    )
                )

        return findings
