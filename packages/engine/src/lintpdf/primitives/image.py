"""Image predicates — Tier-0 Batch 08.

Per universe enumeration §4.8. Predicates over a PDF image XObject (or a
parser-emitted ImageRenderedEvent). Accepts both attribute-style objects
and Mapping shapes.

Image dictionaries follow ISO 32000-2 §8.9: Width, Height, BitsPerComponent,
ColorSpace, Filter, DecodeParms, SMask, etc. Image XObjects also have an
internal stream; primitives here inspect the dictionary, not the pixel data.
"""

from __future__ import annotations

import math
from typing import Any

from lintpdf.primitives import register


def _get(image: Any, *keys: str, default: Any = None) -> Any:
    """Fetch a value from event-style object or Mapping; tries multiple keys."""
    if image is None:
        return default
    for k in keys:
        if hasattr(image, k):
            v = getattr(image, k)
            if v is not None:
                return v
        if hasattr(image, "get"):
            v = image.get(k)
            if v is not None:
                return v
            v = image.get("/" + k)
            if v is not None:
                return v
    return default


def _normalize_filter(value: Any) -> str | list[str] | None:
    """Coerce a filter operand to str or list[str]; strip leading slashes."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for v in value:
            normalized = _normalize_str(v)
            if normalized is not None:
                out.append(normalized)
        return out
    return _normalize_str(value)


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.lstrip("/")
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="replace").lstrip("/")
    return str(value).lstrip("/")


# ---- predicates ---------------------------------------------------------


def color_space(image: Any) -> str | None:
    """Return the image's color-space name (DeviceRGB / DeviceCMYK / etc.) or None."""
    cs = _get(image, "color_space", "ColorSpace", "CS")
    if cs is None:
        return None
    if isinstance(cs, (list, tuple)) and cs:
        return _normalize_str(cs[0])
    return _normalize_str(cs)


def bit_depth(image: Any) -> int:
    """Return BitsPerComponent for the image. Default 8 per PDF spec."""
    bd = _get(image, "bit_depth", "BitsPerComponent", "BPC")
    if bd is None:
        return 8
    try:
        return int(bd)
    except (TypeError, ValueError):
        return 8


def filter_name(image: Any) -> str | list[str] | None:
    """Return the Filter chain (single str or list of str), or None."""
    f = _get(image, "filter", "Filter", "F")
    return _normalize_filter(f)


def has_jpeg(image: Any) -> bool:
    """True iff DCTDecode appears in the filter chain."""
    return _has_filter(image, "DCTDecode")


def has_jpeg2000(image: Any) -> bool:
    """True iff JPXDecode appears in the filter chain."""
    return _has_filter(image, "JPXDecode")


def has_jbig2(image: Any) -> bool:
    """True iff JBIG2Decode appears in the filter chain."""
    return _has_filter(image, "JBIG2Decode")


def _has_filter(image: Any, target: str) -> bool:
    f = filter_name(image)
    if isinstance(f, list):
        return target in f
    return f == target


def dpi_native(image: Any) -> tuple[float, float] | None:
    """Return native (pre-CTM) DPI based on pixel dimensions and rendered size.

    Requires either a ``rendered_size_pt`` (width_pt, height_pt) hint OR
    pixel dimensions divided by a known size in points. Returns None when
    the rendered size is unknown.
    """
    width_px = _get(image, "width", "Width")
    height_px = _get(image, "height", "Height")
    rendered = _get(image, "rendered_size_pt", "size_pt")
    if width_px is None or height_px is None or rendered is None:
        return None
    if not isinstance(rendered, (list, tuple)) or len(rendered) < 2:
        return None
    try:
        w_pt, h_pt = float(rendered[0]), float(rendered[1])
        if w_pt <= 0 or h_pt <= 0:
            return None
        return (float(width_px) / w_pt * 72.0, float(height_px) / h_pt * 72.0)
    except (TypeError, ValueError):
        return None


def dpi_effective(
    image: Any,
    ctm: tuple[float, float, float, float, float, float] | None = None,
) -> tuple[float, float] | None:
    """Return rendered DPI after CTM scaling.

    Image XObjects render in the unit square; ``Width x Height`` pixels are
    scaled to 1x1 user-space units, then transformed by CTM. Effective
    rendered size in points = ``(sx, sy)`` magnitudes from CTM.
    DPI = pixels / inches = pixels / (size_pt / 72).
    """
    width_px = _get(image, "width", "Width")
    height_px = _get(image, "height", "Height")
    if width_px is None or height_px is None or ctm is None or len(ctm) < 4:
        return dpi_native(image)
    try:
        sx = math.hypot(float(ctm[0]), float(ctm[1]))
        sy = math.hypot(float(ctm[2]), float(ctm[3]))
        if sx <= 0 or sy <= 0:
            return None
        return (float(width_px) / sx * 72.0, float(height_px) / sy * 72.0)
    except (TypeError, ValueError):
        return None


def has_icc_profile(image: Any) -> bool:
    """True iff the image has an embedded ICC profile (ColorSpace is ICCBased)."""
    cs = _get(image, "color_space", "ColorSpace", "CS")
    if isinstance(cs, (list, tuple)) and cs:
        return _normalize_str(cs[0]) == "ICCBased"
    if _normalize_str(cs) == "ICCBased":
        return True
    return bool(_get(image, "has_icc_profile", "icc_profile", default=False))


def icc_matches_oi(image: Any, output_intent_icc: Any) -> bool:
    """True iff the image's ICC profile matches the document Output Intent.

    Compares ICC profile names / hashes when both are present. Returns False
    when either side is missing or names don't match.
    """
    if not has_icc_profile(image) or output_intent_icc is None:
        return False
    image_icc = _get(image, "icc_name", "icc_profile_name")
    if image_icc is None:
        cs = _get(image, "color_space", "ColorSpace", "CS")
        if isinstance(cs, (list, tuple)) and len(cs) >= 2:
            stream = cs[1]
            if hasattr(stream, "get"):
                image_icc = stream.get("Name") or stream.get("/Name")
    oi_name = (
        _get(output_intent_icc, "Name", "icc_name", "name")
        if hasattr(output_intent_icc, "get") or hasattr(output_intent_icc, "name")
        else output_intent_icc
    )
    if image_icc is None or oi_name is None:
        return False
    return _normalize_str(image_icc) == _normalize_str(oi_name)


def has_alpha(image: Any) -> bool:
    """True iff the image has an explicit alpha channel (per ColorSpace components)."""
    return bool(_get(image, "has_alpha", "alpha", default=False))


def has_smask(image: Any) -> bool:
    """True iff the image dictionary has an SMask entry."""
    smask = _get(image, "smask", "SMask")
    if smask is None:
        return False
    return _normalize_str(smask) != "None"


def is_inline(image: Any) -> bool:
    """True iff this image was emitted as an inline image (BI...ID...EI)."""
    return bool(_get(image, "is_inline", "inline", default=False))


def is_linked_opi(image: Any) -> bool:
    """True iff the image references an Open Press Interface (OPI) link."""
    opi = _get(image, "OPI", "opi")
    return opi is not None


# ---- registry -----------------------------------------------------------

for _name in (
    "color_space",
    "bit_depth",
    "filter_name",
    "has_jpeg",
    "has_jpeg2000",
    "has_jbig2",
    "dpi_native",
    "dpi_effective",
    "has_icc_profile",
    "icc_matches_oi",
    "has_alpha",
    "has_smask",
    "is_inline",
    "is_linked_opi",
):
    register("image", _name, globals()[_name])

del _name


__all__ = [
    "bit_depth",
    "color_space",
    "dpi_effective",
    "dpi_native",
    "filter_name",
    "has_alpha",
    "has_icc_profile",
    "has_jbig2",
    "has_jpeg",
    "has_jpeg2000",
    "has_smask",
    "icc_matches_oi",
    "is_inline",
    "is_linked_opi",
]
