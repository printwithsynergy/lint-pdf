"""Tests for color-space primitives (Tier-0 Batch 02)."""

from __future__ import annotations

import pytest

from siftpdf.primitives import REGISTRY, color_space

# ---- registry --------------------------------------------------------------


def test_registry_contains_all_seventeen_primitives():
    """All 13 type predicates + 4 helpers registered under 'color_space'."""
    expected = {
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
    }
    assert REGISTRY.get("color_space", {}).keys() == expected


# ---- name normalization ---------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("DeviceRGB", True),
        ("/DeviceRGB", True),
        (b"/DeviceRGB", True),
        (b"DeviceRGB", True),
        ("/DeviceCMYK", False),
        (None, False),
        ("", False),
    ],
)
def test_is_DeviceRGB_handles_name_variants(value, expected):
    assert color_space.is_DeviceRGB(value) is expected


# ---- Device* type predicates ----------------------------------------------


@pytest.mark.parametrize(
    ("predicate", "matching_name"),
    [
        (color_space.is_DeviceCMYK, "DeviceCMYK"),
        (color_space.is_DeviceRGB, "DeviceRGB"),
        (color_space.is_DeviceGray, "DeviceGray"),
    ],
)
def test_device_predicates_match_corresponding_name(predicate, matching_name):
    assert predicate(matching_name) is True
    assert predicate(f"/{matching_name}") is True
    # Cross-check: Device* predicates don't match other Device* names
    for other in ("DeviceCMYK", "DeviceRGB", "DeviceGray"):
        if other != matching_name:
            assert predicate(other) is False
    # And don't match arrays
    assert predicate(["ICCBased", {}]) is False


# ---- CIE-based + ICCBased -------------------------------------------------


def test_is_CalRGB_array():
    assert color_space.is_CalRGB(["CalRGB", {"WhitePoint": [0.95, 1.0, 1.09]}]) is True
    assert color_space.is_CalRGB(["/CalRGB", {}]) is True
    assert color_space.is_CalRGB("CalRGB") is False  # name only is incomplete


def test_is_CalGray_array():
    assert color_space.is_CalGray(["CalGray", {}]) is True
    assert color_space.is_CalGray(["CalRGB", {}]) is False


def test_is_Lab_array():
    assert color_space.is_Lab(["Lab", {"WhitePoint": [0.95, 1.0, 1.09]}]) is True
    assert color_space.is_Lab(["DeviceN", []]) is False


def test_is_ICCBased_array():
    assert color_space.is_ICCBased(["ICCBased", {"N": 4}]) is True
    assert color_space.is_ICCBased(["/ICCBased", {}]) is True
    assert color_space.is_ICCBased("DeviceCMYK") is False


def test_is_ICCBased_false_for_indexed_with_iccbased_base():
    """Phase 2 Q1 decision: type is Indexed regardless of base."""
    indexed = ["Indexed", ["ICCBased", {"N": 4}], 255, b""]
    assert color_space.is_Indexed(indexed) is True
    assert color_space.is_ICCBased(indexed) is False


# ---- Separation / DeviceN / NChannel --------------------------------------


def test_is_Separation_array():
    sep = ["Separation", "PANTONE 185 C", "DeviceCMYK", {"FunctionType": 2}]
    assert color_space.is_Separation(sep) is True


def test_is_DeviceN_array():
    devn = ["DeviceN", ["C", "M", "Y", "K"], "DeviceCMYK", {"FunctionType": 2}]
    assert color_space.is_DeviceN(devn) is True


def test_is_NChannel_requires_subtype_attrs():
    """NChannel = DeviceN with attributes Subtype = NChannel."""
    plain_devn = ["DeviceN", ["C", "M"], "DeviceCMYK", {"FunctionType": 2}]
    assert color_space.is_DeviceN(plain_devn) is True
    assert color_space.is_NChannel(plain_devn) is False
    n_channel = [
        "DeviceN",
        ["C", "M", "Y", "K", "Spot1"],
        "DeviceCMYK",
        {"FunctionType": 2},
        {"Subtype": "NChannel"},
    ]
    assert color_space.is_DeviceN(n_channel) is True
    assert color_space.is_NChannel(n_channel) is True


def test_is_NChannel_false_for_non_DeviceN():
    assert color_space.is_NChannel(["Separation", "spot", "DeviceCMYK", {}]) is False


# ---- Indexed / Pattern / Shading ------------------------------------------


def test_is_Indexed():
    assert color_space.is_Indexed(["Indexed", "DeviceRGB", 255, b"\x00" * 768]) is True


def test_is_Pattern_name_or_array():
    assert color_space.is_Pattern("Pattern") is True
    assert color_space.is_Pattern("/Pattern") is True
    assert color_space.is_Pattern(["Pattern", "DeviceRGB"]) is True
    assert color_space.is_Pattern("DeviceRGB") is False


def test_is_Shading_dict():
    shading = {"ShadingType": 2, "ColorSpace": "DeviceRGB"}
    assert color_space.is_Shading(shading) is True
    assert color_space.is_Shading({"ShadingType": 5}) is True
    assert color_space.is_Shading({}) is False
    assert color_space.is_Shading("DeviceRGB") is False


# ---- alternate_space ------------------------------------------------------


def test_alternate_space_separation():
    sep = ["Separation", "PANTONE 185 C", "DeviceCMYK", {"FunctionType": 2}]
    assert color_space.alternate_space(sep) == "DeviceCMYK"


def test_alternate_space_devicen():
    devn = ["DeviceN", ["C", "M"], ["ICCBased", {"N": 4}], {"FunctionType": 2}]
    assert color_space.alternate_space(devn) == ["ICCBased", {"N": 4}]


def test_alternate_space_indexed():
    indexed = ["Indexed", ["ICCBased", {"N": 4}], 255, b""]
    assert color_space.alternate_space(indexed) == ["ICCBased", {"N": 4}]


def test_alternate_space_iccbased():
    icc = ["ICCBased", {"N": 4, "Alternate": "DeviceCMYK"}]
    assert color_space.alternate_space(icc) == "DeviceCMYK"


def test_alternate_space_returns_none_for_device_or_cal():
    assert color_space.alternate_space("DeviceRGB") is None
    assert color_space.alternate_space(["CalGray", {}]) is None
    assert color_space.alternate_space(["Lab", {}]) is None


# ---- tint_transform_is_zero ----------------------------------------------


def test_tint_transform_is_zero_type2_zero_C0_C1():
    sep_zero = [
        "Separation",
        "Spot",
        "DeviceCMYK",
        {"FunctionType": 2, "C0": [0, 0, 0, 0], "C1": [0, 0, 0, 0], "N": 1},
    ]
    assert color_space.tint_transform_is_zero(sep_zero) is True


def test_tint_transform_is_zero_type2_nonzero():
    sep_nonzero = [
        "Separation",
        "Spot",
        "DeviceCMYK",
        {"FunctionType": 2, "C0": [0, 0, 0, 0], "C1": [0, 0, 0, 1], "N": 1},
    ]
    assert color_space.tint_transform_is_zero(sep_nonzero) is False


def test_tint_transform_is_zero_type0_all_zero_samples():
    sep = [
        "Separation",
        "Spot",
        "DeviceCMYK",
        {"FunctionType": 0, "_Samples": b"\x00\x00\x00\x00"},
    ]
    assert color_space.tint_transform_is_zero(sep) is True


def test_tint_transform_is_zero_type0_some_nonzero():
    sep = [
        "Separation",
        "Spot",
        "DeviceCMYK",
        {"FunctionType": 0, "_Samples": b"\x00\xff\x00\x00"},
    ]
    assert color_space.tint_transform_is_zero(sep) is False


def test_tint_transform_is_zero_type3_recurse():
    inner_zero = {"FunctionType": 2, "C0": [0], "C1": [0], "N": 1}
    sep = [
        "Separation",
        "Spot",
        "DeviceGray",
        {"FunctionType": 3, "Functions": [inner_zero, inner_zero]},
    ]
    assert color_space.tint_transform_is_zero(sep) is True


def test_tint_transform_is_zero_type3_one_nonzero_subfunction():
    zero_fn = {"FunctionType": 2, "C0": [0], "C1": [0], "N": 1}
    one_fn = {"FunctionType": 2, "C0": [0], "C1": [1], "N": 1}
    sep = [
        "Separation",
        "Spot",
        "DeviceGray",
        {"FunctionType": 3, "Functions": [zero_fn, one_fn]},
    ]
    assert color_space.tint_transform_is_zero(sep) is False


def test_tint_transform_is_zero_type4_constant_zero():
    sep = [
        "Separation",
        "Spot",
        "DeviceGray",
        {"FunctionType": 4, "_Program": "{ pop 0 }"},
    ]
    assert color_space.tint_transform_is_zero(sep) is True


def test_tint_transform_is_zero_type4_passthrough_not_zero():
    sep = [
        "Separation",
        "Spot",
        "DeviceGray",
        {"FunctionType": 4, "_Program": "{ }"},
    ]
    assert color_space.tint_transform_is_zero(sep) is False


def test_tint_transform_is_zero_false_for_devicergb_name():
    assert color_space.tint_transform_is_zero("DeviceRGB") is False


# ---- icc_profile_version + icc_profile_class -----------------------------


def _icc_header(version: int, dev_class: str) -> bytes:
    """Build a 128-byte ICC header with version + class set; rest zeros."""
    header = bytearray(128)
    header[8] = (version & 0xF) << 4
    header[12:16] = dev_class.encode("ascii")
    return bytes(header)


def test_icc_profile_version_detects_v2():
    cs = ["ICCBased", {"N": 4, "_StreamData": _icc_header(2, "prtr")}]
    assert color_space.icc_profile_version(cs) == "v2"


def test_icc_profile_version_detects_v4():
    cs = ["ICCBased", {"N": 4, "_StreamData": _icc_header(4, "prtr")}]
    assert color_space.icc_profile_version(cs) == "v4"


def test_icc_profile_version_returns_none_for_non_iccbased():
    assert color_space.icc_profile_version("DeviceCMYK") is None
    assert color_space.icc_profile_version(["DeviceN", []]) is None


def test_icc_profile_version_returns_none_when_bytes_missing():
    cs = ["ICCBased", {"N": 4}]
    assert color_space.icc_profile_version(cs) is None


def test_icc_profile_class_output():
    cs = ["ICCBased", {"N": 4, "_StreamData": _icc_header(4, "prtr")}]
    assert color_space.icc_profile_class(cs) == "output"


def test_icc_profile_class_display():
    cs = ["ICCBased", {"N": 3, "_StreamData": _icc_header(2, "mntr")}]
    assert color_space.icc_profile_class(cs) == "display"


def test_icc_profile_class_input():
    cs = ["ICCBased", {"N": 3, "_StreamData": _icc_header(4, "scnr")}]
    assert color_space.icc_profile_class(cs) == "input"


def test_icc_profile_class_unknown_returns_none():
    cs = ["ICCBased", {"N": 4, "_StreamData": _icc_header(4, "xxxx")}]
    assert color_space.icc_profile_class(cs) is None


# ---- edge cases (per design.md) ------------------------------------------


def test_pattern_name_distinct_from_pattern_array():
    assert color_space.is_Pattern("Pattern") is True
    assert color_space.is_Pattern(["Pattern", "DeviceRGB"]) is True


def test_devicen_with_empty_attributes_is_not_nchannel():
    devn = ["DeviceN", ["C"], "DeviceCMYK", {"FunctionType": 2}, {}]
    assert color_space.is_NChannel(devn) is False


def test_malformed_arrays_dont_raise():
    """Malformed inputs should return False, not raise."""
    assert color_space.is_DeviceCMYK([]) is False
    assert color_space.is_DeviceN(None) is False
    assert color_space.is_Indexed({}) is False
    assert color_space.alternate_space([]) is None
    assert color_space.tint_transform_is_zero([]) is False


def test_string_bytes_pikepdf_name_coercion():
    """Bytes / pikepdf-Name-like inputs all normalize."""

    # Mock a pikepdf.Name-style object that coerces via str()
    class _NameLike:
        def __str__(self):
            return "/DeviceCMYK"

    assert color_space.is_DeviceCMYK(_NameLike()) is True
