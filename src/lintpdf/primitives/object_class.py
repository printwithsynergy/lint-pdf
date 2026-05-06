"""Object-class predicates — Tier-0 Batch 01.

Classifies a content-stream operator+operand tuple into one of the standard
PDF object classes (text, image, path, form xobject, shading, inline image,
clipping path, pattern). Per universe enumeration §4.1.

All predicates take a Python tuple ``(operator: str, operands: list)`` plus
optional graphics-state context, and return ``bool``. They do not mutate
state. They do not raise on unknown operators (return ``False``).

Legacy stream tokenizers often emit ``(operands, operator)`` tuples.
These predicates accept the swapped ``(operator, operands)`` ordering
for readability; callers can swap with :func:`from_parser_tuple`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lintpdf.primitives import register

# PDF Reference Table 51 — text-showing operators. ``Tj``, ``TJ`` show text;
# ``'`` and ``"`` show text and advance text position.
_TEXT_SHOW_OPS = frozenset({"Tj", "TJ", "'", '"'})

# Path painting operators per PDF Reference Table 60. Includes ``n`` (no-op
# path used for clipping). All of these terminate a path-construction
# segment and emit a path object.
_PATH_PAINT_OPS = frozenset(
    {
        "S",
        "s",  # stroke
        "f",
        "F",
        "f*",  # fill
        "B",
        "B*",  # fill + stroke
        "b",
        "b*",  # close + fill + stroke
        "n",  # no-op (paint nothing)
    }
)

# Shading operator
_SHADING_OPS = frozenset({"sh"})

# Sentinel produced by pikepdf adapter for inline images
_INLINE_IMAGE_SENTINEL = "BI_ID_EI"


def from_parser_tuple(parser_tuple: tuple[list[Any], str]) -> tuple[str, list[Any]]:
    """Swap ``(operands, operator)`` to ``(operator, operands)``.

    Some tokenizers return ``(operands, operator_name)`` per stream
    element. Predicates here expect ``(operator, operands)`` for readability.
    """
    operands, operator = parser_tuple
    return operator, operands


def is_text(operator: str, operands: list[Any] | tuple[Any, ...] | None = None) -> bool:
    """True for content-stream operators that show text glyphs.

    Covers ``Tj``, ``TJ`` (show array), ``'`` (next-line show),
    ``"`` (next-line with word/char spacing).

    Note: text-state operators (``Tf``, ``Tm``, ``BT``/``ET``, ``Td``/``TD``,
    ``T*``, ``Ts``, ``Tw``, ``Tc``, ``Tr``, ``Tz``, ``TL``) only set text
    state and do not show text — they return False here. Callers wanting
    "is this object inside a BT...ET block" must track that with graphics
    state, not by inspecting a single operator.
    """
    return operator in _TEXT_SHOW_OPS


def is_image(
    operator: str,
    operands: list[Any] | tuple[Any, ...] | None = None,
    *,
    resources: Mapping[str, Any] | None = None,
) -> bool:
    """True for content operators that render a raster image.

    Two emit forms:
    - ``Do`` referencing an Image XObject (named in page Resources/XObject
      with ``/Subtype /Image``). Caller must pass ``resources`` (page
      resource dictionary) to disambiguate Image XObjects from Form
      XObjects.
    - ``BI ... ID ... EI`` inline images (the parser yields a single
      synthetic ``BI_ID_EI`` operator).

    If ``resources`` is omitted for a ``Do``, returns False (cannot
    disambiguate). Callers that don't have resources should call
    :func:`is_inline_image` separately.
    """
    if operator == _INLINE_IMAGE_SENTINEL:
        return True
    if operator != "Do":
        return False
    if not operands or not resources:
        return False
    name = _resolve_xobject_name(operands[0])
    if name is None:
        return False
    xo = resources.get("XObject") or resources.get("/XObject") or {}
    target = xo.get(name) or xo.get("/" + name)
    if not isinstance(target, Mapping):
        return False
    subtype = target.get("Subtype") or target.get("/Subtype")
    return _stringify(subtype) == "Image"


def is_path(operator: str, operands: list[Any] | tuple[Any, ...] | None = None) -> bool:
    """True for path-painting operators (stroke, fill, close, no-op).

    Returns True for ``S s f F f* B B* b b* n``.

    Path-construction operators (``m``, ``l``, ``c``, ``v``, ``y``, ``re``,
    ``h``) only build the current path; they don't emit a path object on
    their own. They return False here — wait for a paint operator.
    """
    return operator in _PATH_PAINT_OPS


def is_form_xobject(
    operator: str,
    operands: list[Any] | tuple[Any, ...] | None = None,
    *,
    resources: Mapping[str, Any] | None = None,
) -> bool:
    """True for ``Do`` referencing a Form XObject (Subtype = Form).

    Like :func:`is_image`, requires ``resources`` to disambiguate Form
    from Image XObjects. Returns False without resources.
    """
    if operator != "Do" or not operands or not resources:
        return False
    name = _resolve_xobject_name(operands[0])
    if name is None:
        return False
    xo = resources.get("XObject") or resources.get("/XObject") or {}
    target = xo.get(name) or xo.get("/" + name)
    if not isinstance(target, Mapping):
        return False
    subtype = target.get("Subtype") or target.get("/Subtype")
    return _stringify(subtype) == "Form"


def is_shading(operator: str, operands: list[Any] | tuple[Any, ...] | None = None) -> bool:
    """True for the ``sh`` operator (paint a shading dictionary).

    Note: shading via Pattern color-space (``cs /Pattern scn``) is detected
    by :func:`is_pattern`, not here.
    """
    return operator in _SHADING_OPS


def is_inline_image(operator: str, operands: list[Any] | tuple[Any, ...] | None = None) -> bool:
    """True for the synthetic ``BI_ID_EI`` operator emitted by the parser.

    The pikepdf adapter collapses ``BI ... ID ... EI`` blocks into a single
    sentinel so primitives can detect them without re-tokenizing the inline
    image bytes.
    """
    return operator == _INLINE_IMAGE_SENTINEL


def is_clipping_path(
    operator: str,
    operands: list[Any] | tuple[Any, ...] | None = None,
    *,
    graphics_state: Mapping[str, Any] | None = None,
) -> bool:
    """True when the current graphics state has an active clipping path.

    Per playbook §0.6 design Q4: True for any active clip in state, NOT just
    the clip-establishing operator (``W`` / ``W*``). Most callers want "is
    this object being clipped?" rather than "is this the clip-establishing
    operator?".

    Without ``graphics_state``, returns False unless the operator is a
    clip-establishing operator itself.
    """
    if operator in {"W", "W*"}:
        return True
    if graphics_state is None:
        return False
    return bool(graphics_state.get("active_clip") or graphics_state.get("clip_stack"))


def is_pattern(
    operator: str,
    operands: list[Any] | tuple[Any, ...] | None = None,
    *,
    graphics_state: Mapping[str, Any] | None = None,
) -> bool:
    """True when the active fill or stroke uses a Pattern color-space.

    Detected by inspecting graphics state's color-space slots:
    ``fill_color_space`` or ``stroke_color_space`` equal to ``/Pattern``,
    or ``scn``/``SCN`` operators with a Pattern name argument.

    Without ``graphics_state``, returns True only when the operator itself
    declares a Pattern color-space:
    ``cs /Pattern`` / ``CS /Pattern``.
    """
    if operator in {"cs", "CS"} and operands:
        return _stringify(operands[0]) == "Pattern"
    if graphics_state is None:
        return False
    fill_cs = _stringify(graphics_state.get("fill_color_space"))
    stroke_cs = _stringify(graphics_state.get("stroke_color_space"))
    return fill_cs == "Pattern" or stroke_cs == "Pattern"


def _resolve_xobject_name(operand: Any) -> str | None:
    """Strip leading ``/`` from a name-token operand, returning bare name."""
    text = _stringify(operand)
    if text is None:
        return None
    return text[1:] if text.startswith("/") else text


def _stringify(value: Any) -> str | None:
    """Coerce a pikepdf Name / str / bytes operand to a plain Python str."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("latin-1", errors="replace")
    return str(value)


# Register predicates for runtime introspection.
register("object_class", "is_text", is_text)
register("object_class", "is_image", is_image)
register("object_class", "is_path", is_path)
register("object_class", "is_form_xobject", is_form_xobject)
register("object_class", "is_shading", is_shading)
register("object_class", "is_inline_image", is_inline_image)
register("object_class", "is_clipping_path", is_clipping_path)
register("object_class", "is_pattern", is_pattern)


__all__ = [
    "from_parser_tuple",
    "is_clipping_path",
    "is_form_xobject",
    "is_image",
    "is_inline_image",
    "is_path",
    "is_pattern",
    "is_shading",
    "is_text",
]
