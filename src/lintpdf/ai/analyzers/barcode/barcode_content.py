"""Barcode content validation — check digits, URLs, and GS1 AI structure."""

from __future__ import annotations

import io
import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

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

# Symbologies that use GS1 GTIN check digit
_GTIN_TYPES = {"EAN13", "UPCA", "UPCE"}

# Known GS1 Application Identifiers (key AIs with expected formats)
_GS1_AI_SPECS: dict[str, tuple[str, int | None]] = {
    # AI: (description, fixed_length or None for variable)
    "00": ("SSCC", 18),
    "01": ("GTIN", 14),
    "02": ("Content GTIN", 14),
    "10": ("Batch/Lot", None),
    "11": ("Production Date", 6),
    "13": ("Packaging Date", 6),
    "15": ("Best Before Date", 6),
    "17": ("Expiry Date", 6),
    "20": ("Variant", 2),
    "21": ("Serial Number", None),
    "37": ("Count", None),
    "310": ("Net Weight kg", 6),
    "400": ("Customer Order Number", None),
}


def _compute_check_digit(digits: str) -> int:
    """Compute GS1 check digit for a numeric string (without check digit).

    Works for GTIN-8, GTIN-12, GTIN-13, GTIN-14.
    The rightmost digit position alternates weight 3, 1, 3, 1... from right to left.
    """
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        total += d * (3 if i % 2 == 0 else 1)
    return (10 - (total % 10)) % 10


def _expand_upce_to_upca(upce_data: str) -> str | None:
    """Expand UPC-E (6 or 8 digits) to UPC-A (12 digits) for check digit verification."""
    # Strip leading 0 and trailing check digit if present
    if len(upce_data) == 8:
        core = upce_data[1:7]
    elif len(upce_data) == 6:
        core = upce_data
    else:
        return None

    if not core.isdigit():
        return None

    last = core[5]
    if last in ("0", "1", "2"):
        mfr = core[0:2] + last + "00"
        prod = "00" + core[2:5]
    elif last == "3":
        mfr = core[0:3] + "00"
        prod = "000" + core[3:5]
    elif last == "4":
        mfr = core[0:4] + "0"
        prod = "0000" + core[4]
    else:  # 5-9
        mfr = core[0:5]
        prod = "0000" + last

    upca_no_check = "0" + mfr + prod
    check = _compute_check_digit(upca_no_check)
    return upca_no_check + str(check)


def _validate_url(url: str) -> tuple[bool, str]:  # skipcq: PY-R1000
    """Validate a URL and return (is_valid, reason)."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            return False, "missing scheme (http/https)"
        if parsed.scheme not in ("http", "https", "ftp", "ftps", "mailto"):
            return False, f"unsupported scheme '{parsed.scheme}'"
        if not parsed.netloc and parsed.scheme not in ("mailto",):
            return False, "missing host/domain"
        # Check for obviously invalid hostnames
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


def _parse_gs1_element_string(data: str) -> list[tuple[str, str, bool]]:  # skipcq: PY-R1000
    """Parse GS1 element string and return list of (ai, value, is_valid) tuples."""
    # Strip GS1 symbology identifiers
    content = re.sub(r"^\](?:d2|C1|e0|Q3)", "", data)

    results: list[tuple[str, str, bool]] = []
    pos = 0

    while pos < len(content):
        matched = False
        # Try 3-digit AIs first, then 2-digit
        for ai_len in (3, 2):
            if pos + ai_len > len(content):
                continue
            ai = content[pos : pos + ai_len]
            if ai in _GS1_AI_SPECS:
                _desc, fixed_len = _GS1_AI_SPECS[ai]
                pos += ai_len
                if fixed_len is not None:
                    value = content[pos : pos + fixed_len]
                    pos += fixed_len
                    is_valid = len(value) == fixed_len and value.replace(" ", "").isalnum()
                else:
                    # Variable-length: read until GS separator or end
                    end = content.find("\x1d", pos)
                    if end == -1:
                        end = len(content)
                    value = content[pos:end]
                    pos = end + 1 if end < len(content) else end
                    is_valid = len(value) > 0
                results.append((ai, value, is_valid))
                matched = True
                break

        if not matched:
            # Skip unknown character
            pos += 1

    return results


@register_ai_analyzer
class BarcodeContentValidation(BaseAIAnalyzer):
    """Validate barcode content: check digits, URL validity, GS1 AI structure."""

    category = "barcode"
    feature_slug = "barcode_content_validation"
    tier = "cpu"
    credits_per_run = 1

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses pdf_bytes
        # only. document + events + ai_config declared but never used.
        pdf_bytes = ctx.pdf_bytes

        if not (_HAS_PIL and _HAS_PYZBAR):
            logger.debug("barcode_content_validation: pyzbar or Pillow not available — skipping")
            return []

        findings: list[Finding] = []

        services = ctx.services
        if services is None or services.renderer is None:
            logger.debug("barcode_content: ctx.services.renderer unavailable, skipping")
            return []

        try:
            page_images = services.renderer.render_all_pages(pdf_bytes, dpi=300)
        except RuntimeError:
            logger.debug("barcode_content_validation: PDF rendering backend unavailable")
            return []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            img = PILImage.open(io.BytesIO(png_bytes))

            decoded_items = _pyzbar.decode(img)

            # Also decode DataMatrix if available
            dm_items: list[Any] = []
            if _HAS_DMTX:
                dm_items = _dmtx.decode(img)

            # Process 1D/QR barcodes from pyzbar
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

                # --- Check digit verification for GTIN types ---
                if sym_type in _GTIN_TYPES:
                    findings.extend(self._validate_gtin_check_digit(sym_type, data, page_num, bbox))

                # --- URL validation for QR codes ---
                if sym_type == "QRCODE" and (
                    data.startswith("http://")
                    or data.startswith("https://")
                    or data.startswith("ftp://")
                ):
                    is_valid, reason = _validate_url(data)
                    if not is_valid:
                        findings.append(
                            self._make_finding(
                                inspection_id="LPDF_BCV_002",
                                severity=Severity.WARNING,
                                message=(
                                    f"QR code on page {page_num} contains invalid "
                                    f"URL: {reason} — '{data[:100]}'"
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

            # Process DataMatrix for GS1 AI validation
            for item in dm_items:
                data = item.data.decode("utf-8", errors="replace")
                rect = item.rect
                bbox = (
                    float(rect.left),
                    float(rect.top),
                    float(rect.left + rect.width),
                    float(rect.top + rect.height),
                )

                # Check if this is a GS1 DataMatrix (starts with ]d2 or contains AIs)
                if data.startswith("]d2") or _AI_01_RE.search(data):
                    ai_fields = _parse_gs1_element_string(data)
                    for ai, value, is_valid in ai_fields:
                        if not is_valid:
                            findings.append(
                                self._make_finding(
                                    inspection_id="LPDF_BCV_003",
                                    severity=Severity.WARNING,
                                    message=(
                                        f"DataMatrix on page {page_num}: GS1 AI "
                                        f"({ai}) has invalid value '{value}'"
                                    ),
                                    page_num=page_num,
                                    details={
                                        "ai": ai,
                                        "ai_description": _GS1_AI_SPECS.get(ai, ("Unknown",))[0],
                                        "value": value,
                                    },
                                    bbox=bbox,
                                    iso_clause="GS1 General Specifications 3.2",
                                    object_type="barcode",
                                )
                            )

                    # Validate GTIN check digit if AI 01 present
                    if any(ai == "01" for ai, _, _ in ai_fields):
                        for ai, value, _ in ai_fields:
                            if ai == "01" and len(value) == 14 and value.isdigit():
                                expected = _compute_check_digit(value[:13])
                                if expected != int(value[13]):
                                    findings.append(
                                        self._make_finding(
                                            inspection_id="LPDF_BCV_001",
                                            severity=Severity.ERROR,
                                            message=(
                                                f"DataMatrix on page {page_num}: "
                                                f"GTIN {value} has invalid check "
                                                f"digit (expected {expected}, "
                                                f"got {value[13]})"
                                            ),
                                            page_num=page_num,
                                            details={
                                                "gtin": value,
                                                "expected_check": expected,
                                                "actual_check": int(value[13]),
                                            },
                                            bbox=bbox,
                                            iso_clause="GS1 General Specifications 7.9",
                                            object_type="barcode",
                                        )
                                    )

        return findings

    def _validate_gtin_check_digit(  # skipcq: PY-R1000
        self,
        sym_type: str,
        data: str,
        page_num: int,
        bbox: tuple[float, float, float, float],
    ) -> list[Finding]:
        """Validate GTIN/EAN/UPC check digit and return findings."""
        findings: list[Finding] = []

        if sym_type == "EAN13":
            if len(data) == 13 and data.isdigit():
                expected = _compute_check_digit(data[:12])
                if expected != int(data[12]):
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_BCV_001",
                            severity=Severity.ERROR,
                            message=(
                                f"EAN-13 on page {page_num}: check digit invalid "
                                f"(expected {expected}, got {data[12]})"
                            ),
                            page_num=page_num,
                            details={
                                "barcode_data": data,
                                "expected_check": expected,
                                "actual_check": int(data[12]),
                                "symbology": "EAN-13",
                            },
                            bbox=bbox,
                            iso_clause="GS1 General Specifications 7.9",
                            object_type="barcode",
                        )
                    )

        elif sym_type == "UPCA":
            if len(data) == 12 and data.isdigit():
                expected = _compute_check_digit(data[:11])
                if expected != int(data[11]):
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_BCV_001",
                            severity=Severity.ERROR,
                            message=(
                                f"UPC-A on page {page_num}: check digit invalid "
                                f"(expected {expected}, got {data[11]})"
                            ),
                            page_num=page_num,
                            details={
                                "barcode_data": data,
                                "expected_check": expected,
                                "actual_check": int(data[11]),
                                "symbology": "UPC-A",
                            },
                            bbox=bbox,
                            iso_clause="GS1 General Specifications 7.9",
                            object_type="barcode",
                        )
                    )

        elif sym_type == "UPCE":
            expanded = _expand_upce_to_upca(data)
            if expanded is not None:
                expected = _compute_check_digit(expanded[:11])
                if expected != int(expanded[11]):
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_BCV_001",
                            severity=Severity.ERROR,
                            message=(
                                f"UPC-E on page {page_num}: check digit invalid "
                                f"when expanded to UPC-A {expanded}"
                            ),
                            page_num=page_num,
                            details={
                                "barcode_data": data,
                                "expanded_upca": expanded,
                                "symbology": "UPC-E",
                            },
                            bbox=bbox,
                            iso_clause="GS1 General Specifications 7.9",
                            object_type="barcode",
                        )
                    )

        return findings


# Re-export the AI 01 regex for use by other modules
_AI_01_RE = re.compile(r"01(\d{14})")
