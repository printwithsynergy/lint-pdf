"""Transparency-stack predicates — Tier-0 Batch 06.

Per universe enumeration §4.6. Predicates over the active transparency
context: isolated/knockout groups, soft masks, page-level transparency
group, blending color space, and ExtGState alpha / blend mode.

Distinction from :mod:`lintpdf.primitives.stroke_fill`:
    - ``stroke_fill`` operates on the **resolved active graphics state**
      (post-CTM, post-gs operator)
    - ``transparency_stack`` operates on **raw ExtGState / SMask /
      transparency-group dicts** as referenced by content streams,
      page Group attribute, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lintpdf.primitives import register

if TYPE_CHECKING:
    from collections.abc import Mapping


def _str_normalize(value: Any) -> str | None:
    """Strip leading slash from a name token; coerce bytes/Name to str."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.lstrip("/")
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="replace").lstrip("/")
    return str(value).lstrip("/")


def _get_either(d: Any, *keys: str) -> Any:
    """Return the first non-None value among d[k] / d['/'+k] for each k."""
    if not isinstance(d, dict) and not hasattr(d, "get"):
        return None
    for k in keys:
        v = d.get(k) if hasattr(d, "get") else None
        if v is not None:
            return v
        v = d.get("/" + k) if hasattr(d, "get") else None
        if v is not None:
            return v
    return None


def in_isolated_group(state: Mapping[str, Any] | None) -> bool:
    """True iff the active transparency group has Isolated = True."""
    if state is None:
        return False
    group = state.get("transparency_group") or state.get("group")
    if group is None:
        return bool(state.get("isolated"))
    return bool(_get_either(group, "I", "Isolated", "isolated"))


def in_knockout_group(state: Mapping[str, Any] | None) -> bool:
    """True iff the active transparency group has Knockout = True."""
    if state is None:
        return False
    group = state.get("transparency_group") or state.get("group")
    if group is None:
        return bool(state.get("knockout"))
    return bool(_get_either(group, "K", "Knockout", "knockout"))


def has_smask(state: Mapping[str, Any] | None) -> bool:
    """True iff the active graphics state / ExtGState references a soft mask.

    Accepts either a graphics state with ``smask`` key or an ExtGState dict
    with ``SMask`` key. ``SMask = /None`` is treated as no soft mask.
    """
    if state is None:
        return False
    smask = state.get("smask") or state.get("SMask") or state.get("/SMask")
    if smask is None:
        return False
    return _str_normalize(smask) != "None"


def smask_is_alpha(smask_dict: Any) -> bool:
    """True iff the SMask dictionary has Subtype = Alpha."""
    if not isinstance(smask_dict, dict):
        return False
    subtype = _get_either(smask_dict, "S", "Subtype")
    return _str_normalize(subtype) == "Alpha"


def smask_is_luminosity(smask_dict: Any) -> bool:
    """True iff the SMask dictionary has Subtype = Luminosity."""
    if not isinstance(smask_dict, dict):
        return False
    subtype = _get_either(smask_dict, "S", "Subtype")
    return _str_normalize(subtype) == "Luminosity"


def page_transparency_group_present(page: Any) -> bool:
    """True iff the page has a /Group entry with /S /Transparency."""
    page_dict = getattr(page, "page_dict", None) or page
    group = _get_either(page_dict, "Group") if isinstance(page_dict, dict) else None
    if group is None:
        # Try attribute access
        group = getattr(page, "group", None) or getattr(page, "Group", None)
    if group is None:
        return False
    if not isinstance(group, dict):
        return True  # Group present but not introspectable; assume yes
    s = _get_either(group, "S", "Subtype")
    return _str_normalize(s) == "Transparency"


def page_blending_color_space(page: Any) -> str | None:
    """Return the page's transparency-group blending color space (CS) or None."""
    page_dict = getattr(page, "page_dict", None) or page
    group = _get_either(page_dict, "Group") if isinstance(page_dict, dict) else None
    if group is None:
        group = getattr(page, "group", None) or getattr(page, "Group", None)
    if group is None or not isinstance(group, dict):
        return None
    cs = _get_either(group, "CS", "ColorSpace")
    if cs is None:
        return None
    if isinstance(cs, list):
        return _str_normalize(cs[0]) if cs else None
    return _str_normalize(cs)


def extgstate_alpha(extgstate: Any, *, kind: str = "fill") -> float:
    """Return the ExtGState alpha for fill (``ca``) or stroke (``CA``).

    Returns 1.0 (fully opaque) when the ExtGState is missing or doesn't
    set the relevant key.
    """
    if not isinstance(extgstate, dict):
        return 1.0
    v = _get_either(extgstate, "CA") if kind == "stroke" else _get_either(extgstate, "ca")
    if v is None:
        return 1.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 1.0


def extgstate_blend_mode(extgstate: Any) -> str:
    """Return the ExtGState blend mode (``BM``); default ``"Normal"``."""
    if not isinstance(extgstate, dict):
        return "Normal"
    bm = _get_either(extgstate, "BM")
    if bm is None:
        return "Normal"
    if isinstance(bm, list):
        # Array of names — first matching takes effect; return first
        return _str_normalize(bm[0]) or "Normal" if bm else "Normal"
    name = _str_normalize(bm)
    return name or "Normal"


# ---- registry ------------------------------------------------------------

for _name in (
    "in_isolated_group",
    "in_knockout_group",
    "has_smask",
    "smask_is_alpha",
    "smask_is_luminosity",
    "page_transparency_group_present",
    "page_blending_color_space",
    "extgstate_alpha",
    "extgstate_blend_mode",
):
    register("transparency_stack", _name, globals()[_name])

del _name


__all__ = [
    "extgstate_alpha",
    "extgstate_blend_mode",
    "has_smask",
    "in_isolated_group",
    "in_knockout_group",
    "page_blending_color_space",
    "page_transparency_group_present",
    "smask_is_alpha",
    "smask_is_luminosity",
]
