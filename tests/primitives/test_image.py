"""Tests for image primitives (Tier-0 Batch 08)."""

from __future__ import annotations

from lintpdf.primitives import REGISTRY
from lintpdf.primitives import image as image_p


def test_registry_contains_fourteen_primitives():
    expected = {
        "color_space",
        "bit_depth",
        "filter_name",
        "has_jpeg",
        "has_jpeg2000",
        "has_jbig2",
        "dpi_native",
        "dpi_effective",
        "has_icc_profile",
        "icc_matches_oi",
        "has_alpha",
        "has_smask",
        "is_inline",
        "is_linked_opi",
    }
    assert REGISTRY.get("image", {}).keys() == expected


# ---- color_space + bit_depth -----------------------------------------


def test_color_space_from_name():
    assert image_p.color_space({"ColorSpace": "DeviceRGB"}) == "DeviceRGB"
    assert image_p.color_space({"ColorSpace": "/DeviceCMYK"}) == "DeviceCMYK"


def test_color_space_from_array():
    assert image_p.color_space({"ColorSpace": ["ICCBased", {}]}) == "ICCBased"


def test_color_space_returns_none_when_absent():
    assert image_p.color_space({}) is None
    assert image_p.color_space(None) is None


def test_bit_depth_default_eight():
    assert image_p.bit_depth({}) == 8
    assert image_p.bit_depth(None) == 8


def test_bit_depth_from_bpc():
    assert image_p.bit_depth({"BitsPerComponent": 16}) == 16
    assert image_p.bit_depth({"BPC": 1}) == 1


# ---- filter / has_jpeg* / has_jbig2 ---------------------------------


def test_filter_name_single():
    assert image_p.filter_name({"Filter": "DCTDecode"}) == "DCTDecode"
    assert image_p.filter_name({"Filter": "/FlateDecode"}) == "FlateDecode"


def test_filter_name_chain():
    assert image_p.filter_name({"Filter": ["FlateDecode", "DCTDecode"]}) == [
        "FlateDecode",
        "DCTDecode",
    ]


def test_has_jpeg_via_dctdecode():
    assert image_p.has_jpeg({"Filter": "DCTDecode"}) is True
    assert image_p.has_jpeg({"Filter": ["FlateDecode", "DCTDecode"]}) is True
    assert image_p.has_jpeg({"Filter": "FlateDecode"}) is False


def test_has_jpeg2000_via_jpxdecode():
    assert image_p.has_jpeg2000({"Filter": "JPXDecode"}) is True
    assert image_p.has_jpeg2000({"Filter": ["JPXDecode"]}) is True
    assert image_p.has_jpeg2000({"Filter": "DCTDecode"}) is False


def test_has_jbig2_via_jbig2decode():
    assert image_p.has_jbig2({"Filter": "JBIG2Decode"}) is True
    assert image_p.has_jbig2({"Filter": "DCTDecode"}) is False


# ---- dpi_native + dpi_effective -------------------------------------


def test_dpi_native_returns_none_without_rendered_size():
    assert image_p.dpi_native({"Width": 1000, "Height": 1000}) is None


def test_dpi_native_computed_from_rendered_size_pt():
    # 1000px wide, rendered at 72pt → 1000/(72/72) = 1000 dpi
    img = {"Width": 1000, "Height": 500, "rendered_size_pt": (72.0, 36.0)}
    dpi_x, dpi_y = image_p.dpi_native(img)
    assert dpi_x == 1000.0
    assert dpi_y == 1000.0


def test_dpi_effective_with_unit_ctm_returns_image_size():
    """1000px image scaled to 1 user-unit (default) = 1000 px / (1 / 72 in) = 72000 dpi.

    With CTM = identity (1,0,0,1), sx = sy = 1.0 → dpi = px / (1/72) = px * 72.
    """
    img = {"Width": 100, "Height": 100}
    ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    dpi_x, dpi_y = image_p.dpi_effective(img, ctm)
    assert dpi_x == 7200.0  # 100 / 1 * 72
    assert dpi_y == 7200.0


def test_dpi_effective_at_smaller_render_size():
    """Image scaled larger → lower DPI."""
    img = {"Width": 100, "Height": 100}
    ctm = (10.0, 0.0, 0.0, 10.0, 0.0, 0.0)  # 10x scale = 10pt rendered
    dpi_x, dpi_y = image_p.dpi_effective(img, ctm)
    assert dpi_x == 720.0  # 100 / 10 * 72
    assert dpi_y == 720.0


def test_dpi_effective_falls_back_to_native_without_ctm():
    img = {"Width": 100, "Height": 100, "rendered_size_pt": (72.0, 72.0)}
    assert image_p.dpi_effective(img) == image_p.dpi_native(img)


# ---- ICC + alpha / smask ---------------------------------------------


def test_has_icc_profile_via_iccbased_array():
    assert image_p.has_icc_profile({"ColorSpace": ["ICCBased", {}]}) is True


def test_has_icc_profile_false_for_devicergb():
    assert image_p.has_icc_profile({"ColorSpace": "DeviceRGB"}) is False


def test_has_icc_profile_via_explicit_flag():
    assert image_p.has_icc_profile({"has_icc_profile": True}) is True


def test_icc_matches_oi_when_names_equal():
    img = {"ColorSpace": ["ICCBased", {"Name": "GRACoL2006"}]}
    oi = {"Name": "GRACoL2006"}
    assert image_p.icc_matches_oi(img, oi) is True


def test_icc_matches_oi_false_when_names_differ():
    img = {"ColorSpace": ["ICCBased", {"Name": "GRACoL2006"}]}
    oi = {"Name": "ISOcoated_v2_300"}
    assert image_p.icc_matches_oi(img, oi) is False


def test_icc_matches_oi_false_when_image_no_icc():
    img = {"ColorSpace": "DeviceRGB"}
    oi = {"Name": "GRACoL2006"}
    assert image_p.icc_matches_oi(img, oi) is False


def test_has_alpha():
    assert image_p.has_alpha({"has_alpha": True}) is True
    assert image_p.has_alpha({"alpha": True}) is True
    assert image_p.has_alpha({}) is False


def test_has_smask_with_dict():
    assert image_p.has_smask({"SMask": {"S": "Alpha"}}) is True
    assert image_p.has_smask({"smask": {"S": "Luminosity"}}) is True


def test_has_smask_false_when_none_name():
    assert image_p.has_smask({"SMask": "/None"}) is False
    assert image_p.has_smask({}) is False


# ---- inline / opi ----------------------------------------------------


def test_is_inline():
    assert image_p.is_inline({"is_inline": True}) is True
    assert image_p.is_inline({"inline": True}) is True
    assert image_p.is_inline({}) is False


def test_is_linked_opi_true_when_opi_present():
    assert image_p.is_linked_opi({"OPI": {"version": 2.0}}) is True
    assert image_p.is_linked_opi({"opi": {"version": 1.3}}) is True


def test_is_linked_opi_false_when_absent():
    assert image_p.is_linked_opi({}) is False
