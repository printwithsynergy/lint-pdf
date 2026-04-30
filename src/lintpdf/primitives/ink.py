"""Ink predicates — Tier-0 Batch 03.

Per universe enumeration §4.3.

Wraps the existing spot-name taxonomy in
:mod:`lintpdf.analyzers.spot_name_normaliser` and adds library-matching
helpers (Pantone, HKS, RAL, TOYO/DIC/ANPA) plus Lab / alt-CMYK extraction.

Public API takes either a bare ink name (``"PANTONE 185 C"``) or a full
Separation/DeviceN array (``["Separation", "PANTONE 185 C", alt, tint]``).

Phase 2 Batch-3 operator decisions:
- Pantone + HKS + RAL + TOYO/DIC/ANPA libraries supported out of box
- Black-as-Separation classified as process (not spot)
- ``processing_step_group`` returns Title-Case strings to match ISO 19593-1
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from lintpdf.analyzers.spot_name_normaliser import (
    ISO_19593_GROUP_BY_CANONICAL,
    POSITION_TOKENS,
    WHITE_SUBTYPE_TOKENS,
    find_canonical_name,
    normalise_spot_name,
)
from lintpdf.primitives import register

# ---- name & classification predicates -------------------------------------

#: PDF process-color names. Black covers both DeviceCMYK K plate and
#: Black-as-Separation (Phase 2 Q2 operator decision).
_PROCESS_NAMES = frozenset(
    {
        "Cyan",
        "Magenta",
        "Yellow",
        "Black",
        "Gray",
        "DeviceCMYK",
        "DeviceRGB",
        "DeviceGray",
        "Red",
        "Green",
        "Blue",
    }
)

#: Reserved ink names per ISO 32000-2 §8.6.6.4 — must never be used as
#: artwork spot colors. ``All`` paints to every plate; ``None`` paints to
#: none; ``Registration`` is a synonym for ``All`` for printer marks.
_RESERVED_NAMES = frozenset(
    {
        "Cyan",
        "Magenta",
        "Yellow",
        "Black",
        "All",
        "None",
        "Registration",
    }
)


def name(spot: Any) -> str | None:
    """Return the bare-name string for a Separation/DeviceN spot, or None.

    Accepts:
        - Plain string ``"PANTONE 185 C"`` or ``"/PANTONE 185 C"``
        - Separation array ``["Separation", "PANTONE 185 C", alt, tint]``
        - DeviceN array ``["DeviceN", ["C","M","Y","K"], alt, tint]``
          (returns the joined name, e.g. ``"C+M+Y+K"``)
        - bytes / pikepdf.Name (coerced via str())
    """
    text = _coerce_name(spot)
    if text is not None:
        return text
    if isinstance(spot, Sequence) and not isinstance(spot, (str, bytes)) and len(spot) >= 2:
        head = _coerce_name(spot[0])
        if head == "Separation":
            return _coerce_name(spot[1])
        if head == "DeviceN":
            inks = spot[1]
            if isinstance(inks, Sequence) and not isinstance(inks, (str, bytes)):
                joined = "+".join(filter(None, (_coerce_name(i) for i in inks)))
                return joined or None
    return None


def is_process(name_or_spot: Any) -> bool:
    """True for Cyan / Magenta / Yellow / Black / Gray + DeviceN of process inks.

    Black-as-Separation is process (Phase 2 Batch 3 Q2 decision).
    """
    text = name(name_or_spot)
    if text is None:
        return False
    if "+" in text:
        return all(part in _PROCESS_NAMES for part in text.split("+"))
    return text in _PROCESS_NAMES


def is_spot(name_or_spot: Any) -> bool:
    """True for non-reserved, non-process spot names (PANTONE, HKS, custom)."""
    text = name(name_or_spot)
    if text is None:
        return False
    if "+" in text:
        # Multi-ink DeviceN: spot iff any component is non-process and non-reserved
        return any(
            part and part not in _PROCESS_NAMES and part not in _RESERVED_NAMES
            for part in text.split("+")
        )
    return text not in _PROCESS_NAMES and text not in _RESERVED_NAMES


def is_reserved_name(name_or_spot: Any) -> bool:
    """True for the seven reserved names: Cyan/Magenta/Yellow/Black/All/None/Registration."""
    text = name(name_or_spot)
    return text in _RESERVED_NAMES if text else False


# ---- Lab / alt-CMYK extraction --------------------------------------------


def lab_value(spot_cs: Any) -> tuple[float, float, float] | None:
    """Return Lab tuple if the Separation/DeviceN alt-space is Lab and the
    tint transform's C1 (output at tint=1.0) is 3-component.

    Returns None for non-Lab alts or non-extractable tint transforms.
    """
    if not _is_separation_or_devicen(spot_cs) or len(spot_cs) < 4:
        return None
    alt = spot_cs[2]
    if not _is_lab_array(alt):
        return None
    return _extract_c1_3tuple(spot_cs[3])


def alt_cmyk(spot_cs: Any) -> tuple[float, float, float, float] | None:
    """Return CMYK 4-tuple from the tint transform's C1 if alt is DeviceCMYK."""
    if not _is_separation_or_devicen(spot_cs) or len(spot_cs) < 4:
        return None
    alt = spot_cs[2]
    if _coerce_name(alt) != "DeviceCMYK":
        return None
    return _extract_c1_4tuple(spot_cs[3])


def alt_lab(spot_cs: Any) -> tuple[float, float, float] | None:
    """Alias of :func:`lab_value` for symmetry with :func:`alt_cmyk`."""
    return lab_value(spot_cs)


# ---- library matching -----------------------------------------------------

#: Pantone book naming: PANTONE <number><suffix> or PANTONE <named-color>.
#: Suffixes: C (coated), U (uncoated), M (matte), CP/UP (process simulation),
#: HC (high-chroma), PC (process), Q (proofing), N (neon).
#: Named: "Reflex Blue C", "Process Yellow C", etc.
_PANTONE_RE = re.compile(
    r"""
    ^PANTONE\s+
    (?:
        \d{3,4}                               # numeric: 185
        |
        (?:Reflex|Rubine|Rhodamine|Process|Warm|Cool|Black|Yellow|Bright|Trans)
        \s+ \w+                               # named: Reflex Blue
    )
    [\s\w]* \s*                               # optional suffix words
    [CUMHPNQ]+(?:P)?                          # finishing code: C, U, M, CP, UP, HC, PC, etc.
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

_HKS_RE = re.compile(r"^HKS\s+\d+\s*[KNZE]?\s*$", re.IGNORECASE)

_RAL_RE = re.compile(r"^RAL\s+\d{4}\s*$", re.IGNORECASE)

_TOYO_RE = re.compile(r"^TOYO\s+\d{3,4}\s*$", re.IGNORECASE)

_DIC_RE = re.compile(r"^DIC\s+\d{3,4}\s*[a-z]?\s*$", re.IGNORECASE)

_ANPA_RE = re.compile(r"^ANPA\s+\d{1,4}\s*$", re.IGNORECASE)

_LIBRARY_PATTERNS: dict[str, re.Pattern[str]] = {
    "pantone": _PANTONE_RE,
    "hks": _HKS_RE,
    "ral": _RAL_RE,
    "toyo": _TOYO_RE,
    "dic": _DIC_RE,
    "anpa": _ANPA_RE,
}


def matches_library(
    name_or_spot: Any,
    library: str,
    *,
    custom_pattern: str | None = None,
) -> bool:
    """Test whether a spot name matches a library naming convention.

    ``library`` is one of: ``pantone``, ``hks``, ``ral``, ``toyo``, ``dic``,
    ``anpa``, ``custom`` (provide ``custom_pattern`` regex). Case-insensitive.
    Returns False for unknown libraries.
    """
    text = name(name_or_spot)
    if text is None:
        return False
    library_lc = library.lower()
    if library_lc == "custom":
        if not custom_pattern:
            return False
        try:
            return bool(re.match(custom_pattern, text, re.IGNORECASE))
        except re.error:
            return False
    pattern = _LIBRARY_PATTERNS.get(library_lc)
    if pattern is None:
        return False
    return bool(pattern.match(text))


# ---- ISO 19593-1 processing-step semantics --------------------------------


def is_processing_step(name_or_spot: Any) -> bool:
    """True iff the name maps to an ISO 19593-1 ProcessingSteps group.

    Wraps :func:`lintpdf.analyzers.spot_name_normaliser.find_canonical_name`
    + :data:`POSITION_TOKENS` to cover Structural / Braille / Information /
    Positions / White / Varnish / Custom.
    """
    text = name(name_or_spot)
    if text is None:
        return False
    canonical = find_canonical_name(text)
    if canonical is not None:
        return True
    normalized = normalise_spot_name(text)
    return normalized in POSITION_TOKENS


def processing_step_group(name_or_spot: Any) -> str | None:
    """Return the Title-Case ISO 19593-1 group name for a processing-step spot.

    Returns one of: Structural, Braille, Information, Positions, White,
    Varnish, Custom — or None if the name is not a processing step.

    Phase 2 Batch 3 Q3 decision: Title-Case to match ISO 19593-1 verbatim.
    """
    text = name(name_or_spot)
    if text is None:
        return None
    canonical = find_canonical_name(text)
    if canonical is not None:
        iso_group = ISO_19593_GROUP_BY_CANONICAL.get(canonical)
        if iso_group is not None:
            return _iso_group_to_step_group(iso_group)
    normalized = normalise_spot_name(text)
    if normalized in POSITION_TOKENS:
        return "Positions"
    return None


def processing_step_type(name_or_spot: Any) -> str | None:
    """Return the specific ISO 19593-1 type (Cutting, Folding, Glueing, etc.)
    for a processing-step spot, or None.

    This is the more granular type within a group; e.g.,
    ``CutContour`` → group=Structural, type=Cutting; ``Crease`` → group=Structural,
    type=Folding.
    """
    text = name(name_or_spot)
    if text is None:
        return None
    canonical = find_canonical_name(text)
    if canonical is not None:
        return ISO_19593_GROUP_BY_CANONICAL.get(canonical)
    if normalise_spot_name(text) in POSITION_TOKENS:
        return "Positions"
    if any(token in text.lower() for token in WHITE_SUBTYPE_TOKENS):
        return "White"
    return None


# ---- internals ------------------------------------------------------------


def _iso_group_to_step_group(iso_group: str) -> str:
    """Map ISO 19593-1 type to its parent group (Title-Case)."""
    mapping = {
        "Cutting": "Structural",
        "KissCutting": "Structural",
        "Folding": "Structural",
        "Perforating": "Structural",
        "White": "White",
        "Varnish": "Varnish",
        "VarnishFree": "Varnish",
    }
    return mapping.get(iso_group, "Custom")


def _coerce_name(value: Any) -> str | None:
    """Coerce a name-like scalar to a bare-name string.

    Returns None for sequences (lists, tuples, arrays) so callers can
    distinguish "this is an array, walk into it" from "this is a name token".
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return None
    if isinstance(value, str):
        text = value
    elif isinstance(value, bytes):
        text = value.decode("latin-1", errors="replace")
    else:
        text = str(value)
    return text[1:] if text.startswith("/") else text or None


def _is_separation_or_devicen(spot_cs: Any) -> bool:
    if not isinstance(spot_cs, Sequence) or isinstance(spot_cs, (str, bytes)):
        return False
    if len(spot_cs) < 2:
        return False
    head = _coerce_name(spot_cs[0])
    return head in {"Separation", "DeviceN"}


def _is_lab_array(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return False
    if len(value) < 1:
        return False
    return _coerce_name(value[0]) == "Lab"


def _extract_c1_3tuple(func: Any) -> tuple[float, float, float] | None:
    if not isinstance(func, Mapping):
        return None
    c1 = func.get("C1") or func.get("/C1")
    if not isinstance(c1, Sequence) or isinstance(c1, (str, bytes)) or len(c1) < 3:
        return None
    try:
        return (float(c1[0]), float(c1[1]), float(c1[2]))
    except (TypeError, ValueError):
        return None


def _extract_c1_4tuple(func: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(func, Mapping):
        return None
    c1 = func.get("C1") or func.get("/C1")
    if not isinstance(c1, Sequence) or isinstance(c1, (str, bytes)) or len(c1) < 4:
        return None
    try:
        return (float(c1[0]), float(c1[1]), float(c1[2]), float(c1[3]))
    except (TypeError, ValueError):
        return None


# ---- registry -------------------------------------------------------------

for _name in (
    "name",
    "is_process",
    "is_spot",
    "is_reserved_name",
    "lab_value",
    "alt_cmyk",
    "alt_lab",
    "matches_library",
    "is_processing_step",
    "processing_step_group",
    "processing_step_type",
):
    register("ink", _name, globals()[_name])

del _name


__all__ = [
    "alt_cmyk",
    "alt_lab",
    "is_process",
    "is_processing_step",
    "is_reserved_name",
    "is_spot",
    "lab_value",
    "matches_library",
    "name",
    "processing_step_group",
    "processing_step_type",
]
