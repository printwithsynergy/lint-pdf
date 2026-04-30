"""Geometry / page-box / path / transform predicates — Tier-0 Batch 04.

Per universe enumeration §4.4. 23 predicates covering five sub-areas:
box accessors, box predicates, object bbox + containment, path predicates,
and transform / CTM helpers.

All predicates are pure functions that operate on:
    - ``page``: a :class:`siftpdf.parser.PdfPage` (or any object exposing
      ``media_box`` / ``crop_box`` / etc. attributes)
    - ``box``: a ``(x0, y0, x1, y1)`` 4-tuple of floats
    - ``obj``: dict / dataclass / Mapping exposing ``bbox`` / ``ctm`` keys
    - ``path``: list of ``(operator, operands)`` tuples constituting a path
      construction sequence terminated by a paint operator
    - ``state``: graphics-state dict with ``dash_array`` / ``dash_phase`` /
      ``miter_limit`` / ``line_cap`` keys

No mutation, no side effects. Returns ``None`` for missing data; ``False``
for "not applicable" predicates.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from siftpdf.primitives import register

Box = tuple[float, float, float, float]
Ctm = tuple[float, float, float, float, float, float]

# ---- box accessors -------------------------------------------------------

# Box-construction operators per PDF Reference Table 60. The path
# construction operators that contribute nodes; ``h`` closes the subpath.
_PATH_NODE_OPS = frozenset({"m", "l", "c", "v", "y", "re", "h"})

# Path-paint operators that close the subpath as part of the paint
_PATH_CLOSE_PAINT_OPS = frozenset({"s", "b", "b*"})


def _box_from(value: Any) -> Box | None:
    """Coerce a box value to a 4-tuple.

    Accepts:
        - 4-tuple/list ``(x0, y0, x1, y1)``
        - Dataclass / object with ``x0`` / ``y0`` / ``x1`` / ``y1`` attributes
          (e.g. :class:`siftpdf.semantic.model.PdfBox`)
        - ``None`` → returns ``None``
    """
    if value is None:
        return None
    if (
        hasattr(value, "x0")
        and hasattr(value, "y0")
        and hasattr(value, "x1")
        and hasattr(value, "y1")
    ):
        try:
            return (float(value.x0), float(value.y0), float(value.x1), float(value.y1))
        except (TypeError, ValueError):
            return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 4:
        try:
            return (float(value[0]), float(value[1]), float(value[2]), float(value[3]))
        except (TypeError, ValueError):
            return None
    return None


def media_box(page: Any) -> Box | None:
    """Return MediaBox as ``(x0,y0,x1,y1)`` or None if not defined."""
    return _box_from(getattr(page, "media_box", None))


def crop_box(page: Any) -> Box | None:
    """Return CropBox; falls back to MediaBox per PDF spec when absent."""
    box = _box_from(getattr(page, "crop_box", None))
    return box if box is not None else media_box(page)


def trim_box(page: Any) -> Box | None:
    """Return TrimBox or None."""
    return _box_from(getattr(page, "trim_box", None))


def bleed_box(page: Any) -> Box | None:
    """Return BleedBox or None."""
    return _box_from(getattr(page, "bleed_box", None))


def art_box(page: Any) -> Box | None:
    """Return ArtBox or None."""
    return _box_from(getattr(page, "art_box", None))


# ---- box predicates ------------------------------------------------------


def box_contains(outer: Box, inner: Box, *, eps: float = 0.0) -> bool:
    """True iff ``inner`` is contained within ``outer`` with tolerance ``eps``.

    Tolerance applies inward: the check is `outer[0] - eps <= inner[0]`,
    so a small float drift between equal boxes is forgiven.
    """
    if outer is None or inner is None:
        return False
    return (
        outer[0] - eps <= inner[0]
        and outer[1] - eps <= inner[1]
        and outer[2] + eps >= inner[2]
        and outer[3] + eps >= inner[3]
    )


def box_equals(a: Box, b: Box, *, eps: float = 0.0) -> bool:
    """True iff two boxes are equal within ``eps`` tolerance."""
    if a is None or b is None:
        return False
    return all(abs(a[i] - b[i]) <= eps for i in range(4))


# ---- object bbox / containment -------------------------------------------


def obj_bbox(obj: Any) -> Box | None:
    """Discover an object's bbox from common attribute / key names.

    Looks for: ``bbox``, ``rect``, ``BBox``, ``Rect`` (in that order).
    Returns None if no bbox-like value is found.
    """
    for key in ("bbox", "rect", "BBox", "Rect"):
        if isinstance(obj, Mapping) and key in obj:
            return _box_from(obj[key])
        attr = getattr(obj, key, None)
        if attr is not None:
            return _box_from(attr)
    return None


def obj_intersects(obj: Any, box: Box) -> bool:
    """True iff the object's bbox intersects ``box``.

    Standard AABB overlap test. Edge-touching counts as intersection.
    """
    bb = obj_bbox(obj)
    if bb is None or box is None:
        return False
    return not (bb[2] < box[0] or bb[0] > box[2] or bb[3] < box[1] or bb[1] > box[3])


def obj_outside(obj: Any, box: Box) -> bool:
    """True iff the object's bbox is entirely outside ``box``."""
    bb = obj_bbox(obj)
    if bb is None or box is None:
        return False
    return bb[2] < box[0] or bb[0] > box[2] or bb[3] < box[1] or bb[1] > box[3]


def obj_within(obj: Any, box: Box, *, margin: float = 0.0) -> bool:
    """True iff the object's bbox is fully inside ``box`` minus ``margin``.

    Margin shrinks the containing box inward; useful for "is this content
    in the safe area (trim - 3mm)?" queries.
    """
    bb = obj_bbox(obj)
    if bb is None or box is None:
        return False
    return box_contains(
        (box[0] + margin, box[1] + margin, box[2] - margin, box[3] - margin),
        bb,
        eps=0.0,
    )


# ---- path predicates -----------------------------------------------------


def path_is_closed(path: Sequence[tuple[str, Sequence[Any]]]) -> bool:
    """True iff the path's last operator closes the subpath.

    Closure indicators: ``h`` operator at end, or paint operator that
    closes (``s``, ``b``, ``b*``).
    """
    if not path:
        return False
    last_op = _path_last_op(path)
    if last_op == "h":
        return True
    return last_op in _PATH_CLOSE_PAINT_OPS


def path_self_intersects(path: Sequence[tuple[str, Sequence[Any]]]) -> bool:
    """True iff any two non-vertex-sharing path segments cross.

    Skips Bézier curves (returns False conservatively for paths containing
    only curves). Compares all segment pairs; segments sharing an endpoint
    are considered adjacent and skipped (would not cross under normal path
    traversal).
    """
    segments = _path_to_line_segments(path)
    if len(segments) < 2:
        return False
    for i in range(len(segments)):
        for j in range(i + 1, len(segments)):
            s1, s2 = segments[i], segments[j]
            if _segments_share_endpoint(s1, s2):
                continue
            if _segments_cross(s1, s2):
                return True
    return False


def _segments_share_endpoint(
    s1: tuple[float, float, float, float],
    s2: tuple[float, float, float, float],
) -> bool:
    """True iff the two segments share at least one endpoint."""
    p1a, p1b = (s1[0], s1[1]), (s1[2], s1[3])
    p2a, p2b = (s2[0], s2[1]), (s2[2], s2[3])
    return p1a in {p2a, p2b} or p1b in {p2a, p2b}


def path_node_count(path: Sequence[tuple[str, Sequence[Any]]]) -> int:
    """Count of path-construction operators in the sequence."""
    return sum(1 for op, _ in path if op in _PATH_NODE_OPS)


def path_is_dashed(state: Mapping[str, Any] | None) -> bool:
    """True iff the graphics state's dash array is non-empty."""
    if state is None:
        return False
    dash = state.get("dash_array")
    if dash is None:
        return False
    if isinstance(dash, Sequence) and not isinstance(dash, (str, bytes)):
        return len(dash) > 0
    return False


def path_dash_phase(state: Mapping[str, Any] | None) -> float:
    """Return the dash phase (offset into the dash pattern) or 0.0."""
    if state is None:
        return 0.0
    return float(state.get("dash_phase", 0.0))


def path_miter_limit(state: Mapping[str, Any] | None) -> float:
    """Return the miter limit (default 10.0 per PDF spec)."""
    if state is None:
        return 10.0
    return float(state.get("miter_limit", 10.0))


def path_line_cap(state: Mapping[str, Any] | None) -> int:
    """Return the line cap style: 0 = butt, 1 = round, 2 = square."""
    if state is None:
        return 0
    return int(state.get("line_cap", 0))


# ---- transform / CTM predicates ------------------------------------------


def _ctm_from(obj: Any) -> Ctm | None:
    val = None
    if isinstance(obj, Mapping):
        val = obj.get("ctm") or obj.get("CTM")
    if val is None:
        val = getattr(obj, "ctm", None) or getattr(obj, "CTM", None)
    if val is None:
        return None
    if isinstance(val, Sequence) and not isinstance(val, (str, bytes)) and len(val) >= 6:
        try:
            return tuple(float(x) for x in val[:6])  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None
    return None


def obj_ctm(obj: Any) -> Ctm | None:
    """Return the object's CTM as a 6-tuple ``(a,b,c,d,e,f)`` or None."""
    return _ctm_from(obj)


def obj_rotation(obj: Any) -> float:
    """Return rotation in degrees [0, 360); 0 if no CTM or no rotation.

    Computed from CTM as ``atan2(b, a)`` then normalized to [0, 360).
    """
    ctm = _ctm_from(obj)
    if ctm is None:
        return 0.0
    a, b = ctm[0], ctm[1]
    deg = math.degrees(math.atan2(b, a))
    return deg % 360.0


def obj_scale_xy(obj: Any) -> tuple[float, float]:
    """Return ``(sx, sy)`` scale factors extracted from the CTM.

    Per PDF spec: sx = sqrt(a² + b²); sy = sqrt(c² + d²). Returns
    ``(1.0, 1.0)`` when no CTM is found (identity).
    """
    ctm = _ctm_from(obj)
    if ctm is None:
        return (1.0, 1.0)
    a, b, c, d, _, _ = ctm
    return (math.hypot(a, b), math.hypot(c, d))


def obj_is_mirrored(obj: Any) -> bool:
    """True iff the CTM has negative determinant (X or Y axis flipped)."""
    ctm = _ctm_from(obj)
    if ctm is None:
        return False
    a, b, c, d, _, _ = ctm
    return (a * d - b * c) < 0


def obj_is_skewed(obj: Any) -> bool:
    """True iff the CTM has off-diagonal terms that aren't pure rotation.

    An unrotated, non-skewed CTM has ``b == c == 0``. Pure rotation has
    ``b == -c``. Anything else implies non-orthogonal axes (skew).
    Tolerance 1e-9.
    """
    ctm = _ctm_from(obj)
    if ctm is None:
        return False
    _a, b, c, _d, _, _ = ctm
    if abs(b) < 1e-9 and abs(c) < 1e-9:
        return False
    # If b ≈ -c, it's pure rotation (already handled by obj_rotation).
    return abs(b + c) >= 1e-9


# ---- internals -----------------------------------------------------------


def _path_last_op(path: Sequence[tuple[str, Sequence[Any]]]) -> str | None:
    if not path:
        return None
    return path[-1][0]


def _path_to_line_segments(
    path: Sequence[tuple[str, Sequence[Any]]],
) -> list[tuple[float, float, float, float]]:
    """Reduce a path to line segments. Skips Bézier curves (returns line
    approximations would be lossy; conservatively False for self-intersect).
    """
    segments: list[tuple[float, float, float, float]] = []
    cx = cy = 0.0
    sub_start_x = sub_start_y = 0.0
    for op, operands in path:
        try:
            if op == "m" and len(operands) >= 2:
                cx, cy = float(operands[0]), float(operands[1])
                sub_start_x, sub_start_y = cx, cy
            elif op == "l" and len(operands) >= 2:
                nx, ny = float(operands[0]), float(operands[1])
                segments.append((cx, cy, nx, ny))
                cx, cy = nx, ny
            elif op == "re" and len(operands) >= 4:
                x, y, w, h = (float(operands[i]) for i in range(4))
                segments.append((x, y, x + w, y))
                segments.append((x + w, y, x + w, y + h))
                segments.append((x + w, y + h, x, y + h))
                segments.append((x, y + h, x, y))
                cx, cy = x, y
                sub_start_x, sub_start_y = x, y
            elif op == "h":
                segments.append((cx, cy, sub_start_x, sub_start_y))
                cx, cy = sub_start_x, sub_start_y
            # Skip c/v/y curves: they don't lower to lines
        except (TypeError, ValueError):
            continue
    return segments


def _segments_cross(
    s1: tuple[float, float, float, float],
    s2: tuple[float, float, float, float],
) -> bool:
    """Standard CCW-based segment intersection test."""

    def ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    a, b, c, d = (s1[0], s1[1]), (s1[2], s1[3]), (s2[0], s2[1]), (s2[2], s2[3])
    d1 = ccw(*c, *d, *a)
    d2 = ccw(*c, *d, *b)
    d3 = ccw(*a, *b, *c)
    d4 = ccw(*a, *b, *d)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


# ---- registry ------------------------------------------------------------

for _name in (
    "media_box",
    "crop_box",
    "trim_box",
    "bleed_box",
    "art_box",
    "box_contains",
    "box_equals",
    "obj_bbox",
    "obj_intersects",
    "obj_outside",
    "obj_within",
    "path_is_closed",
    "path_self_intersects",
    "path_node_count",
    "path_is_dashed",
    "path_dash_phase",
    "path_miter_limit",
    "path_line_cap",
    "obj_ctm",
    "obj_rotation",
    "obj_scale_xy",
    "obj_is_mirrored",
    "obj_is_skewed",
):
    register("geometry", _name, globals()[_name])

del _name


__all__ = [
    "Box",
    "Ctm",
    "art_box",
    "bleed_box",
    "box_contains",
    "box_equals",
    "crop_box",
    "media_box",
    "obj_bbox",
    "obj_ctm",
    "obj_intersects",
    "obj_is_mirrored",
    "obj_is_skewed",
    "obj_outside",
    "obj_rotation",
    "obj_scale_xy",
    "obj_within",
    "path_dash_phase",
    "path_is_closed",
    "path_is_dashed",
    "path_line_cap",
    "path_miter_limit",
    "path_node_count",
    "path_self_intersects",
    "trim_box",
]
