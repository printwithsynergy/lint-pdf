"""Barcode predicates — Tier-0 Batch 11 (final).

Per universe enumeration §4.11. Predicates over a barcode object emitted
by the barcode analyzer (or any classified region carrying a symbology
tag). Both attribute-style objects and Mapping shapes are accepted.

Symbology vocabulary normalized to upper-case canonical names:

  Linear (1D):  EAN-13, EAN-8, UPC-A, UPC-E, CODE128, CODE39, CODE93,
                ITF, ITF-14, CODABAR
  Matrix (2D):  QR, DATAMATRIX, PDF417, AZTEC, MAXICODE
"""

from __future__ import annotations

import re
from typing import Any

from lintpdf.primitives import register

_LINEAR = frozenset(
    {
        "EAN-13",
        "EAN-8",
        "UPC-A",
        "UPC-E",
        "CODE128",
        "CODE39",
        "CODE93",
        "ITF",
        "ITF-14",
        "INTERLEAVED2OF5",
        "CODABAR",
    }
)

_MATRIX = frozenset(
    {
        "QR",
        "DATAMATRIX",
        "PDF417",
        "AZTEC",
        "MAXICODE",
    }
)


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
    """Fetch by attribute or Mapping with /-prefix fallback."""
    if obj is None:
        return default
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
        if hasattr(obj, "get"):
            v = obj.get(k)
            if v is not None:
                return v
    return default


def _normalize_symbology(value: Any) -> str | None:
    """Coerce a symbology label to canonical upper-case form."""
    if value is None:
        return None
    s = str(value).strip().upper()
    s = s.replace("_", "-").replace(" ", "")
    # Common aliases
    aliases = {
        "DATAMATRIX": "DATAMATRIX",
        "DATA-MATRIX": "DATAMATRIX",
        "QRCODE": "QR",
        "QR-CODE": "QR",
        "CODE-128": "CODE128",
        "CODE-39": "CODE39",
        "CODE-93": "CODE93",
        "PDF-417": "PDF417",
        "INTERLEAVED2OF5": "ITF",
        "I2OF5": "ITF",
        "ITF14": "ITF-14",
        "EAN13": "EAN-13",
        "EAN8": "EAN-8",
        "UPCA": "UPC-A",
        "UPCE": "UPC-E",
    }
    return aliases.get(s, s)


# ---- predicates --------------------------------------------------------


def is_barcode(obj: Any) -> bool:
    """True iff the object carries a barcode classification or symbology tag."""
    if bool(_get(obj, "is_barcode", default=False)):
        return True
    cls = _get(obj, "object_class", "kind", "type")
    if str(cls).lower() in ("barcode", "qr", "datamatrix"):
        return True
    return symbology(obj) is not None


def symbology(obj: Any) -> str | None:
    """Return the canonical symbology name (e.g. ``"EAN-13"``) or None."""
    s = _get(obj, "symbology", "barcode_type", "format")
    return _normalize_symbology(s)


def is_1d(obj: Any) -> bool:
    """True iff the symbology is linear (1D)."""
    s = symbology(obj)
    return s in _LINEAR if s else False


def is_2d(obj: Any) -> bool:
    """True iff the symbology is 2D / matrix."""
    s = symbology(obj)
    return s in _MATRIX if s else False


def narrow_bar_width(obj: Any) -> float | None:
    """Return narrowest bar width (or X-dimension) in points; None if unknown."""
    val = _get(obj, "narrow_bar_width", "x_dimension", "min_bar_width")
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def quiet_zone(obj: Any) -> tuple[float, float, float, float] | None:
    """Return per-side quiet zones in points (left, top, right, bottom), or None."""
    qz = _get(obj, "quiet_zone", "quiet_zones")
    if qz is None:
        return None
    if not hasattr(qz, "__iter__"):
        return None
    try:
        items = list(qz)
    except TypeError:
        return None
    if len(items) != 4:
        return None
    try:
        return (float(items[0]), float(items[1]), float(items[2]), float(items[3]))
    except (TypeError, ValueError):
        return None


def is_decodable(obj: Any) -> bool:
    """True iff a decoder successfully read the barcode (decoded value present)."""
    if bool(_get(obj, "is_decodable", "decodable")):
        return True
    return decoded_value(obj) is not None


def decoded_value(obj: Any) -> str | None:
    """Return the decoded payload string, or None when no decoder result."""
    val = _get(obj, "decoded_value", "value", "payload", "text")
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val)


_GS1_AI_RE = re.compile(r"\((\d{2,4})\)")


def gs1_compliant(obj: Any) -> bool:
    """True iff the decoded payload includes valid GS1 Application Identifiers.

    Recognizes either ``(NN)`` parenthesized AI form or FNC1-prefixed payload.
    Returns False for non-GS1 symbologies (UPC/EAN handled separately).
    """
    explicit = _get(obj, "gs1_compliant", default=None)
    if isinstance(explicit, bool):
        return explicit
    payload = decoded_value(obj)
    if payload is None:
        return False
    if payload.startswith("]C1") or payload.startswith("\x1d"):
        return True
    return _GS1_AI_RE.search(payload) is not None


# ---- registry ---------------------------------------------------------

for _name in (
    "is_barcode",
    "symbology",
    "is_1d",
    "is_2d",
    "narrow_bar_width",
    "quiet_zone",
    "is_decodable",
    "decoded_value",
    "gs1_compliant",
):
    register("barcode", _name, globals()[_name])

del _name


__all__ = [
    "decoded_value",
    "gs1_compliant",
    "is_1d",
    "is_2d",
    "is_barcode",
    "is_decodable",
    "narrow_bar_width",
    "quiet_zone",
    "symbology",
]
