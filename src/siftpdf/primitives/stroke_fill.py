"""Stroke / fill predicates — Tier-0 Batch 05.

Per universe enumeration §4.5. 8 predicates covering paint operators
(``has_fill`` / ``has_stroke``), graphics-state inspection (color, width,
opacity, blend mode), and CTM-aware effective-width math.

All predicates are pure functions. Returns sensible defaults when the
graphics state is missing keys (per PDF spec defaults: width 1.0,
opacity 1.0, blend mode "Normal", line cap 0, miter limit 10.0).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from siftpdf.primitives import register

if TYPE_CHECKING:
    from collections.abc import Mapping

# Paint operators that fill the path: f, F (legacy alias), f*, B, B*, b, b*
_FILL_OPS = frozenset({"f", "F", "f*", "B", "B*", "b", "b*"})

# Paint operators that stroke the path: S, s, B, B*, b, b*
_STROKE_OPS = frozenset({"S", "s", "B", "B*", "b", "b*"})


def has_fill(operator: str) -> bool:
    """True iff the paint operator fills the current path."""
    return operator in _FILL_OPS


def has_stroke(operator: str) -> bool:
    """True iff the paint operator strokes the current path.

    Note: ``n`` (no-op) returns False — it neither fills nor strokes.
    """
    return operator in _STROKE_OPS


def fill_color(state: Mapping[str, Any] | None) -> Any:
    """Return the active fill color from graphics state.

    The shape depends on the active color space:
        - DeviceGray: float
        - DeviceRGB: tuple[float, float, float]
        - DeviceCMYK: tuple[float, float, float, float]
        - Pattern: name string

    Returns None if no fill color is set.
    """
    if state is None:
        return None
    return state.get("fill_color")


def stroke_color(state: Mapping[str, Any] | None) -> Any:
    """Return the active stroke color from graphics state. See :func:`fill_color`."""
    if state is None:
        return None
    return state.get("stroke_color")


def width(state: Mapping[str, Any] | None) -> float:
    """Return the current line width in user-space units.

    Default 1.0 per PDF spec when graphics state is missing or doesn't
    set ``line_width``.
    """
    if state is None:
        return 1.0
    return float(state.get("line_width", 1.0))


def effective_width(
    state: Mapping[str, Any] | None,
    ctm: tuple[float, float, float, float, float, float] | None,
) -> float:
    """Return the rendered line width after CTM transformation.

    Hairline detection uses this: a 0.5pt line under a 0.5x scale is
    rendered at 0.25pt, which crosses many press hairline thresholds.

    The effective width is ``line_width xmin(scale_x, scale_y)`` because
    a stroke is drawn perpendicular to the path; the narrower of the two
    axis scales is what matters for "is this hairline?". Returns the raw
    line width if no CTM is provided.
    """
    line_w = width(state)
    if ctm is None:
        return line_w
    a, b, c, d, _, _ = ctm
    sx = math.hypot(a, b)
    sy = math.hypot(c, d)
    return line_w * min(sx, sy)


def opacity(state: Mapping[str, Any] | None, *, kind: str = "fill") -> float:
    """Return the current opacity for the given paint kind.

    PDF separates fill opacity (``ca``) from stroke opacity (``CA``).
    ``kind`` is ``"fill"`` (default) or ``"stroke"``. Returns 1.0 when
    state is missing or the relevant key is unset.
    """
    if state is None:
        return 1.0
    if kind == "stroke":
        # ExtGState CA = stroke opacity
        for k in ("CA", "stroke_opacity", "stroke_alpha"):
            if k in state:
                return float(state[k])
        return 1.0
    # Default: fill
    for k in ("ca", "fill_opacity", "fill_alpha"):
        if k in state:
            return float(state[k])
    return 1.0


def blend_mode(state: Mapping[str, Any] | None) -> str:
    """Return the current blend mode (``BM`` in ExtGState).

    Default ``"Normal"`` per PDF spec when graphics state is missing or
    doesn't declare a blend mode.
    """
    if state is None:
        return "Normal"
    bm = state.get("BM") or state.get("blend_mode")
    if bm is None:
        return "Normal"
    if isinstance(bm, str):
        return bm.lstrip("/")
    if isinstance(bm, bytes):
        return bm.decode("latin-1", errors="replace").lstrip("/")
    return str(bm)


# ---- registry ------------------------------------------------------------

for _name in (
    "has_fill",
    "has_stroke",
    "fill_color",
    "stroke_color",
    "width",
    "effective_width",
    "opacity",
    "blend_mode",
):
    register("stroke_fill", _name, globals()[_name])

del _name


__all__ = [
    "blend_mode",
    "effective_width",
    "fill_color",
    "has_fill",
    "has_stroke",
    "opacity",
    "stroke_color",
    "width",
]
