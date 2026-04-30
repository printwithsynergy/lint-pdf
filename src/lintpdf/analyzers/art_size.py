"""Art-size inspector — trim dimensions from the dieline (WS-D).

Strict: when the dieline is ``source="missing"`` we return ``None``
*and* rely on the caller to emit a ``LPDF_DIE_MISSING`` warning.
No guessing from the TrimBox, MediaBox, or BleedBox — those lie
about the real trim edge on packaging files that pad the sheet
for bleed and gripper margin.

The size is computed from the **center line** of the dieline
stroke — i.e. the bbox of the polygon inset by half the stroke
width. On a file with ``polylines=[]`` (name-match path that
didn't emit geometry) we fall back to the page's CropBox intersected
with the spot separation mask if available — otherwise ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ArtSizeMM:
    """Trim dimensions in millimetres."""

    width_mm: float
    height_mm: float


_POINT_TO_MM = 25.4 / 72.0


def _bbox_of_polygons(
    polylines: list[list[list[float]]],
) -> tuple[float, float, float, float] | None:
    if not polylines:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for poly in polylines:
        for pt in poly:
            if len(pt) >= 2:
                xs.append(float(pt[0]))
                ys.append(float(pt[1]))
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def compute_art_size(dieline: Any, *, stroke_pts: float = 1.0) -> ArtSizeMM | None:
    """Compute trim size from a ``DielineResult``.

    Returns ``None`` when the dieline is missing or has no
    polylines to measure. Caller must emit ``LPDF_DIE_MISSING``
    on ``None``.
    """
    if dieline is None or getattr(dieline, "source", "missing") == "missing":
        return None
    polys = list(getattr(dieline, "polylines", []) or [])
    bbox = _bbox_of_polygons(polys)
    if bbox is None:
        return None

    x0, y0, x1, y1 = bbox
    # Inset by half the stroke so we measure the centerline, not
    # the outer edge. Customers who hand-stroke their dielines at
    # 0.5pt or 1pt are the common case.
    inset = stroke_pts / 2.0
    width_pts = max(0.0, (x1 - x0) - inset * 2.0)
    height_pts = max(0.0, (y1 - y0) - inset * 2.0)
    return ArtSizeMM(
        width_mm=round(width_pts * _POINT_TO_MM, 3),
        height_mm=round(height_pts * _POINT_TO_MM, 3),
    )


def result_to_json(size: ArtSizeMM | None) -> dict[str, float] | None:
    if size is None:
        return None
    return {"width_mm": size.width_mm, "height_mm": size.height_mm}
