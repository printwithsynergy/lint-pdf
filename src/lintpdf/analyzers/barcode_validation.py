"""GS1 AI / UDI / EU DPP content validators (T5-N06 + T5-N08).

These functions take a decoded barcode payload (from zxing-cpp or
similar) and validate the encoded content against:

- GS1 AI syntax (ISO/IEC 15418, GS1 General Specifications) for
  GS1-128 / DataMatrix / QR codes carrying GS1 element strings.
  Emits ``LPDF_BARCODE_GS1_AI``.
- US FDA UDI format (21 CFR 801) — GS1 AI 01 + 17 + 10/21 for
  medical-device labels. Emits ``LPDF_BARCODE_UDI``.
- EU Digital Product Passport — URL pattern targeting the DPP
  registry. Emits ``LPDF_BARCODE_EU_DPP``.

Pure-Python validators, no external dependencies. Callers are
expected to invoke them when they have a decoded barcode string;
they emit zero findings on inputs that don't match the relevant
syntax.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lintpdf.analyzers.finding import Finding, Severity

__all__ = [
    "GS1_AI_SCHEMA",
    "validate_eu_dpp_payload",
    "validate_gs1_ai_payload",
    "validate_udi_payload",
]


@dataclass(frozen=True)
class _AISpec:
    ai: str
    fixed_length: int  # 0 if variable-length
    regex: re.Pattern[str]
    description: str


# Subset of GS1 AIs that cover ~95 % of real-world traffic on print
# labels: identifiers, dates, lot/serial, weights/volumes, and the
# common URL/URI AIs (8200 / 8201 / 8202).
GS1_AI_SCHEMA: dict[str, _AISpec] = {
    "00": _AISpec("00", 18, re.compile(r"\d{18}"), "SSCC"),
    "01": _AISpec("01", 14, re.compile(r"\d{14}"), "GTIN"),
    "02": _AISpec("02", 14, re.compile(r"\d{14}"), "GTIN of contained items"),
    "10": _AISpec("10", 0, re.compile(r"[\x21-\x7e]{1,20}"), "Batch / Lot number"),
    "11": _AISpec("11", 6, re.compile(r"\d{6}"), "Production date YYMMDD"),
    "12": _AISpec("12", 6, re.compile(r"\d{6}"), "Due date YYMMDD"),
    "13": _AISpec("13", 6, re.compile(r"\d{6}"), "Packaging date YYMMDD"),
    "15": _AISpec("15", 6, re.compile(r"\d{6}"), "Best before date YYMMDD"),
    "16": _AISpec("16", 6, re.compile(r"\d{6}"), "Sell by date YYMMDD"),
    "17": _AISpec("17", 6, re.compile(r"\d{6}"), "Expiration date YYMMDD"),
    "20": _AISpec("20", 2, re.compile(r"\d{2}"), "Variant"),
    "21": _AISpec("21", 0, re.compile(r"[\x21-\x7e]{1,20}"), "Serial number"),
    "22": _AISpec("22", 0, re.compile(r"[\x21-\x7e]{1,20}"), "Consumer product variant"),
    "30": _AISpec("30", 0, re.compile(r"\d{1,8}"), "Variable count"),
    "37": _AISpec("37", 0, re.compile(r"\d{1,8}"), "Number of units in container"),
    "240": _AISpec("240", 0, re.compile(r"[\x21-\x7e]{1,30}"), "Additional product ID"),
    "241": _AISpec("241", 0, re.compile(r"[\x21-\x7e]{1,30}"), "Customer part number"),
    "250": _AISpec("250", 0, re.compile(r"[\x21-\x7e]{1,30}"), "Secondary serial"),
    "251": _AISpec("251", 0, re.compile(r"[\x21-\x7e]{1,30}"), "Reference to source"),
    "310": _AISpec("310", 7, re.compile(r"[0-5]\d{6}"), "Net weight (kg) — implicit decimal"),
    "320": _AISpec("320", 7, re.compile(r"[0-5]\d{6}"), "Net weight (lb) — implicit decimal"),
    "8200": _AISpec("8200", 0, re.compile(r"[\x21-\x7e]{1,70}"), "Extended packaging URL"),
    "8201": _AISpec("8201", 0, re.compile(r"[\x21-\x7e]{1,70}"), "Component / part identifier URL"),
    "8202": _AISpec("8202", 0, re.compile(r"[\x21-\x7e]{1,70}"), "Trade item URL"),
}


_FNC1 = "\x1d"  # Group separator used by GS1 to terminate variable-length AIs


def _strip_fnc1_prefix(payload: str) -> str:
    """GS1-128 / GS1 DataMatrix payloads frequently start with a
    leading ``]C1`` / ``]Q3`` AIM identifier or a literal FNC1; strip
    the leading marker so the AI walker starts at the first AI."""
    if payload.startswith("]C1") or payload.startswith("]Q3") or payload.startswith("]e0"):
        return payload[3:]
    if payload.startswith(_FNC1):
        return payload[1:]
    return payload


def _walk_gs1_payload(payload: str) -> list[tuple[str, str, str | None]]:
    """Walk an FNC1-separated GS1 element string into ``(ai, value, error)``
    triples. Emit one entry per AI consumed; ``error`` is non-None
    when the value didn't satisfy the AI's syntax.
    """
    payload = _strip_fnc1_prefix(payload)
    out: list[tuple[str, str, str | None]] = []
    pos = 0
    while pos < len(payload):
        # AI prefixes are 2-4 digits; try the longest match first.
        ai: str | None = None
        for length in (4, 3, 2):
            candidate = payload[pos : pos + length]
            if candidate in GS1_AI_SCHEMA:
                ai = candidate
                pos += length
                break
        if ai is None:
            out.append(("?", payload[pos:], "unknown_ai"))
            return out
        spec = GS1_AI_SCHEMA[ai]
        if spec.fixed_length:
            value = payload[pos : pos + spec.fixed_length]
            pos += spec.fixed_length
        else:
            sep = payload.find(_FNC1, pos)
            if sep == -1:
                value = payload[pos:]
                pos = len(payload)
            else:
                value = payload[pos:sep]
                pos = sep + 1
        if not spec.regex.fullmatch(value):
            out.append((ai, value, "format_violation"))
        else:
            out.append((ai, value, None))
    return out


def validate_gs1_ai_payload(
    payload: str,
    *,
    page_num: int,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[Finding]:
    """T5-N08 — when ``payload`` looks like a GS1 element string, walk
    its AIs and emit ``LPDF_BARCODE_GS1_AI`` if any AI fails its
    syntax check (or an unknown AI is encountered)."""
    if not payload:
        return []
    if not (payload.startswith("01") or _FNC1 in payload or payload.startswith("]C1")):
        # Doesn't look like GS1 element string — silent.
        return []

    walked = _walk_gs1_payload(payload)
    errors = [(ai, val, err) for ai, val, err in walked if err]
    if not errors:
        return []

    return [
        Finding(
            inspection_id="LPDF_BARCODE_GS1_AI",
            severity=Severity.WARNING,
            message=(
                f"Barcode payload contains {len(errors)} GS1 AI syntax issue(s) "
                f"(first: AI {errors[0][0]} = '{errors[0][1]}' — {errors[0][2]})"
            ),
            page_num=page_num,
            details={
                "errors": [{"ai": ai, "value": val, "issue": err} for ai, val, err in errors],
                "ai_count": len(walked),
                "regulation": "GS1 General Specifications / ISO/IEC 15418",
            },
            iso_clause="ISO/IEC 15418",
            bbox=bbox,
            object_type="barcode",
        )
    ]


_UDI_REQUIRED_AIS = ("01",)
_UDI_RECOMMENDED_AIS = ("17", "10", "21")


def validate_udi_payload(
    payload: str,
    *,
    page_num: int,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[Finding]:
    """T5-N06 — when ``payload`` looks like a UDI-DI element string
    (FDA 21 CFR 801 / EU MDR 2017/745), validate the AI sequence."""
    if not payload:
        return []
    walked = _walk_gs1_payload(payload)
    if not walked:
        return []
    seen_ais = {ai for ai, _val, _err in walked if ai != "?"}
    if "01" not in seen_ais:
        # Not a UDI candidate — silent.
        return []

    issues: list[str] = []
    for ai in _UDI_REQUIRED_AIS:
        if ai not in seen_ais:
            issues.append(f"missing_required_ai_{ai}")
    rec_present = sum(1 for ai in _UDI_RECOMMENDED_AIS if ai in seen_ais)
    if rec_present == 0:
        issues.append("missing_all_recommended_production_ais")
    if not issues:
        return []

    return [
        Finding(
            inspection_id="LPDF_BARCODE_UDI",
            severity=Severity.WARNING,
            message=(f"UDI barcode on page {page_num} has structural issues: {', '.join(issues)}"),
            page_num=page_num,
            details={
                "issues": issues,
                "seen_ais": sorted(seen_ais),
                "regulation": "FDA 21 CFR 801 (UDI) / EU MDR 2017/745",
            },
            iso_clause="FDA 21 CFR 801.40",
            bbox=bbox,
            object_type="barcode",
        )
    ]


_EU_DPP_PATTERN = re.compile(
    r"https?://[^/]*?(?:dpp|digitalproductpassport|europa\.eu/dpp)[^\s]*",
    re.IGNORECASE,
)


def validate_eu_dpp_payload(
    payload: str,
    *,
    page_num: int,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[Finding]:
    """T5-N06 — when ``payload`` is a URL targeting the EU Digital
    Product Passport, validate the URL is well-formed and uses
    HTTPS (DPP regulation requires authenticated access)."""
    if not payload:
        return []
    match = _EU_DPP_PATTERN.search(payload)
    if not match:
        return []
    url = match.group(0)
    issues: list[str] = []
    if not url.startswith("https://"):
        issues.append("non_https_dpp_url")
    if " " in url or "\n" in url or "\t" in url:
        issues.append("malformed_url_whitespace")
    if not issues:
        return []

    return [
        Finding(
            inspection_id="LPDF_BARCODE_EU_DPP",
            severity=Severity.WARNING,
            message=(f"EU DPP URL on page {page_num} has issues: {', '.join(issues)}"),
            page_num=page_num,
            details={
                "issues": issues,
                "url": url,
                "regulation": "EU Digital Product Passport (Regulation 2024/1781)",
            },
            iso_clause="EU Regulation 2024/1781",
            bbox=bbox,
            object_type="barcode",
        )
    ]
