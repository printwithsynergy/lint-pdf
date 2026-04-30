"""Pharma serialization validation — EU FMD DataMatrix compliance."""

from __future__ import annotations

import io
import logging
import re
from typing import TYPE_CHECKING, Any

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

try:
    from pylibdmtx import pylibdmtx as _dmtx

    _HAS_DMTX = True
except ImportError:
    _HAS_DMTX = False
    _dmtx = None

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

# GS1 Application Identifiers for pharma serialisation
_GS1_FNC1 = "\x1d"  # GS1 FNC1 separator (Group Separator)
_AI_GTIN = "01"  # AI 01: GTIN (14 digits)
_AI_SERIAL = "21"  # AI 21: Serial number (up to 20 chars)
_AI_BATCH = "10"  # AI 10: Batch/Lot number (up to 20 chars)
_AI_EXPIRY = "17"  # AI 17: Expiry date (YYMMDD, 6 digits)

# Regex patterns for AI field extraction from GS1 element strings
# The DataMatrix content starts with FNC1 (]d2 prefix for GS1 DataMatrix)
_GS1_DM_PREFIX = re.compile(r"^\]d2")

# AI patterns (fixed-length AIs don't need FNC1 separator)
_AI_01_RE = re.compile(r"01(\d{14})")  # GTIN: fixed 14 digits
_AI_17_RE = re.compile(r"17(\d{6})")  # Expiry: fixed 6 digits (YYMMDD)
_AI_10_RE = re.compile(r"10([^\x1d]{1,20})")  # Batch: variable, up to 20
_AI_21_RE = re.compile(r"21([^\x1d]{1,20})")  # Serial: variable, up to 20


def _parse_gs1_ais(data: str) -> dict[str, str | None]:
    """Parse GS1 Application Identifiers from DataMatrix content.

    Returns dict with keys 'gtin', 'serial', 'batch', 'expiry' (or None if absent).
    """
    # Strip GS1 DataMatrix symbology identifier if present
    content = _GS1_DM_PREFIX.sub("", data)

    result: dict[str, str | None] = {
        "gtin": None,
        "serial": None,
        "batch": None,
        "expiry": None,
    }

    m = _AI_01_RE.search(content)
    if m:
        result["gtin"] = m.group(1)

    m = _AI_21_RE.search(content)
    if m:
        result["serial"] = m.group(1)

    m = _AI_10_RE.search(content)
    if m:
        result["batch"] = m.group(1)

    m = _AI_17_RE.search(content)
    if m:
        result["expiry"] = m.group(1)

    return result


def _validate_expiry_date(yymmdd: str) -> bool:
    """Validate a YYMMDD expiry date string."""
    if len(yymmdd) != 6 or not yymmdd.isdigit():
        return False
    _yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    if mm < 1 or mm > 12:
        return False
    # DD=00 is valid in GS1 (means last day of month)
    return not dd > 31


def _is_pharma_context(_document: Any, ai_config: Any) -> bool:
    """Check if the document is likely a pharmaceutical package.

    Uses ai_config hints or document metadata to determine if pharma checks apply.
    """
    # If ai_config explicitly flags pharma context
    if ai_config is not None:
        config_dict = getattr(ai_config, "config", None) or {}
        if isinstance(config_dict, dict) and (
            config_dict.get("pharma_mode") or config_dict.get("eu_fmd")
        ):
            return True

    # Otherwise, assume pharma checks apply if DataMatrix barcodes are present
    # (the analyzer will be invoked only when the feature is explicitly enabled)
    return True


@register_ai_analyzer
class PharmaSerialization(BaseAIAnalyzer):
    """Validate EU FMD pharmaceutical DataMatrix (ECC200, ISO/IEC 16022)."""

    category = "barcode"
    feature_slug = "pharma_serialization_validation"
    tier = "cpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        if not (_HAS_PIL and (_HAS_DMTX or _HAS_PYZBAR)):
            logger.debug(
                "pharma_serialization: pylibdmtx/pyzbar or Pillow not available — skipping"
            )
            return []

        if not _is_pharma_context(document, ai_config):
            return []

        from lintpdf.ai.rendering import render_all_pages

        findings: list[Finding] = []

        try:
            page_images = render_all_pages(pdf_bytes, dpi=300)
        except RuntimeError:
            logger.debug("pharma_serialization: PDF rendering backend unavailable")
            return []

        dm_found = False
        other_2d_count = 0

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            img = PILImage.open(io.BytesIO(png_bytes))

            # --- Detect DataMatrix barcodes ---
            dm_items: list[Any] = []
            if _HAS_DMTX:
                dm_items = _dmtx.decode(img)

            # --- Also check for competing 2D barcodes (QR, Aztec, etc.) ---
            if _HAS_PYZBAR:
                pyzbar_items = _pyzbar.decode(img)
                for item in pyzbar_items:
                    if item.type == "QRCODE":
                        other_2d_count += 1

            for item in dm_items:
                dm_found = True
                data = item.data.decode("utf-8", errors="replace")
                rect = item.rect
                bbox = (
                    float(rect.left),
                    float(rect.top),
                    float(rect.left + rect.width),
                    float(rect.top + rect.height),
                )

                # Parse GS1 AI structure
                ais = _parse_gs1_ais(data)

                # --- Check for required AIs ---
                missing_ais: list[str] = []
                if ais["gtin"] is None:
                    missing_ais.append("AI 01 (GTIN)")
                if ais["serial"] is None:
                    missing_ais.append("AI 21 (Serial Number)")
                if ais["batch"] is None:
                    missing_ais.append("AI 10 (Batch/Lot)")
                if ais["expiry"] is None:
                    missing_ais.append("AI 17 (Expiry Date)")

                if missing_ais:
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_PS_001",
                            severity=Severity.ERROR,
                            message=(
                                f"Pharma DataMatrix on page {page_num} is missing "
                                f"required EU FMD fields: {', '.join(missing_ais)}"
                            ),
                            page_num=page_num,
                            details={
                                "decoded_data": data,
                                "parsed_ais": ais,
                                "missing_ais": missing_ais,
                            },
                            bbox=bbox,
                            iso_clause="EU FMD 2011/62/EU, ISO/IEC 16022",
                            object_type="barcode",
                        )
                    )

                # --- Validate GTIN check digit ---
                if ais["gtin"] is not None:
                    gtin = ais["gtin"]
                    if len(gtin) == 14 and gtin.isdigit():
                        check = _compute_gtin_check_digit(gtin[:13])
                        if check != int(gtin[13]):
                            findings.append(
                                self._make_finding(
                                    inspection_id="LPDF_PS_002",
                                    severity=Severity.ERROR,
                                    message=(
                                        f"Pharma DataMatrix on page {page_num}: "
                                        f"GTIN {gtin} has invalid check digit "
                                        f"(expected {check}, got {gtin[13]})"
                                    ),
                                    page_num=page_num,
                                    details={
                                        "gtin": gtin,
                                        "expected_check": check,
                                        "actual_check": int(gtin[13]),
                                    },
                                    bbox=bbox,
                                    iso_clause="GS1 General Specifications 7.9",
                                    object_type="barcode",
                                )
                            )

                # --- Validate expiry date format ---
                if ais["expiry"] is not None and not _validate_expiry_date(ais["expiry"]):
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_PS_003",
                            severity=Severity.ERROR,
                            message=(
                                f"Pharma DataMatrix on page {page_num}: "
                                f"invalid expiry date format '{ais['expiry']}' "
                                f"(expected YYMMDD)"
                            ),
                            page_num=page_num,
                            details={
                                "expiry_raw": ais["expiry"],
                            },
                            bbox=bbox,
                            iso_clause="GS1 General Specifications 3.4.3",
                            object_type="barcode",
                        )
                    )

                # --- Report successful parse as advisory ---
                if not missing_ais:
                    findings.append(
                        self._make_finding(
                            inspection_id="LPDF_PS_004",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Pharma DataMatrix on page {page_num}: "
                                f"all EU FMD fields present — "
                                f"GTIN {ais['gtin']}, Serial {ais['serial']}, "
                                f"Batch {ais['batch']}, Expiry {ais['expiry']}"
                            ),
                            page_num=page_num,
                            details={
                                "parsed_ais": ais,
                            },
                            bbox=bbox,
                            object_type="barcode",
                        )
                    )

        # --- No DataMatrix found on a pharma document ---
        if not dm_found:
            findings.append(
                self._make_finding(
                    inspection_id="LPDF_PS_005",
                    severity=Severity.ERROR,
                    message=(
                        "No DataMatrix barcode found — EU FMD requires a "
                        "GS1 DataMatrix (ECC200) on pharmaceutical packaging"
                    ),
                    iso_clause="EU FMD 2011/62/EU",
                    object_type="barcode",
                )
            )

        # --- Competing 2D barcodes ---
        if other_2d_count > 0:
            findings.append(
                self._make_finding(
                    inspection_id="LPDF_PS_006",
                    severity=Severity.WARNING,
                    message=(
                        f"Found {other_2d_count} non-DataMatrix 2D barcode(s) "
                        f"alongside pharma DataMatrix — may cause scanning confusion"
                    ),
                    details={"other_2d_count": other_2d_count},
                    object_type="barcode",
                )
            )

        return findings


def _compute_gtin_check_digit(digits_13: str) -> int:
    """Compute GS1 check digit for 13-digit string (GTIN-14 without check)."""
    total = 0
    for i, ch in enumerate(digits_13):
        d = int(ch)
        total += d * (3 if i % 2 == 0 else 1)
    return (10 - (total % 10)) % 10
