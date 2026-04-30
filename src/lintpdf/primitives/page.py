"""Page and document structure predicates — Tier-0 Batch 09.

Per universe enumeration §4.9. Predicates over a Page dictionary or a
Document object (tries attribute access then Mapping shape).

Page geometry boxes (ISO 32000-2 §14.11.2):
  MediaBox  → physical page size (required)
  CropBox   → visible region (defaults to MediaBox)
  BleedBox  → bleed extent (defaults to CropBox)
  TrimBox   → final trimmed page (defaults to CropBox)
  ArtBox    → meaningful content extent (defaults to CropBox)
"""

from __future__ import annotations

from typing import Any

from lintpdf.primitives import register

Rect = tuple[float, float, float, float]


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
            v = obj.get("/" + k)
            if v is not None:
                return v
    return default


def _coerce_rect(value: Any) -> Rect | None:
    """Coerce a 4-element sequence to a rect tuple of floats."""
    if value is None:
        return None
    if not hasattr(value, "__iter__"):
        return None
    try:
        items = list(value)
    except TypeError:
        return None
    if len(items) != 4:
        return None
    try:
        return (float(items[0]), float(items[1]), float(items[2]), float(items[3]))
    except (TypeError, ValueError):
        return None


# ---- page geometry boxes ------------------------------------------------


def media_box(page: Any) -> Rect | None:
    """Return the page's MediaBox as (llx, lly, urx, ury) or None."""
    return _coerce_rect(_get(page, "media_box", "MediaBox"))


def crop_box(page: Any) -> Rect | None:
    """Return CropBox if explicitly defined, else MediaBox, else None."""
    cb = _coerce_rect(_get(page, "crop_box", "CropBox"))
    return cb if cb is not None else media_box(page)


def bleed_box(page: Any) -> Rect | None:
    """Return BleedBox if explicitly defined, else CropBox."""
    bb = _coerce_rect(_get(page, "bleed_box", "BleedBox"))
    return bb if bb is not None else crop_box(page)


def trim_box(page: Any) -> Rect | None:
    """Return TrimBox if explicitly defined, else CropBox."""
    tb = _coerce_rect(_get(page, "trim_box", "TrimBox"))
    return tb if tb is not None else crop_box(page)


def art_box(page: Any) -> Rect | None:
    """Return ArtBox if explicitly defined, else CropBox."""
    ab = _coerce_rect(_get(page, "art_box", "ArtBox"))
    return ab if ab is not None else crop_box(page)


# ---- size / orientation / rotation / user-unit -------------------------


def user_unit(page: Any) -> float:
    """Return UserUnit multiplier for the page (default 1.0)."""
    uu = _get(page, "user_unit", "UserUnit")
    if uu is None:
        return 1.0
    try:
        return float(uu)
    except (TypeError, ValueError):
        return 1.0


def size_pt(page: Any) -> tuple[float, float] | None:
    """Return (width_pt, height_pt) from MediaBox * UserUnit, or None."""
    box = media_box(page)
    if box is None:
        return None
    uu = user_unit(page)
    width = (box[2] - box[0]) * uu
    height = (box[3] - box[1]) * uu
    return (width, height)


def rotation(page: Any) -> int:
    """Return /Rotate normalized to [0, 360); default 0."""
    rot = _get(page, "rotation", "Rotate")
    if rot is None:
        return 0
    try:
        normalized = int(rot) % 360
    except (TypeError, ValueError):
        return 0
    return normalized


def orientation(page: Any) -> str | None:
    """Return "portrait" / "landscape" / "square" honoring /Rotate.

    A page rotated 90° / 270° swaps width and height.
    """
    size = size_pt(page)
    if size is None:
        return None
    width, height = size
    if rotation(page) in (90, 270):
        width, height = height, width
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def has_oversize_bleed(page: Any, max_pt: float = 36.0) -> bool:
    """True iff the BleedBox extends more than ``max_pt`` past the TrimBox edge.

    Threshold default 36pt = 0.5 inch (typical print spec is 3mm ≈ 8.5pt).
    Returns False if either box is missing.
    """
    trim = trim_box(page)
    bleed = bleed_box(page)
    if trim is None or bleed is None:
        return False
    # Bleed should expand outward; difference per side
    left = trim[0] - bleed[0]
    bottom = trim[1] - bleed[1]
    right = bleed[2] - trim[2]
    top = bleed[3] - trim[3]
    return any(side > max_pt for side in (left, bottom, right, top))


# ---- document-level ----------------------------------------------------


def page_count(doc: Any) -> int:
    """Return the number of pages in the document."""
    n = _get(doc, "page_count", "PageCount", "num_pages")
    if n is not None:
        try:
            return int(n)
        except (TypeError, ValueError):
            pass
    pages = _get(doc, "pages", "Pages")
    if pages is None:
        return 0
    # Pages dict node: prefer /Count over len() (dict len is field count, not pages)
    count = _get(pages, "Count")
    if count is not None:
        try:
            return int(count)
        except (TypeError, ValueError):
            pass
    if isinstance(pages, (list, tuple)):
        return len(pages)
    if hasattr(pages, "__len__") and not hasattr(pages, "get"):
        try:
            return len(pages)
        except TypeError:
            return 0
    return 0


def has_structure_tree(doc: Any) -> bool:
    """True iff the document Catalog has a /StructTreeRoot (Tagged PDF)."""
    catalog = _get(doc, "catalog", "Catalog", "Root")
    target = catalog if catalog is not None else doc
    str_root = _get(target, "struct_tree_root", "StructTreeRoot")
    return str_root is not None


# ---- registry ----------------------------------------------------------

for _name in (
    "media_box",
    "crop_box",
    "bleed_box",
    "trim_box",
    "art_box",
    "size_pt",
    "orientation",
    "rotation",
    "user_unit",
    "has_oversize_bleed",
):
    register("page", _name, globals()[_name])

register("doc", "page_count", page_count)
register("doc", "has_structure_tree", has_structure_tree)

del _name


__all__ = [
    "art_box",
    "bleed_box",
    "crop_box",
    "has_oversize_bleed",
    "has_structure_tree",
    "media_box",
    "orientation",
    "page_count",
    "rotation",
    "size_pt",
    "trim_box",
    "user_unit",
]
