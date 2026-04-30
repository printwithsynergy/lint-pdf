"""Tests for geometry primitives (Tier-0 Batch 04)."""

from __future__ import annotations

import math

import pytest

from siftpdf.primitives import REGISTRY, geometry

# ---- registry ------------------------------------------------------------


def test_registry_contains_all_twentythree_primitives():
    expected = {
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
    }
    assert REGISTRY.get("geometry", {}).keys() == expected


# ---- box accessors -------------------------------------------------------


class _MockPage:
    def __init__(self, **boxes):
        for name, value in boxes.items():
            setattr(self, name, value)


def test_box_accessors_extract_tuples():
    page = _MockPage(
        media_box=(0, 0, 612, 792),
        crop_box=(10, 10, 600, 780),
        trim_box=(20, 20, 590, 770),
        bleed_box=(0, 0, 612, 792),
        art_box=(30, 30, 580, 760),
    )
    assert geometry.media_box(page) == (0.0, 0.0, 612.0, 792.0)
    assert geometry.crop_box(page) == (10.0, 10.0, 600.0, 780.0)
    assert geometry.trim_box(page) == (20.0, 20.0, 590.0, 770.0)
    assert geometry.bleed_box(page) == (0.0, 0.0, 612.0, 792.0)
    assert geometry.art_box(page) == (30.0, 30.0, 580.0, 760.0)


def test_crop_box_falls_back_to_media_box():
    page = _MockPage(media_box=(0, 0, 100, 100), crop_box=None)
    assert geometry.crop_box(page) == (0.0, 0.0, 100.0, 100.0)


def test_trim_box_returns_none_when_absent():
    page = _MockPage(media_box=(0, 0, 100, 100), trim_box=None)
    assert geometry.trim_box(page) is None


def test_box_accessors_handle_missing_attributes():
    page = _MockPage()  # no attributes set
    assert geometry.media_box(page) is None
    assert geometry.trim_box(page) is None
    assert geometry.bleed_box(page) is None
    assert geometry.art_box(page) is None


# ---- box predicates -----------------------------------------------------


def test_box_contains_strict():
    outer = (0, 0, 100, 100)
    assert geometry.box_contains(outer, (10, 10, 90, 90)) is True
    assert geometry.box_contains(outer, (0, 0, 100, 100)) is True  # equal
    assert geometry.box_contains(outer, (-1, 0, 100, 100)) is False


def test_box_contains_with_eps():
    outer = (0, 0, 100, 100)
    inner = (-0.05, -0.05, 100.05, 100.05)
    assert geometry.box_contains(outer, inner) is False
    assert geometry.box_contains(outer, inner, eps=0.1) is True


def test_box_equals_with_eps():
    a = (0, 0, 100, 100)
    b = (0.001, 0, 100, 100)
    assert geometry.box_equals(a, b) is False
    assert geometry.box_equals(a, b, eps=0.01) is True


def test_box_predicates_none_safe():
    assert geometry.box_contains(None, (0, 0, 1, 1)) is False
    assert geometry.box_equals(None, None) is False


# ---- obj bbox / intersection -------------------------------------------


def test_obj_bbox_dict_keys():
    assert geometry.obj_bbox({"bbox": [0, 0, 10, 10]}) == (0.0, 0.0, 10.0, 10.0)
    assert geometry.obj_bbox({"BBox": (5, 5, 50, 50)}) == (5.0, 5.0, 50.0, 50.0)
    assert geometry.obj_bbox({"rect": (1, 2, 3, 4)}) == (1.0, 2.0, 3.0, 4.0)


def test_obj_bbox_attribute():
    class Obj:
        bbox = (10, 20, 30, 40)

    assert geometry.obj_bbox(Obj()) == (10.0, 20.0, 30.0, 40.0)


def test_obj_bbox_returns_none_when_absent():
    assert geometry.obj_bbox({}) is None
    assert geometry.obj_bbox(None) is None


def test_obj_intersects_overlapping():
    obj = {"bbox": (10, 10, 50, 50)}
    assert geometry.obj_intersects(obj, (0, 0, 30, 30)) is True


def test_obj_intersects_edge_touching():
    obj = {"bbox": (10, 10, 50, 50)}
    assert geometry.obj_intersects(obj, (50, 50, 100, 100)) is True


def test_obj_intersects_disjoint():
    obj = {"bbox": (10, 10, 20, 20)}
    assert geometry.obj_intersects(obj, (50, 50, 60, 60)) is False


def test_obj_outside():
    obj = {"bbox": (10, 10, 20, 20)}
    assert geometry.obj_outside(obj, (50, 50, 60, 60)) is True
    assert geometry.obj_outside(obj, (0, 0, 30, 30)) is False


def test_obj_within():
    obj = {"bbox": (20, 20, 80, 80)}
    page_box = (0, 0, 100, 100)
    assert geometry.obj_within(obj, page_box) is True
    # With margin, the safe area shrinks
    assert geometry.obj_within(obj, page_box, margin=25) is False
    assert geometry.obj_within(obj, page_box, margin=10) is True


# ---- path predicates ---------------------------------------------------


def test_path_is_closed_via_h():
    path = [("m", [0, 0]), ("l", [10, 0]), ("l", [10, 10]), ("h", [])]
    assert geometry.path_is_closed(path) is True


def test_path_is_closed_via_close_paint():
    path = [("m", [0, 0]), ("l", [10, 0]), ("s", [])]
    assert geometry.path_is_closed(path) is True


def test_path_is_open():
    path = [("m", [0, 0]), ("l", [10, 0]), ("S", [])]
    assert geometry.path_is_closed(path) is False


def test_path_node_count():
    path = [
        ("m", [0, 0]),
        ("l", [10, 0]),
        ("c", [10, 5, 5, 10, 0, 10]),
        ("h", []),
        ("S", []),
    ]
    assert geometry.path_node_count(path) == 4  # m, l, c, h (S is paint)


def test_path_self_intersects_simple_x():
    # Two crossing line segments
    path = [
        ("m", [0, 0]),
        ("l", [10, 10]),
        ("m", [0, 10]),
        ("l", [10, 0]),
        ("S", []),
    ]
    assert geometry.path_self_intersects(path) is True


def test_path_self_intersects_simple_square():
    """Closed square — does not self-intersect."""
    path = [
        ("m", [0, 0]),
        ("l", [10, 0]),
        ("l", [10, 10]),
        ("l", [0, 10]),
        ("h", []),
    ]
    assert geometry.path_self_intersects(path) is False


def test_path_self_intersects_too_few_segments():
    path = [("m", [0, 0]), ("l", [10, 0]), ("S", [])]
    assert geometry.path_self_intersects(path) is False


def test_path_is_dashed_with_array():
    assert geometry.path_is_dashed({"dash_array": [3, 2]}) is True


def test_path_is_dashed_empty_array():
    assert geometry.path_is_dashed({"dash_array": []}) is False


def test_path_is_dashed_no_state():
    assert geometry.path_is_dashed(None) is False
    assert geometry.path_is_dashed({}) is False


def test_path_dash_phase():
    assert geometry.path_dash_phase({"dash_phase": 1.5}) == 1.5
    assert geometry.path_dash_phase(None) == 0.0
    assert geometry.path_dash_phase({}) == 0.0


def test_path_miter_limit_default():
    assert geometry.path_miter_limit(None) == 10.0
    assert geometry.path_miter_limit({}) == 10.0


def test_path_miter_limit_set():
    assert geometry.path_miter_limit({"miter_limit": 4.0}) == 4.0


def test_path_line_cap():
    assert geometry.path_line_cap(None) == 0
    assert geometry.path_line_cap({"line_cap": 1}) == 1
    assert geometry.path_line_cap({"line_cap": 2}) == 2


# ---- transform / CTM predicates --------------------------------------


def test_obj_ctm_extracted_from_dict():
    obj = {"ctm": [1, 0, 0, 1, 50, 100]}
    assert geometry.obj_ctm(obj) == (1.0, 0.0, 0.0, 1.0, 50.0, 100.0)


def test_obj_ctm_returns_none_when_absent():
    assert geometry.obj_ctm({}) is None


def test_obj_rotation_zero_for_identity():
    assert geometry.obj_rotation({"ctm": [1, 0, 0, 1, 0, 0]}) == 0.0


def test_obj_rotation_90_degrees():
    """CTM for 90° rotation: a=0, b=1, c=-1, d=0."""
    obj = {"ctm": [0, 1, -1, 0, 0, 0]}
    assert geometry.obj_rotation(obj) == pytest.approx(90.0)


def test_obj_rotation_180_degrees():
    obj = {"ctm": [-1, 0, 0, -1, 0, 0]}
    assert geometry.obj_rotation(obj) == pytest.approx(180.0)


def test_obj_rotation_270_degrees():
    obj = {"ctm": [0, -1, 1, 0, 0, 0]}
    assert geometry.obj_rotation(obj) == pytest.approx(270.0)


def test_obj_rotation_no_ctm_returns_zero():
    assert geometry.obj_rotation({}) == 0.0


def test_obj_scale_xy_identity():
    assert geometry.obj_scale_xy({"ctm": [1, 0, 0, 1, 0, 0]}) == (1.0, 1.0)


def test_obj_scale_xy_uniform():
    assert geometry.obj_scale_xy({"ctm": [2, 0, 0, 2, 0, 0]}) == (2.0, 2.0)


def test_obj_scale_xy_non_uniform():
    assert geometry.obj_scale_xy({"ctm": [3, 0, 0, 5, 0, 0]}) == (3.0, 5.0)


def test_obj_scale_xy_with_rotation_extracts_magnitudes():
    """Pure rotation has scale = 1.0 even with non-zero off-diagonals."""
    angle = math.radians(45)
    ctm = [
        math.cos(angle),
        math.sin(angle),
        -math.sin(angle),
        math.cos(angle),
        0,
        0,
    ]
    sx, sy = geometry.obj_scale_xy({"ctm": ctm})
    assert sx == pytest.approx(1.0)
    assert sy == pytest.approx(1.0)


def test_obj_scale_xy_no_ctm_identity():
    assert geometry.obj_scale_xy({}) == (1.0, 1.0)


def test_obj_is_mirrored_negative_determinant():
    # X-axis flip: a=-1, d=1 → det = -1
    assert geometry.obj_is_mirrored({"ctm": [-1, 0, 0, 1, 0, 0]}) is True
    # Y-axis flip
    assert geometry.obj_is_mirrored({"ctm": [1, 0, 0, -1, 0, 0]}) is True


def test_obj_is_mirrored_false_for_identity():
    assert geometry.obj_is_mirrored({"ctm": [1, 0, 0, 1, 0, 0]}) is False


def test_obj_is_mirrored_false_for_pure_rotation():
    angle = math.radians(45)
    ctm = [math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0, 0]
    assert geometry.obj_is_mirrored({"ctm": ctm}) is False


def test_obj_is_skewed_pure_rotation_is_not_skewed():
    """b == -c → pure rotation → not skewed."""
    angle = math.radians(45)
    ctm = [math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0, 0]
    assert geometry.obj_is_skewed({"ctm": ctm}) is False


def test_obj_is_skewed_identity_not_skewed():
    assert geometry.obj_is_skewed({"ctm": [1, 0, 0, 1, 0, 0]}) is False


def test_obj_is_skewed_horizontal_skew():
    # Skew along X: b = 0, c = 0.3
    assert geometry.obj_is_skewed({"ctm": [1, 0, 0.3, 1, 0, 0]}) is True


def test_obj_is_skewed_no_ctm():
    assert geometry.obj_is_skewed({}) is False
