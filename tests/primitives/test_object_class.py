"""Tests for object-class primitives (Tier-0 Batch 01)."""

from __future__ import annotations

import pytest

from siftpdf.primitives import REGISTRY, object_class

# ---- registry --------------------------------------------------------------


def test_registry_contains_all_eight_predicates():
    """All 8 object-class predicates registered under 'object_class'."""
    expected = {
        "is_text",
        "is_image",
        "is_path",
        "is_form_xobject",
        "is_shading",
        "is_inline_image",
        "is_clipping_path",
        "is_pattern",
    }
    assert REGISTRY.get("object_class", {}).keys() == expected


def test_registry_callable_matches_module_attr():
    for name in REGISTRY["object_class"]:
        assert REGISTRY["object_class"][name] is getattr(object_class, name)


# ---- from_parser_tuple ----------------------------------------------------


def test_from_parser_tuple_swaps_ordering():
    operator, operands = object_class.from_parser_tuple(([1, 2, 3], "Tj"))
    assert operator == "Tj"
    assert operands == [1, 2, 3]


# ---- is_text --------------------------------------------------------------


@pytest.mark.parametrize("op", ["Tj", "TJ", "'", '"'])
def test_is_text_true_for_show_operators(op):
    assert object_class.is_text(op, []) is True


@pytest.mark.parametrize("op", ["Tf", "Tm", "BT", "ET", "Td", "TD", "T*", "Ts", "Tw"])
def test_is_text_false_for_text_state_operators(op):
    """Text-state operators set state but don't show text → False."""
    assert object_class.is_text(op, []) is False


def test_is_text_false_for_unrelated_operators():
    assert object_class.is_text("S", []) is False
    assert object_class.is_text("Do", ["Im0"]) is False


# ---- is_image -------------------------------------------------------------


def test_is_image_inline_image_sentinel():
    assert object_class.is_image("BI_ID_EI", []) is True


def test_is_image_do_with_image_xobject():
    resources = {"XObject": {"Im0": {"Subtype": "Image"}}}
    assert object_class.is_image("Do", ["/Im0"], resources=resources) is True


def test_is_image_do_with_form_xobject_returns_false():
    resources = {"XObject": {"Fm0": {"Subtype": "Form"}}}
    assert object_class.is_image("Do", ["/Fm0"], resources=resources) is False


def test_is_image_do_without_resources_returns_false():
    """Do without resources is ambiguous — return False."""
    assert object_class.is_image("Do", ["/Im0"]) is False


def test_is_image_unknown_xobject_returns_false():
    resources = {"XObject": {}}
    assert object_class.is_image("Do", ["/Missing"], resources=resources) is False


# ---- is_path --------------------------------------------------------------


@pytest.mark.parametrize("op", ["S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"])
def test_is_path_true_for_paint_operators(op):
    assert object_class.is_path(op, []) is True


@pytest.mark.parametrize("op", ["m", "l", "c", "v", "y", "re", "h"])
def test_is_path_false_for_construction_operators(op):
    """Path-construction operators only build the current path — False."""
    assert object_class.is_path(op, []) is False


def test_is_path_n_no_op_still_returns_true():
    """`n` is no-paint but still terminates a path object → True."""
    assert object_class.is_path("n", []) is True


# ---- is_form_xobject ------------------------------------------------------


def test_is_form_xobject_true_for_form_subtype():
    resources = {"XObject": {"Fm0": {"Subtype": "Form"}}}
    assert object_class.is_form_xobject("Do", ["/Fm0"], resources=resources) is True


def test_is_form_xobject_false_for_image_subtype():
    resources = {"XObject": {"Im0": {"Subtype": "Image"}}}
    assert object_class.is_form_xobject("Do", ["/Im0"], resources=resources) is False


def test_is_form_xobject_without_resources_returns_false():
    assert object_class.is_form_xobject("Do", ["/Fm0"]) is False


# ---- is_shading -----------------------------------------------------------


def test_is_shading_true_for_sh():
    assert object_class.is_shading("sh", ["/Sh0"]) is True


def test_is_shading_false_for_pattern_only_path():
    assert object_class.is_shading("scn", []) is False


# ---- is_inline_image ------------------------------------------------------


def test_is_inline_image_true_for_sentinel():
    assert object_class.is_inline_image("BI_ID_EI", []) is True


def test_is_inline_image_false_for_normal_do():
    assert object_class.is_inline_image("Do", ["/Im0"]) is False


# ---- is_clipping_path -----------------------------------------------------


def test_is_clipping_path_true_for_w_op():
    assert object_class.is_clipping_path("W", []) is True


def test_is_clipping_path_true_for_w_star_op():
    assert object_class.is_clipping_path("W*", []) is True


def test_is_clipping_path_true_with_active_clip_state():
    state = {"active_clip": True}
    assert object_class.is_clipping_path("S", [], graphics_state=state) is True


def test_is_clipping_path_true_with_clip_stack():
    state = {"clip_stack": [object()]}
    assert object_class.is_clipping_path("S", [], graphics_state=state) is True


def test_is_clipping_path_false_without_active_state():
    assert object_class.is_clipping_path("S", []) is False
    assert object_class.is_clipping_path("S", [], graphics_state={}) is False


# ---- is_pattern -----------------------------------------------------------


def test_is_pattern_true_for_cs_pattern():
    assert object_class.is_pattern("cs", ["Pattern"]) is True
    assert object_class.is_pattern("CS", ["Pattern"]) is True


def test_is_pattern_true_for_state_with_fill_pattern():
    state = {"fill_color_space": "Pattern"}
    assert object_class.is_pattern("f", [], graphics_state=state) is True


def test_is_pattern_true_for_state_with_stroke_pattern():
    state = {"stroke_color_space": "Pattern"}
    assert object_class.is_pattern("S", [], graphics_state=state) is True


def test_is_pattern_false_for_devicergb_state():
    state = {"fill_color_space": "DeviceRGB", "stroke_color_space": "DeviceRGB"}
    assert object_class.is_pattern("f", [], graphics_state=state) is False


def test_is_pattern_false_without_state_or_pattern_op():
    assert object_class.is_pattern("S", []) is False


# ---- edge cases (per design.md §"Edge cases") ------------------------------


def test_form_inside_form_distinguishes_outer_do_from_inner_text():
    """Edge case 1: Form XObject containing text. Outer Do classified as
    form_xobject; inner Tj inside the form classified as text.
    """
    resources = {"XObject": {"Fm0": {"Subtype": "Form"}}}
    # outer
    assert object_class.is_form_xobject("Do", ["/Fm0"], resources=resources) is True
    assert object_class.is_text("Do", ["/Fm0"]) is False
    # inner (would be parsed when walking into the form's own content stream)
    assert object_class.is_text("Tj", [b"Hello"]) is True
    assert object_class.is_form_xobject("Tj", [b"Hello"]) is False


def test_inline_image_with_ei_in_data_does_not_split():
    """Edge case 2: parser collapses the entire BI...EI block into one
    sentinel even if EI appears inside the image bytes.
    """
    # Verified at the parser level (parse_content_stream). Primitive layer
    # only sees the single BI_ID_EI sentinel.
    assert object_class.is_inline_image("BI_ID_EI", []) is True


def test_shading_via_sh_distinct_from_pattern_shading():
    """Edge case 4: sh operator is_shading; pattern-shading is_pattern."""
    assert object_class.is_shading("sh", ["/Sh0"]) is True
    assert object_class.is_pattern("sh", ["/Sh0"]) is False
    # Pattern-shading via cs Pattern + scn
    assert object_class.is_pattern("cs", ["Pattern"]) is True
    assert object_class.is_shading("cs", ["Pattern"]) is False


def test_nested_clipping_remains_true():
    """Edge case 5: nested clip paths remain True throughout the inner stack."""
    state = {"clip_stack": [object(), object(), object()]}
    assert object_class.is_clipping_path("S", [], graphics_state=state) is True
