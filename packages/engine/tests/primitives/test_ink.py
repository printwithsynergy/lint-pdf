"""Tests for ink primitives (Tier-0 Batch 03)."""

from __future__ import annotations

import pytest

from lintpdf.primitives import REGISTRY, ink

# ---- registry --------------------------------------------------------------


def test_registry_contains_all_eleven_primitives():
    expected = {
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
    }
    assert REGISTRY.get("ink", {}).keys() == expected


# ---- name -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("PANTONE 185 C", "PANTONE 185 C"),
        ("/PANTONE 185 C", "PANTONE 185 C"),
        (b"/PANTONE 185 C", "PANTONE 185 C"),
        (["Separation", "PANTONE 185 C", "DeviceCMYK", {}], "PANTONE 185 C"),
        (["Separation", "/CutContour", "DeviceCMYK", {}], "CutContour"),
        (None, None),
        ("", None),
    ],
)
def test_name_extracts_spot_label(input_value, expected):
    assert ink.name(input_value) == expected


def test_name_devicen_joins_components():
    devn = ["DeviceN", ["Cyan", "Magenta", "Spot1"], "DeviceCMYK", {}]
    assert ink.name(devn) == "Cyan+Magenta+Spot1"


# ---- is_process / is_spot / is_reserved_name -----------------------------


@pytest.mark.parametrize(
    "name", ["Cyan", "Magenta", "Yellow", "Black", "Gray", "DeviceCMYK"]
)
def test_is_process_true_for_process_names(name):
    assert ink.is_process(name) is True


def test_is_process_true_for_black_separation_per_phase2_decision():
    assert ink.is_process(["Separation", "Black", "DeviceCMYK", {}]) is True


def test_is_process_false_for_pantone():
    assert ink.is_process("PANTONE 185 C") is False
    assert ink.is_process(["Separation", "PANTONE 185 C", "DeviceCMYK", {}]) is False


def test_is_process_devicen_cmyk_components():
    devn = ["DeviceN", ["Cyan", "Magenta", "Yellow", "Black"], "DeviceCMYK", {}]
    assert ink.is_process(devn) is True


def test_is_process_devicen_with_spot_component_is_not_process():
    devn = ["DeviceN", ["Cyan", "Magenta", "Pantone185"], "DeviceCMYK", {}]
    assert ink.is_process(devn) is False


def test_is_spot_true_for_pantone():
    assert ink.is_spot("PANTONE 185 C") is True
    assert ink.is_spot(["Separation", "PANTONE 185 C", "DeviceCMYK", {}]) is True


def test_is_spot_false_for_process_or_reserved():
    assert ink.is_spot("Cyan") is False
    assert ink.is_spot("All") is False
    assert ink.is_spot("Registration") is False


@pytest.mark.parametrize(
    "name", ["Cyan", "Magenta", "Yellow", "Black", "All", "None", "Registration"]
)
def test_is_reserved_name_seven_reserved(name):
    assert ink.is_reserved_name(name) is True


def test_is_reserved_name_false_for_arbitrary_spot():
    assert ink.is_reserved_name("PANTONE 185 C") is False
    assert ink.is_reserved_name("CutContour") is False


# ---- library matching -----------------------------------------------------


@pytest.mark.parametrize(
    ("name", "library", "expected"),
    [
        ("PANTONE 185 C", "pantone", True),
        ("PANTONE 185 U", "pantone", True),
        ("PANTONE 4865 CP", "pantone", True),
        ("Pantone 185 C", "pantone", True),  # case insensitive
        ("PANTONE Reflex Blue C", "pantone", True),
        ("PANTONE Process Yellow C", "pantone", True),
        ("PANTONE 185", "pantone", False),  # missing finishing code
        ("PMS 185 C", "pantone", False),  # PMS != PANTONE
        ("HKS 13 K", "hks", True),
        ("HKS 7 N", "hks", True),
        ("hks 13 k", "hks", True),
        ("HKS 13", "hks", True),  # finishing optional
        ("RAL 1234", "ral", True),
        ("RAL 12345", "ral", False),  # too many digits
        ("TOYO 185", "toyo", True),
        ("TOYO 0185", "toyo", True),
        ("DIC 185", "dic", True),
        ("DIC 185s", "dic", True),
        ("ANPA 25", "anpa", True),
        ("ANPA 5", "anpa", True),
    ],
)
def test_matches_library(name, library, expected):
    assert ink.matches_library(name, library) is expected


def test_matches_library_unknown_returns_false():
    assert ink.matches_library("PANTONE 185 C", "ferrari-red") is False


def test_matches_library_custom_regex():
    assert ink.matches_library(
        "INHOUSE-2025-NAVY",
        "custom",
        custom_pattern=r"^INHOUSE-\d{4}-[A-Z]+$",
    )
    assert (
        ink.matches_library(
            "PANTONE 185 C", "custom", custom_pattern=r"^INHOUSE-\d{4}-[A-Z]+$"
        )
        is False
    )


def test_matches_library_custom_without_pattern_returns_false():
    assert ink.matches_library("INHOUSE", "custom") is False


def test_matches_library_invalid_custom_regex_returns_false():
    assert ink.matches_library("X", "custom", custom_pattern=r"[invalid(") is False


# ---- ISO 19593-1 processing steps ----------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("CutContour", True),
        ("DieLine", True),
        ("Cut", True),
        ("Crease", True),
        ("Perforation", True),
        ("Perf", True),
        ("White", True),
        ("Varnish", True),
        ("Registration", True),
        ("Trim Mark", True),
        ("Color Bar", True),
        ("PANTONE 185 C", False),
        ("Cyan", False),
        ("RandomSpotName", False),
    ],
)
def test_is_processing_step(name, expected):
    assert ink.is_processing_step(name) is expected


@pytest.mark.parametrize(
    ("name", "expected_group"),
    [
        ("CutContour", "Structural"),
        ("Crease", "Structural"),
        ("Perforation", "Structural"),
        ("White", "White"),
        ("Varnish", "Varnish"),
        ("Registration", "Positions"),
        ("Trim Mark", "Positions"),
        ("PANTONE 185 C", None),
    ],
)
def test_processing_step_group_titlecase(name, expected_group):
    """Phase 2 Batch 3 Q3: Title-Case ISO 19593-1 group names."""
    assert ink.processing_step_group(name) == expected_group


@pytest.mark.parametrize(
    ("name", "expected_type"),
    [
        ("CutContour", "Cutting"),
        ("KissCut", "KissCutting"),
        ("Crease", "Folding"),
        ("Perforation", "Perforating"),
        ("White", "White"),
        ("Varnish", "Varnish"),
        ("Registration", "Positions"),
    ],
)
def test_processing_step_type(name, expected_type):
    assert ink.processing_step_type(name) == expected_type


# ---- Lab / alt-CMYK extraction -------------------------------------------


def test_lab_value_extracts_c1_tuple():
    sep = [
        "Separation",
        "PANTONE 185 C",
        ["Lab", {}],
        {"FunctionType": 2, "C0": [0, 0, 0], "C1": [55.0, 12.5, -8.3], "N": 1},
    ]
    assert ink.lab_value(sep) == (55.0, 12.5, -8.3)


def test_lab_value_returns_none_for_non_lab_alt():
    sep_cmyk = [
        "Separation",
        "X",
        "DeviceCMYK",
        {"FunctionType": 2, "C0": [0, 0, 0, 0], "C1": [0.5, 0.3, 0.2, 0.8]},
    ]
    assert ink.lab_value(sep_cmyk) is None


def test_alt_cmyk_extracts_c1_tuple():
    sep = [
        "Separation",
        "X",
        "DeviceCMYK",
        {"FunctionType": 2, "C0": [0, 0, 0, 0], "C1": [0.5, 0.3, 0.2, 0.8]},
    ]
    assert ink.alt_cmyk(sep) == (0.5, 0.3, 0.2, 0.8)


def test_alt_cmyk_returns_none_for_lab_alt():
    sep_lab = [
        "Separation",
        "X",
        ["Lab", {}],
        {"FunctionType": 2, "C0": [0, 0, 0], "C1": [55.0, 12.5, -8.3]},
    ]
    assert ink.alt_cmyk(sep_lab) is None


def test_alt_lab_alias_of_lab_value():
    sep = [
        "Separation",
        "X",
        ["Lab", {}],
        {"FunctionType": 2, "C0": [0, 0, 0], "C1": [55.0, 12.5, -8.3], "N": 1},
    ]
    assert ink.alt_lab(sep) == ink.lab_value(sep)


def test_extraction_returns_none_for_non_separation():
    assert ink.lab_value("DeviceRGB") is None
    assert ink.alt_cmyk(["DeviceRGB"]) is None


def test_extraction_returns_none_for_short_c1():
    sep_short = [
        "Separation",
        "X",
        "DeviceCMYK",
        {"FunctionType": 2, "C0": [0, 0, 0, 0], "C1": [0.5, 0.3]},  # only 2-tuple
    ]
    assert ink.alt_cmyk(sep_short) is None
