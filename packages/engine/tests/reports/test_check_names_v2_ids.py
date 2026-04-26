"""Tests for the v2_ids field on CheckInfo (Path A — Wave A registration)."""

from __future__ import annotations

from lintpdf.reports.check_names import CHECK_NAMES, CheckInfo, get_check_info


def test_check_info_v2_ids_default_empty():
    info = CheckInfo(name="x", description="y")
    assert info.v2_ids == ()


def test_check_info_accepts_v2_ids():
    info = CheckInfo(name="x", description="y", v2_ids=("D-08", "D-09"))
    assert info.v2_ids == ("D-08", "D-09")


def test_ai_die_detected_maps_to_d01():
    assert CHECK_NAMES["AI_DIE_001"].v2_ids == ("D-01",)


def test_zorder_maps_to_d06():
    assert "D-06" in CHECK_NAMES["LPDF_DIE_ZORDER"].v2_ids


def test_knockout_maps_to_d07():
    assert CHECK_NAMES["LPDF_DIE_KNOCKOUT"].v2_ids == ("D-07",)


def test_layer_content_maps_to_d04():
    assert CHECK_NAMES["LPDF_DIE_LAYER_CONTENT"].v2_ids == ("D-04",)


def test_content_outside_maps_to_d15():
    assert "D-15" in CHECK_NAMES["LPDF_DIE_CONTENT_OUTSIDE"].v2_ids


def test_epm_002_maps_to_a4():
    """EPM-A4: Small black text / thin black lines below threshold (Phase 2.EPM)."""
    assert "EPM-A4" in CHECK_NAMES["LPDF_EPM_002"].v2_ids


def test_epm_004_maps_to_a5():
    """EPM-A5: Maximum ink coverage exceeds EPM TAC (Phase 2.EPM)."""
    assert CHECK_NAMES["LPDF_EPM_004"].v2_ids == ("EPM-A5",)


def test_epm_007_maps_to_b2():
    """EPM-B2: Registration color in artwork (Phase 2.EPM)."""
    assert CHECK_NAMES["LPDF_EPM_007"].v2_ids == ("EPM-B2",)


def test_epm_008_maps_to_a7_and_c4():
    """EPM-A7: Neutral gray deviation; EPM-C4: Neutral gray fills (Phase 2.EPM).

    LPDF_EPM_008 fires when CMY components are near-equal with K=0; this
    covers both the strong A7 signal (high-saturation neutrals likely to
    drift) and the soft C4 signal (any near-equal CMY mix).
    """
    assert CHECK_NAMES["LPDF_EPM_008"].v2_ids == ("EPM-A7", "EPM-C4")


def test_epm_009_maps_to_a5():
    """EPM-A5 (total-toner sense): Maximum ink coverage exceeds EPM device limit."""
    assert CHECK_NAMES["LPDF_EPM_009"].v2_ids == ("EPM-A5",)


def test_epm_014_maps_to_c8():
    """EPM-C8: Output Intent mismatched to press ICC (Phase 2.EPM soft signal)."""
    assert CHECK_NAMES["LPDF_EPM_014"].v2_ids == ("EPM-C8",)


def test_epm_018_maps_to_a4():
    """EPM-A4 (thin-line sense): stroked paths below digital-press minimum."""
    assert CHECK_NAMES["LPDF_EPM_018"].v2_ids == ("EPM-A4",)


def test_box_001_maps_to_p03_and_p04():
    """LPDF_BOX_001 covers both TrimBox missing (P-03) and BleedBox missing (P-04).

    The analyzer (lintpdf/analyzers/page_geometry.py) emits one finding per
    missing box, discriminated by ``details["missing_box"]``. The CheckInfo
    code is shared because the underlying defect class is identical.
    """
    assert CHECK_NAMES["LPDF_BOX_001"].v2_ids == ("P-03", "P-04")


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
    """All registered v2 IDs should follow the spec format ``X-NN``, ``XX-NN``,
    or the EPM compound form ``EPM-A1`` / ``EPM-B6`` / ``EPM-C8`` per playbook §10.
    """
    import re

    pattern = re.compile(r"^[A-Z]{1,4}-(?:[A-Z]?\d{1,3})[a-z]?$")
    for code, info in CHECK_NAMES.items():
        for vid in info.v2_ids:
            assert pattern.match(vid), f"{code}: invalid v2_id {vid!r}"
