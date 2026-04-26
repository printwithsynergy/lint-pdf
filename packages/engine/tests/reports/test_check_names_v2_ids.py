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


def test_img_001_maps_to_i01_and_i02():
    """I-01 (Color image res < min) + I-02 (Grayscale res < min) — both fire from
    LPDF_IMG_001 (low-DPI detector) regardless of color space (Wave D batch 3)."""
    assert CHECK_NAMES["LPDF_IMG_001"].v2_ids == ("I-01", "I-02")


def test_img_002_maps_to_i04():
    """I-04: Color image resolution > max (Wave D batch 3 — corrects Phase 1 audit
    that misnamed this as IMG_003+IMG_004)."""
    assert CHECK_NAMES["LPDF_IMG_002"].v2_ids == ("I-04",)


def test_img_006_maps_to_i21():
    """I-21: Image scale > 100% — upscaling detector (Wave D batch 3 — corrects
    Phase 1 audit that mismapped this to IMG_008)."""
    assert CHECK_NAMES["LPDF_IMG_006"].v2_ids == ("I-21",)


def test_img_008_maps_to_i11():
    """I-11: JPEG2000 detected (Wave D batch 3 — corrects Phase 1 audit)."""
    assert CHECK_NAMES["LPDF_IMG_008"].v2_ids == ("I-11",)


def test_img_010_and_012_both_map_to_i24():
    """I-24: OPI link present — fires both from content-stream (LPDF_IMG_010) and
    page-resource walk (LPDF_IMG_012). Promoted from absent in Wave D batch 3."""
    assert CHECK_NAMES["LPDF_IMG_010"].v2_ids == ("I-24",)
    assert CHECK_NAMES["LPDF_IMG_012"].v2_ids == ("I-24",)


def test_img_014_maps_to_i18():
    """I-18: Image sheared / skewed (Wave D batch 3)."""
    assert CHECK_NAMES["LPDF_IMG_014"].v2_ids == ("I-18",)


def test_img_015_maps_to_i17():
    """I-17: Image rotated non-orthogonally (Wave D batch 3 — corrects Phase 1
    audit that mismapped this to IMG_017)."""
    assert CHECK_NAMES["LPDF_IMG_015"].v2_ids == ("I-17",)


def test_img_016_maps_to_i19():
    """I-19: Image mirrored / flipped (Wave D batch 3 — corrects Phase 1 audit
    that mismapped this to IMG_019)."""
    assert CHECK_NAMES["LPDF_IMG_016"].v2_ids == ("I-19",)


def test_img_017_maps_to_i22():
    """I-22: Image scale < 25% — partial coverage; LPDF_IMG_017 fires at <10% only.
    Promoted from absent in Wave D batch 3."""
    assert CHECK_NAMES["LPDF_IMG_017"].v2_ids == ("I-22",)


def test_font_005_maps_to_f13():
    """F-13: ToUnicode CMap missing (Wave B catch-up; partial — CID-only today)."""
    assert CHECK_NAMES["LPDF_FONT_005"].v2_ids == ("F-13",)


def test_font_012_maps_to_f18():
    """F-18: Artificial bold / faux bold (Wave B catch-up T1)."""
    assert CHECK_NAMES["LPDF_FONT_012"].v2_ids == ("F-18",)


def test_font_013_maps_to_f19():
    """F-19: Artificial italic / faux oblique (Wave B catch-up T1)."""
    assert CHECK_NAMES["LPDF_FONT_013"].v2_ids == ("F-19",)


def test_font_015_maps_to_f38():
    """F-38: Font license / DRM prevents embedding (Wave D T2 batch 2)."""
    assert CHECK_NAMES["LPDF_FONT_015"].v2_ids == ("F-38",)


def test_font_004_maps_to_f05():
    """F-05: Type 3 font present (Wave D T2 batch 1)."""
    assert CHECK_NAMES["LPDF_FONT_004"].v2_ids == ("F-05",)


def test_font_011_maps_to_f10():
    """F-10: Multiple Master font present (Wave D T2 batch 1)."""
    assert CHECK_NAMES["LPDF_FONT_011"].v2_ids == ("F-10",)


def test_text_003_maps_to_f29():
    """F-29: Invisible text rendering mode 3 (Wave D T2 batch 1)."""
    assert CHECK_NAMES["LPDF_TEXT_003"].v2_ids == ("F-29",)


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
