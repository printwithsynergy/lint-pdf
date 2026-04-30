"""Text predicates — Tier-0 Batch 07.

Per universe enumeration §4.7. Predicates over a text-rendering event or
text-state Mapping. The engine's parser emits ``TextRenderedEvent`` objects
with attributes like ``font_name``, ``font_size``, ``rendering_mode``,
``text_matrix`` etc.; primitives here accept either an event-shaped object
(attribute access) or a plain Mapping (key access).

All predicates are pure functions with sensible PDF-spec defaults.
"""

from __future__ import annotations

import math
import re
from typing import Any

from siftpdf.primitives import register

# Subset font names use the convention "XXXXXX+OriginalName" where
# XXXXXX is exactly six uppercase letters. Per ISO 32000-2 §9.6.4.
_SUBSET_RE = re.compile(r"^[A-Z]{6}\+")


def _get(text: Any, attr: str, default: Any = None) -> Any:
    """Fetch ``attr`` from event-style object OR Mapping."""
    if text is None:
        return default
    if hasattr(text, attr):
        return getattr(text, attr)
    if hasattr(text, "get"):
        return text.get(attr, default)
    return default


def font_name(text: Any) -> str | None:
    """Return the font's BaseFont name (with optional subset prefix), or None."""
    name = _get(text, "font_name") or _get(text, "BaseFont") or _get(text, "name")
    return str(name) if name else None


def font_subtype(text: Any) -> str | None:
    """Return font subtype: Type1, TrueType, CIDFontType0, CIDFontType2, MMType1, Type3."""
    sub = _get(text, "font_subtype") or _get(text, "Subtype")
    return str(sub) if sub else None


def font_is_embedded(text: Any) -> bool:
    """True iff the font is embedded (FontFile / FontFile2 / FontFile3 stream present)."""
    return bool(_get(text, "font_is_embedded", False) or _get(text, "embedded", False))


def font_is_subset(text: Any) -> bool:
    """True iff the BaseFont name has the 6-letter subset prefix."""
    name = font_name(text)
    if not name:
        return False
    return bool(_SUBSET_RE.match(name))


def font_has_to_unicode(text: Any) -> bool:
    """True iff the font has a /ToUnicode CMap."""
    return bool(_get(text, "has_to_unicode", False) or _get(text, "to_unicode", False))


def font_to_unicode_complete(text: Any) -> bool:
    """True iff every used glyph in this font maps to a Unicode codepoint via ToUnicode."""
    return bool(_get(text, "to_unicode_complete", False))


def font_widths_consistent(text: Any) -> bool:
    """True iff font widths array matches the font program metrics (no gaps).

    Defaults True for fonts whose adapter cannot determine consistency.
    """
    consistent = _get(text, "font_widths_consistent", True)
    return bool(consistent) if consistent is not None else True


def glyph_uses_notdef(text: Any) -> bool:
    """True iff this text-rendering event uses the .notdef glyph (visible missing glyph)."""
    return bool(_get(text, "glyph_uses_notdef", False) or _get(text, "uses_notdef", False))


def is_artificial_bold(text: Any) -> bool:
    """True iff weight is synthesized via ``Tr 2`` (fill+stroke) with non-trivial stroke width.

    Detection heuristic: rendering_mode == 2 AND line_width > 0.
    """
    if rendering_mode(text) != 2:
        return False
    return float(_get(text, "line_width", 0.0) or 0.0) > 0.0


def is_artificial_italic(text: Any) -> bool:
    """True iff the text matrix has horizontal shear (synthesized italic).

    Detection: text-matrix ``c`` component (off-diagonal) significantly nonzero
    while font itself is not declared as italic.
    """
    tm = _get(text, "text_matrix")
    if tm is None or not hasattr(tm, "__getitem__") or len(tm) < 6:
        return False
    try:
        c = float(tm[2])
    except (TypeError, ValueError):
        return False
    return abs(c) > 0.05  # >5% shear is artificial italic


def is_artificial_outline(text: Any) -> bool:
    """True iff text rendering mode is 1 (stroke only) — outline-only style."""
    return rendering_mode(text) == 1


def rendering_mode(text: Any) -> int:
    """Return PDF text rendering mode (0..7); default 0 (fill).

    Per ISO 32000-2 §9.3.6: 0=fill, 1=stroke, 2=fill+stroke, 3=invisible,
    4=fill+clip, 5=stroke+clip, 6=fill+stroke+clip, 7=clip.
    """
    mode = _get(text, "rendering_mode")
    if mode is None:
        mode = _get(text, "Tr")
    if mode is None:
        return 0
    try:
        return int(mode)
    except (TypeError, ValueError):
        return 0


def size_pt(text: Any) -> float:
    """Return the font size as set by the most recent ``Tf`` operator.

    This is the user-space size BEFORE text-matrix or CTM scaling.
    """
    size = _get(text, "font_size")
    if size is None:
        size = _get(text, "Tf_size")
    if size is None:
        return 0.0
    try:
        return float(size)
    except (TypeError, ValueError):
        return 0.0


def effective_size_pt(
    text: Any,
    ctm: tuple[float, float, float, float, float, float] | None = None,
) -> float:
    """Return the rendered text size in user-space points.

    Computed as ``font_size x text_matrix_scale x ctm_scale`` where each
    scale uses the geometric mean of the X / Y scale factors. This is what
    "is this text below 6pt?" checks should use.

    If text_matrix is absent, falls back to ``size_pt x ctm_scale``.
    If both are absent, returns ``size_pt``.
    """
    s = size_pt(text)
    if s == 0.0:
        return 0.0

    # Text-matrix scale
    tm = _get(text, "text_matrix")
    tm_scale = 1.0
    if tm is not None and hasattr(tm, "__getitem__") and len(tm) >= 4:
        try:
            a, b, c, d = float(tm[0]), float(tm[1]), float(tm[2]), float(tm[3])
            sx = math.hypot(a, b)
            sy = math.hypot(c, d)
            tm_scale = math.sqrt(sx * sy) if sx > 0 and sy > 0 else max(sx, sy, 1.0)
        except (TypeError, ValueError):
            pass

    # CTM scale (use min for hairline-style detection)
    ctm_scale = 1.0
    if ctm is not None and len(ctm) >= 4:
        a, b, c, d = ctm[0], ctm[1], ctm[2], ctm[3]
        sx = math.hypot(a, b)
        sy = math.hypot(c, d)
        ctm_scale = math.sqrt(sx * sy) if sx > 0 and sy > 0 else max(sx, sy, 1.0)

    return s * tm_scale * ctm_scale


# ---- registry ------------------------------------------------------------

for _name in (
    "font_name",
    "font_subtype",
    "font_is_embedded",
    "font_is_subset",
    "font_has_to_unicode",
    "font_to_unicode_complete",
    "font_widths_consistent",
    "glyph_uses_notdef",
    "is_artificial_bold",
    "is_artificial_italic",
    "is_artificial_outline",
    "rendering_mode",
    "size_pt",
    "effective_size_pt",
):
    register("text", _name, globals()[_name])

del _name


__all__ = [
    "effective_size_pt",
    "font_has_to_unicode",
    "font_is_embedded",
    "font_is_subset",
    "font_name",
    "font_subtype",
    "font_to_unicode_complete",
    "font_widths_consistent",
    "glyph_uses_notdef",
    "is_artificial_bold",
    "is_artificial_italic",
    "is_artificial_outline",
    "rendering_mode",
    "size_pt",
]
