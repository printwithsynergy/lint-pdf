"""Tests for stroke/fill primitives (Tier-0 Batch 05)."""

from __future__ import annotations

import math

import pytest

from siftpdf.primitives import REGISTRY, stroke_fill


def test_registry_contains_eight_primitives():
    expected = {
        "has_fill",
        "has_stroke",
        "fill_color",
        "stroke_color",
        "width",
        "effective_width",
        "opacity",
        "blend_mode",
    }
    assert REGISTRY.get("stroke_fill", {}).keys() == expected


# ---- has_fill / has_stroke ----------------------------------------------


@pytest.mark.parametrize("op", ["f", "F", "f*", "B", "B*", "b", "b*"])
def test_has_fill_true_for_fill_paint_ops(op):
    assert stroke_fill.has_fill(op) is True


@pytest.mark.parametrize("op", ["S", "s", "n", "Q", "q"])
def test_has_fill_false_for_non_fill_ops(op):
    assert stroke_fill.has_fill(op) is False


@pytest.mark.parametrize("op", ["S", "s", "B", "B*", "b", "b*"])
def test_has_stroke_true_for_stroke_paint_ops(op):
    assert stroke_fill.has_stroke(op) is True


@pytest.mark.parametrize("op", ["f", "F", "f*", "n"])
def test_has_stroke_false_for_fill_only_or_no_op(op):
    assert stroke_fill.has_stroke(op) is False


def test_b_op_paints_both_fill_and_stroke():
    """`B` and `b` paint both fill and stroke."""
    assert stroke_fill.has_fill("B") is True
    assert stroke_fill.has_stroke("B") is True
    assert stroke_fill.has_fill("b") is True
    assert stroke_fill.has_stroke("b") is True


# ---- fill_color / stroke_color -------------------------------------------


def test_fill_color_extracts_from_state():
    state = {"fill_color": (1.0, 0.0, 0.0)}
    assert stroke_fill.fill_color(state) == (1.0, 0.0, 0.0)


def test_fill_color_none_state():
    assert stroke_fill.fill_color(None) is None
    assert stroke_fill.fill_color({}) is None


def test_stroke_color_extracts_from_state():
    state = {"stroke_color": (0.0, 1.0, 0.0)}
    assert stroke_fill.stroke_color(state) == (0.0, 1.0, 0.0)


# ---- width + effective_width --------------------------------------------


def test_width_default_one():
    assert stroke_fill.width(None) == 1.0
    assert stroke_fill.width({}) == 1.0


def test_width_from_state():
    assert stroke_fill.width({"line_width": 0.5}) == 0.5
    assert stroke_fill.width({"line_width": 0}) == 0.0  # zero-width = device-pixel


def test_effective_width_no_ctm_returns_raw_width():
    state = {"line_width": 0.5}
    assert stroke_fill.effective_width(state, None) == 0.5


def test_effective_width_unit_ctm():
    state = {"line_width": 0.5}
    ctm = (1, 0, 0, 1, 0, 0)
    assert stroke_fill.effective_width(state, ctm) == 0.5


def test_effective_width_uniform_2x_scale():
    state = {"line_width": 0.5}
    ctm = (2, 0, 0, 2, 0, 0)
    assert stroke_fill.effective_width(state, ctm) == 1.0


def test_effective_width_uniform_half_scale_creates_hairline():
    state = {"line_width": 0.5}
    ctm = (0.5, 0, 0, 0.5, 0, 0)
    assert stroke_fill.effective_width(state, ctm) == 0.25


def test_effective_width_non_uniform_uses_min_scale():
    """Effective width = line_width x min(sx, sy)."""
    state = {"line_width": 1.0}
    ctm = (3, 0, 0, 0.5, 0, 0)  # sx=3, sy=0.5
    assert stroke_fill.effective_width(state, ctm) == 0.5


def test_effective_width_with_rotation_preserves_scale():
    """Pure rotation has scale 1.0."""
    state = {"line_width": 0.5}
    angle = math.radians(45)
    ctm = (math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0, 0)
    assert stroke_fill.effective_width(state, ctm) == pytest.approx(0.5)


# ---- opacity -----------------------------------------------------------


def test_opacity_defaults_to_one():
    assert stroke_fill.opacity(None) == 1.0
    assert stroke_fill.opacity({}) == 1.0
    assert stroke_fill.opacity({}, kind="stroke") == 1.0


def test_opacity_fill_via_ca():
    assert stroke_fill.opacity({"ca": 0.5}) == 0.5
    assert stroke_fill.opacity({"fill_opacity": 0.3}) == 0.3
    assert stroke_fill.opacity({"fill_alpha": 0.7}) == 0.7


def test_opacity_stroke_via_ca_uppercase():
    assert stroke_fill.opacity({"CA": 0.5}, kind="stroke") == 0.5
    assert stroke_fill.opacity({"stroke_opacity": 0.3}, kind="stroke") == 0.3
    assert stroke_fill.opacity({"stroke_alpha": 0.7}, kind="stroke") == 0.7


def test_opacity_fill_and_stroke_independent():
    state = {"ca": 0.4, "CA": 0.8}
    assert stroke_fill.opacity(state, kind="fill") == 0.4
    assert stroke_fill.opacity(state, kind="stroke") == 0.8


# ---- blend_mode --------------------------------------------------------


def test_blend_mode_default_normal():
    assert stroke_fill.blend_mode(None) == "Normal"
    assert stroke_fill.blend_mode({}) == "Normal"


@pytest.mark.parametrize(
    "stored_value",
    ["Multiply", "/Multiply", b"/Multiply", b"Multiply"],
)
def test_blend_mode_strips_leading_slash(stored_value):
    assert stroke_fill.blend_mode({"BM": stored_value}) == "Multiply"


def test_blend_mode_via_blend_mode_key():
    assert stroke_fill.blend_mode({"blend_mode": "Screen"}) == "Screen"
