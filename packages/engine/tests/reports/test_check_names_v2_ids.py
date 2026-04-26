"""Tests for the v2_ids field on CheckInfo (Path A — Wave A registration)."""

from __future__ import annotations

from lintpdf.reports.check_names import CHECK_NAMES, CheckInfo, get_check_info


def test_check_info_v2_ids_default_empty():
    info = CheckInfo(name="x", description="y")
    assert info.v2_ids == ()


def test_check_info_accepts_v2_ids():
    info = CheckInfo(name="x", description="y", v2_ids=("D-08", "D-09"))
    assert info.v2_ids == ("D-08", "D-09")


def test_zorder_maps_to_d06():
    assert "D-06" in CHECK_NAMES["LPDF_DIE_ZORDER"].v2_ids


def test_knockout_maps_to_d07():
    assert CHECK_NAMES["LPDF_DIE_KNOCKOUT"].v2_ids == ("D-07",)


def test_layer_content_maps_to_d04():
    assert CHECK_NAMES["LPDF_DIE_LAYER_CONTENT"].v2_ids == ("D-04",)


def test_content_outside_maps_to_d15():
    assert "D-15" in CHECK_NAMES["LPDF_DIE_CONTENT_OUTSIDE"].v2_ids


def test_get_check_info_fallback_has_empty_v2_ids():
    info = get_check_info("LPDF_NEVER_HEARD_OF")
    assert info.v2_ids == ()


def test_existing_unmapped_checks_have_empty_v2_ids():
    # Most LPDF_FONT_* and LPDF_IMG_* etc. should default to empty;
    # this protects against accidental v2_id misassignment.
    info = CHECK_NAMES.get("LPDF_DIE_MISSING")
    assert info is not None
    assert info.v2_ids == ()


def test_v2_id_format_is_dash_uppercase_digits():
    """All registered v2 IDs should follow the spec format ``X-NN`` or ``XX-NN``."""
    import re

    pattern = re.compile(r"^[A-Z]{1,4}-\d{1,3}[a-z]?$")
    for code, info in CHECK_NAMES.items():
        for vid in info.v2_ids:
            assert pattern.match(vid), f"{code}: invalid v2_id {vid!r}"
