"""Tests for transparency-stack primitives (Tier-0 Batch 06)."""

from __future__ import annotations

from siftpdf.primitives import REGISTRY
from siftpdf.primitives import transparency_stack as ts


def test_registry_contains_nine_primitives():
    expected = {
        "in_isolated_group",
        "in_knockout_group",
        "has_smask",
        "smask_is_alpha",
        "smask_is_luminosity",
        "page_transparency_group_present",
        "page_blending_color_space",
        "extgstate_alpha",
        "extgstate_blend_mode",
    }
    assert REGISTRY.get("transparency_stack", {}).keys() == expected


# ---- in_isolated_group / in_knockout_group ----------------------------


def test_in_isolated_group_via_transparency_group_dict():
    state = {"transparency_group": {"I": True}}
    assert ts.in_isolated_group(state) is True


def test_in_isolated_group_via_long_key():
    state = {"transparency_group": {"Isolated": True}}
    assert ts.in_isolated_group(state) is True


def test_in_isolated_group_false_when_no_group():
    assert ts.in_isolated_group(None) is False
    assert ts.in_isolated_group({}) is False
    assert ts.in_isolated_group({"transparency_group": {}}) is False


def test_in_knockout_group_via_short_key():
    state = {"transparency_group": {"K": True}}
    assert ts.in_knockout_group(state) is True


def test_in_knockout_group_independent_of_isolated():
    state = {"transparency_group": {"I": True, "K": False}}
    assert ts.in_isolated_group(state) is True
    assert ts.in_knockout_group(state) is False


# ---- has_smask -------------------------------------------------------


def test_has_smask_true_when_smask_set():
    assert ts.has_smask({"smask": {"S": "Alpha"}}) is True
    assert ts.has_smask({"SMask": {"Subtype": "Luminosity"}}) is True


def test_has_smask_false_when_smask_is_none_name():
    assert ts.has_smask({"smask": "/None"}) is False
    assert ts.has_smask({"smask": "None"}) is False
    assert ts.has_smask({}) is False
    assert ts.has_smask(None) is False


# ---- smask_is_alpha / smask_is_luminosity ----------------------------


def test_smask_is_alpha():
    assert ts.smask_is_alpha({"S": "Alpha"}) is True
    assert ts.smask_is_alpha({"S": "/Alpha"}) is True
    assert ts.smask_is_alpha({"Subtype": "Alpha"}) is True
    assert ts.smask_is_alpha({"S": "Luminosity"}) is False


def test_smask_is_luminosity():
    assert ts.smask_is_luminosity({"S": "Luminosity"}) is True
    assert ts.smask_is_luminosity({"S": "/Luminosity"}) is True
    assert ts.smask_is_luminosity({"S": "Alpha"}) is False


def test_smask_is_alpha_false_for_non_dict():
    assert ts.smask_is_alpha("Alpha") is False
    assert ts.smask_is_alpha(None) is False


# ---- page transparency group ----------------------------------------


def test_page_transparency_group_present_via_page_dict():
    page = type("MockPage", (), {"page_dict": {"Group": {"S": "Transparency"}}})()
    assert ts.page_transparency_group_present(page) is True


def test_page_transparency_group_present_via_attribute():
    page = type("MockPage", (), {"group": {"S": "Transparency"}})()
    assert ts.page_transparency_group_present(page) is True


def test_page_transparency_group_present_false_when_absent():
    page = type("MockPage", (), {"page_dict": {}})()
    assert ts.page_transparency_group_present(page) is False


def test_page_blending_color_space_returns_name():
    page = type(
        "MockPage", (), {"page_dict": {"Group": {"S": "Transparency", "CS": "DeviceCMYK"}}}
    )()
    assert ts.page_blending_color_space(page) == "DeviceCMYK"


def test_page_blending_color_space_returns_array_first_element():
    page = type(
        "MockPage",
        (),
        {"page_dict": {"Group": {"S": "Transparency", "CS": ["ICCBased", {}]}}},
    )()
    assert ts.page_blending_color_space(page) == "ICCBased"


def test_page_blending_color_space_returns_none_when_absent():
    page = type("MockPage", (), {"page_dict": {}})()
    assert ts.page_blending_color_space(page) is None


# ---- extgstate alpha + blend mode -----------------------------------


def test_extgstate_alpha_fill_default():
    assert ts.extgstate_alpha({}) == 1.0
    assert ts.extgstate_alpha(None) == 1.0


def test_extgstate_alpha_fill_set():
    assert ts.extgstate_alpha({"ca": 0.5}) == 0.5


def test_extgstate_alpha_stroke_set():
    assert ts.extgstate_alpha({"CA": 0.7}, kind="stroke") == 0.7


def test_extgstate_alpha_independent_kinds():
    eg = {"ca": 0.4, "CA": 0.8}
    assert ts.extgstate_alpha(eg, kind="fill") == 0.4
    assert ts.extgstate_alpha(eg, kind="stroke") == 0.8


def test_extgstate_blend_mode_default_normal():
    assert ts.extgstate_blend_mode({}) == "Normal"
    assert ts.extgstate_blend_mode(None) == "Normal"


def test_extgstate_blend_mode_strips_slash():
    assert ts.extgstate_blend_mode({"BM": "/Multiply"}) == "Multiply"
    assert ts.extgstate_blend_mode({"BM": "Multiply"}) == "Multiply"


def test_extgstate_blend_mode_array_returns_first():
    """PDF allows /BM [ /Multiply /Normal ] — first available wins."""
    assert ts.extgstate_blend_mode({"BM": ["Multiply", "Normal"]}) == "Multiply"
