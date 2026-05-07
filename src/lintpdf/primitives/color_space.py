"""Color-space predicates — Tier-0 Batch 02.

Classifies a PDF color-space (resolved name, array, or dict) into one of
the standard PDF color-space families. Per universe enumeration §4.2.

Predicate names use **PascalCase** verbatim from the universe enumeration
to honor the canonical reference (operator decision Phase 2 Q1).

Input shape: a "color space" can be:
    - Plain string name: ``"DeviceRGB"``, ``"DeviceCMYK"``, ``"/DeviceGray"``
    - List/array: ``["CalGray", {...}]`` or ``["DeviceN", names, alt, tint]``
    - pikepdf Name / Array / Dictionary already coerced to plain Python types
    - Any object exposing ``__getitem__`` / ``__len__`` for arrays

Predicates handle both with-leading-slash (``"/DeviceRGB"``) and bare
(``"DeviceRGB"``) name forms, and tolerate ``bytes`` / ``str`` / pikepdf
``Name`` objects (coerced via ``str()``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from lintpdf.codex_render import eval_type4 as _codex_eval_type4
from lintpdf.primitives import register

# Canonical names — bare (no leading slash) for matching after normalization.
_DEVICE_CMYK = "DeviceCMYK"
_DEVICE_RGB = "DeviceRGB"
_DEVICE_GRAY = "DeviceGray"
_CAL_RGB = "CalRGB"
_CAL_GRAY = "CalGray"
_LAB = "Lab"
_ICC_BASED = "ICCBased"
_SEPARATION = "Separation"
_DEVICE_N = "DeviceN"
_INDEXED = "Indexed"
_PATTERN = "Pattern"


# ---- coercion helpers -----------------------------------------------------


def _normalize_name(value: Any) -> str | None:
    """Coerce a name token (str / bytes / pikepdf.Name) to a bare-name str.

    Strips a leading ``/`` if present. Returns None if the input cannot be
    coerced to a name-like string.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value[1:] if value.startswith("/") else value
    if isinstance(value, bytes):
        text = value.decode("latin-1", errors="replace")
        return text[1:] if text.startswith("/") else text
    text = str(value)
    return text[1:] if text.startswith("/") else text


def _array_head(cs: Any) -> str | None:
    """Return the bare-name first element of a color-space array, or None."""
    if isinstance(cs, Sequence) and not isinstance(cs, (str, bytes)):
        if len(cs) == 0:
            return None
        return _normalize_name(cs[0])
    return None


def _is_name(cs: Any, expected: str) -> bool:
    """True iff ``cs`` is a name token equal to ``expected`` (bare form)."""
    name = _normalize_name(cs)
    return name == expected


def _is_array_starting_with(cs: Any, expected: str) -> bool:
    head = _array_head(cs)
    return head == expected


# ---- type predicates (PascalCase per Phase 2 Q1) --------------------------


def is_DeviceCMYK(cs: Any) -> bool:
    """True for the ``/DeviceCMYK`` name token."""
    return _is_name(cs, _DEVICE_CMYK)


def is_DeviceRGB(cs: Any) -> bool:
    """True for the ``/DeviceRGB`` name token."""
    return _is_name(cs, _DEVICE_RGB)


def is_DeviceGray(cs: Any) -> bool:
    """True for the ``/DeviceGray`` name token."""
    return _is_name(cs, _DEVICE_GRAY)


def is_CalRGB(cs: Any) -> bool:
    """True for ``[/CalRGB <<dict>>]`` arrays."""
    return _is_array_starting_with(cs, _CAL_RGB)


def is_CalGray(cs: Any) -> bool:
    """True for ``[/CalGray <<dict>>]`` arrays."""
    return _is_array_starting_with(cs, _CAL_GRAY)


def is_Lab(cs: Any) -> bool:
    """True for ``[/Lab <<dict>>]`` arrays."""
    return _is_array_starting_with(cs, _LAB)


def is_ICCBased(cs: Any) -> bool:
    """True for ``[/ICCBased <<stream>>]`` arrays.

    Per Phase 2 Q1 (Indexed/ICC): if the cs is Indexed and its base is
    ICCBased, this returns False (cs type is Indexed; callers wanting
    the base should invoke :func:`alternate_space`).
    """
    return _is_array_starting_with(cs, _ICC_BASED)


def is_Separation(cs: Any) -> bool:
    """True for ``[/Separation name alt tint]`` arrays."""
    return _is_array_starting_with(cs, _SEPARATION)


def is_DeviceN(cs: Any) -> bool:
    """True for ``[/DeviceN ...]`` arrays (includes NChannel subtype)."""
    return _is_array_starting_with(cs, _DEVICE_N)


def is_NChannel(cs: Any) -> bool:
    """True for DeviceN arrays whose attributes dict has Subtype = NChannel.

    Per ISO 32000-2 §8.6.6.5 / Phase 2 Q1, NChannel is a DeviceN subtype.
    Detection: array starts with ``/DeviceN`` AND a 5th element (attributes
    dict) has ``Subtype == NChannel``.
    """
    if not _is_array_starting_with(cs, _DEVICE_N):
        return False
    if not isinstance(cs, Sequence) or isinstance(cs, (str, bytes)):
        return False
    if len(cs) < 5:
        return False
    attrs = cs[4]
    if not isinstance(attrs, Mapping):
        return False
    subtype = attrs.get("Subtype") or attrs.get("/Subtype")
    return _normalize_name(subtype) == "NChannel"


def is_Indexed(cs: Any) -> bool:
    """True for ``[/Indexed base hival lookup]`` arrays."""
    return _is_array_starting_with(cs, _INDEXED)


def is_Pattern(cs: Any) -> bool:
    """True for the ``/Pattern`` name token or ``[/Pattern alt]`` arrays."""
    if _is_name(cs, _PATTERN):
        return True
    return _is_array_starting_with(cs, _PATTERN)


def is_Shading(cs: Any) -> bool:
    """True when ``cs`` is a shading dictionary (has ShadingType key).

    Note: in PDF, shading is normally invoked via the ``sh`` operator (see
    :func:`lintpdf.primitives.object_class.is_shading`); a "shading color
    space" is the form found inside SMask Form XObjects' ``/G`` group.
    """
    if not isinstance(cs, Mapping):
        return False
    return "ShadingType" in cs or "/ShadingType" in cs


# ---- inspection helpers ---------------------------------------------------


def alternate_space(cs: Any) -> Any | None:
    """Return the alternate (process) color space for Separation / DeviceN /
    ICCBased / Indexed.

    - Separation: ``[/Separation name alt tint]`` → ``alt`` (index 2)
    - DeviceN: ``[/DeviceN names alt tint ...]`` → ``alt`` (index 2)
    - ICCBased: looks up ``/Alternate`` in the ICC stream's dictionary
    - Indexed: ``[/Indexed base hival lookup]`` → ``base`` (index 1)
    Returns None for spaces that have no alternate (Device*, Cal*, Lab,
    Pattern name, Shading).
    """
    if isinstance(cs, Sequence) and not isinstance(cs, (str, bytes)) and len(cs) >= 2:
        head = _normalize_name(cs[0])
        if head in {_SEPARATION, _DEVICE_N} and len(cs) >= 3:
            return cs[2]
        if head == _INDEXED and len(cs) >= 2:
            return cs[1]
        if head == _ICC_BASED and len(cs) >= 2:
            stream = cs[1]
            if isinstance(stream, Mapping):
                return stream.get("Alternate") or stream.get("/Alternate")
    return None


def tint_transform_is_zero(cs: Any) -> bool:
    """True iff a Separation or DeviceN tint transform is a constant zero.

    Inspects the function dictionary at array index 3 (Separation / DeviceN
    layout). Supports FunctionTypes 0, 2, 3 directly; FunctionType 4 is
    evaluated via :mod:`lintpdf.primitives._ps_type4` at sample points
    [0.0, 0.5, 1.0]. Returns False on unknown FunctionType or unparseable
    program.

    Rationale: a zero-output tint transform means the spot/DeviceN plate
    contributes no ink to the alternate space — typically a stray ``All``
    color or a no-op spot.
    """
    if not isinstance(cs, Sequence) or isinstance(cs, (str, bytes)):
        return False
    head = _array_head(cs)
    if head not in {_SEPARATION, _DEVICE_N} or len(cs) < 4:
        return False
    func = cs[3]
    return _function_is_zero(func)


def _function_is_zero(func: Any) -> bool:
    """Recursive zero-check across PDF FunctionTypes 0/2/3/4."""
    if not isinstance(func, Mapping):
        return False
    ftype = func.get("FunctionType")
    if ftype is None:
        ftype = func.get("/FunctionType")
    if ftype == 0:
        # Sampled function — all sample bytes zero
        sample = func.get("_Samples") or func.get("Samples")
        if sample is None:
            # Caller didn't decode the stream; we cannot verify
            return False
        if isinstance(sample, (bytes, bytearray)):
            return all(b == 0 for b in sample)
        if isinstance(sample, Sequence):
            return all(int(s) == 0 for s in sample if not isinstance(s, (bytes, bytearray)))
        return False
    if ftype == 2:
        # Exponential function — C0 and C1 both zero
        c0 = func.get("C0") or func.get("/C0") or [0]
        c1 = func.get("C1") or func.get("/C1") or [1]
        return all(float(x) == 0 for x in _as_iter(c0)) and all(float(x) == 0 for x in _as_iter(c1))
    if ftype == 3:
        # Stitching — all sub-functions are zero
        subs = func.get("Functions") or func.get("/Functions") or []
        if not isinstance(subs, Sequence) or not subs:
            return False
        return all(_function_is_zero(s) for s in subs)
    if ftype == 4:
        # PostScript — evaluate at sample points via the codex client.
        # The codex engine owns PDF byte-level Type-4 evaluation; lint
        # never shells out to ``gs -dNODISPLAY`` directly any more.
        program = func.get("_Program") or func.get("Program")
        if program is None:
            return False
        if isinstance(program, bytes):
            program = program.decode("latin-1", errors="replace")
        for x in (0.0, 0.5, 1.0):
            result = _codex_eval_type4(program, inputs=[x])
            if result is None:
                return False
            if not all(abs(v) < 1e-9 for v in result):
                return False
        return True
    return False


def _as_iter(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return [value]


def icc_profile_version(cs: Any) -> str | None:
    """Inspect an ICCBased color-space's ICC profile bytes for v2/v4 marker.

    Per ICC.1:2010 §7.1.4: bytes 8-11 of the ICC header encode the profile
    version. The first byte's high nibble is the major version (2 or 4).
    Returns ``"v2"``, ``"v4"``, or None on unrecognized / missing bytes.
    """
    icc_bytes = _icc_header_bytes(cs)
    if icc_bytes is None or len(icc_bytes) < 12:
        return None
    major = icc_bytes[8] >> 4 & 0x0F
    if major == 2:
        return "v2"
    if major == 4:
        return "v4"
    return None


def icc_profile_class(cs: Any) -> str | None:
    """Return the ICC profile/device class for an ICCBased color-space.

    Per ICC.1:2010 §7.1.5: bytes 12-15 of the ICC header encode the
    profile/device class as 4 ASCII chars: scnr, mntr, prtr, link, spac,
    abst, nmcl. Mapped to friendly names.
    """
    icc_bytes = _icc_header_bytes(cs)
    if icc_bytes is None or len(icc_bytes) < 16:
        return None
    sig = icc_bytes[12:16].decode("latin-1", errors="replace")
    return {
        "scnr": "input",
        "mntr": "display",
        "prtr": "output",
        "link": "device_link",
        "spac": "color_space",
        "abst": "abstract",
        "nmcl": "named_color",
    }.get(sig)


def _icc_header_bytes(cs: Any) -> bytes | None:
    """Extract the first 128 bytes of an ICCBased color-space's profile stream."""
    if not isinstance(cs, Sequence) or isinstance(cs, (str, bytes)):
        return None
    if _array_head(cs) != _ICC_BASED or len(cs) < 2:
        return None
    stream = cs[1]
    if isinstance(stream, Mapping):
        data = stream.get("_StreamData") or stream.get("StreamData") or stream.get("_data")
        if isinstance(data, (bytes, bytearray)):
            return bytes(data[:128])
    if isinstance(stream, (bytes, bytearray)):
        return bytes(stream[:128])
    return None


# ---- registry -------------------------------------------------------------

for _name in (
    "is_DeviceCMYK",
    "is_DeviceRGB",
    "is_DeviceGray",
    "is_CalRGB",
    "is_CalGray",
    "is_Lab",
    "is_ICCBased",
    "is_Separation",
    "is_DeviceN",
    "is_NChannel",
    "is_Indexed",
    "is_Pattern",
    "is_Shading",
    "alternate_space",
    "tint_transform_is_zero",
    "icc_profile_version",
    "icc_profile_class",
):
    register("color_space", _name, globals()[_name])

del _name


__all__ = [
    "alternate_space",
    "icc_profile_class",
    "icc_profile_version",
    "is_CalGray",
    "is_CalRGB",
    "is_DeviceCMYK",
    "is_DeviceGray",
    "is_DeviceN",
    "is_DeviceRGB",
    "is_ICCBased",
    "is_Indexed",
    "is_Lab",
    "is_NChannel",
    "is_Pattern",
    "is_Separation",
    "is_Shading",
    "tint_transform_is_zero",
]
