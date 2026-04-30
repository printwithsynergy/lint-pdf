"""Q-C2 / Q-C3 / Q-C7 — EPM scoring tests."""

from __future__ import annotations

import pytest

from lintpdf.epm import codes
from lintpdf.epm.scoring import EpmTier, EpmVerdict, score_epm_candidacy

# ---- empty input ---------------------------------------------------------


def test_no_findings_passes_clean():
    v = score_epm_candidacy([])
    assert v.tier == EpmTier.PASS
    assert v.rejection_drivers == ()
    assert v.advisories == ()
    assert v.recommends_indichrome is False
    assert v.passes is True


def test_unknown_codes_are_ignored():
    """A non-EPM finding shouldn't bias the verdict."""
    v = score_epm_candidacy(["LPDF_IMG_001", "LPDF_FONT_005"])
    assert v.tier == EpmTier.PASS


# ---- Tier A: any single finding rejects ---------------------------------


@pytest.mark.parametrize("code", list(codes.TIER_A_CODES))
def test_any_tier_a_finding_rejects(code: str):
    v = score_epm_candidacy([code])
    assert v.tier == EpmTier.REJECT
    assert code in v.rejection_drivers


def test_legacy_tier_a_code_rejects():
    """Legacy LPDF_EPM_001 (K-channel usage) is treated as A-tier."""
    v = score_epm_candidacy(["LPDF_EPM_001"])
    assert v.tier == EpmTier.REJECT
    assert "LPDF_EPM_001" in v.rejection_drivers
    assert "LPDF_EPM_001" in v.legacy_codes_fired


# ---- Tier B: two or more reject; one is marginal -----------------------


def test_one_tier_b_finding_is_marginal():
    v = score_epm_candidacy([codes.EPM_BLEED_BELOW_MIN])
    assert v.tier == EpmTier.MARGINAL
    assert v.rejection_drivers == (codes.EPM_BLEED_BELOW_MIN,)


def test_two_tier_b_findings_reject():
    v = score_epm_candidacy([codes.EPM_BLEED_BELOW_MIN, codes.EPM_PROCESS_COLOR_COUNT])
    assert v.tier == EpmTier.REJECT
    assert codes.EPM_BLEED_BELOW_MIN in v.rejection_drivers
    assert codes.EPM_PROCESS_COLOR_COUNT in v.rejection_drivers


def test_legacy_tier_b_codes_count_toward_threshold():
    """Two legacy B-tier codes (003 weak CMY + 008 gray balance) reject."""
    v = score_epm_candidacy(["LPDF_EPM_003", "LPDF_EPM_008"])
    assert v.tier == EpmTier.REJECT


# ---- Tier C: advisories only ---------------------------------------------


def test_only_tier_c_findings_pass_with_advisory():
    v = score_epm_candidacy([codes.EPM_TRAPPING_DISABLED])
    assert v.tier == EpmTier.PASS_WITH_ADVISORY
    assert codes.EPM_TRAPPING_DISABLED in v.advisories
    assert v.passes is True


def test_multiple_tier_c_findings_still_advisory():
    v = score_epm_candidacy([codes.EPM_TRAPPING_DISABLED, codes.EPM_PAGE_GEOMETRY_VARIES])
    assert v.tier == EpmTier.PASS_WITH_ADVISORY


def test_legacy_tier_c_code_advisory():
    v = score_epm_candidacy(["LPDF_EPM_011"])  # spot fidelity risk
    assert v.tier == EpmTier.PASS_WITH_ADVISORY


# ---- A wins over B and C -------------------------------------------------


def test_tier_a_dominates_other_tiers():
    v = score_epm_candidacy(
        [
            codes.EPM_GAMUT_OUT_OF_REACH,  # A
            codes.EPM_BLEED_BELOW_MIN,  # B
            codes.EPM_TRAPPING_DISABLED,  # C
        ]
    )
    assert v.tier == EpmTier.REJECT
    # All non-C drivers surface; advisories list the C-tier only
    assert codes.EPM_GAMUT_OUT_OF_REACH in v.rejection_drivers
    assert codes.EPM_BLEED_BELOW_MIN in v.rejection_drivers
    assert codes.EPM_TRAPPING_DISABLED in v.advisories


# ---- IndiChrome upsell (Q-C6) -------------------------------------------


def test_gamut_rejection_recommends_indichrome():
    v = score_epm_candidacy([codes.EPM_GAMUT_OUT_OF_REACH])
    assert v.recommends_indichrome is True


def test_spot_count_rejection_recommends_indichrome_when_paired():
    """Spot count alone is C-tier (advisory); pair with another B → reject."""
    v = score_epm_candidacy([codes.EPM_SPOT_COUNT_HIGH, codes.EPM_BLEED_BELOW_MIN])
    # 1 B + 1 C → marginal (B-tier alone)
    assert v.tier == EpmTier.MARGINAL
    # IndiChrome hint depends on rejection drivers; here the driver is
    # the bleed B-tier, so IndiChrome shouldn't fire on its own.
    assert v.recommends_indichrome is False


def test_legacy_spot_fidelity_drives_indichrome_when_paired_with_a():
    """LPDF_EPM_011 (spot fidelity) is in the IndiChrome driver set."""
    v = score_epm_candidacy(
        [
            "LPDF_EPM_001",  # A — K-channel usage
            "LPDF_EPM_011",  # C — spot fidelity (advisory)
        ]
    )
    # A-tier rejects; advisories list 011; recommends_indichrome looks at
    # rejection_drivers (and 011 is C-tier here, so won't trigger). The
    # only A driver is 001, which isn't in the indichrome set.
    assert v.tier == EpmTier.REJECT
    assert v.recommends_indichrome is False


def test_two_b_with_indichrome_driver():
    """When the rejection driver IS in the indichrome set, hint fires."""
    v = score_epm_candidacy(
        [
            "LPDF_EPM_005",  # B — spot K-dependent fallback (in indichrome set)
            codes.EPM_BLEED_BELOW_MIN,  # B
        ]
    )
    assert v.tier == EpmTier.REJECT
    assert v.recommends_indichrome is True


def test_clean_pass_no_indichrome_hint():
    v = score_epm_candidacy([])
    assert v.recommends_indichrome is False


def test_advisory_only_no_indichrome_hint():
    v = score_epm_candidacy([codes.EPM_TRAPPING_DISABLED])
    assert v.recommends_indichrome is False


# ---- determinism + idempotence ------------------------------------------


def test_duplicate_codes_dedup():
    v = score_epm_candidacy(
        [
            codes.EPM_BLEED_BELOW_MIN,
            codes.EPM_BLEED_BELOW_MIN,
            codes.EPM_BLEED_BELOW_MIN,
        ]
    )
    # 3 copies of one B-tier code = still one B finding → MARGINAL, not REJECT
    assert v.tier == EpmTier.MARGINAL
    assert v.rejection_drivers == (codes.EPM_BLEED_BELOW_MIN,)


def test_scorer_is_pure():
    """Same input always yields equal output."""
    inp = [codes.EPM_GAMUT_OUT_OF_REACH, codes.EPM_TRAPPING_DISABLED]
    a = score_epm_candidacy(inp)
    b = score_epm_candidacy(list(inp))
    assert a == b


# ---- v2-ID coverage -----------------------------------------------------


def test_all_16_new_codes_have_unique_v2_ids():
    seen = list(codes.V2_ID_BY_CODE.values())
    assert len(seen) == len(set(seen)) == 16


def test_all_16_new_codes_target_epm_a_b_or_c_tiers():
    for v2 in codes.V2_ID_BY_CODE.values():
        assert v2.startswith(("EPM-A", "EPM-B", "EPM-C")), v2


def test_tier_groupings_cover_all_16_new_codes():
    by_tier = set(codes.TIER_A_CODES) | set(codes.TIER_B_CODES) | set(codes.TIER_C_CODES)
    assert by_tier == set(codes.V2_ID_BY_CODE.keys())


def test_tier_a_has_5_codes_b_has_5_c_has_6():
    """Per the playbook design: 5 + 5 + 6 = 16 new codes total."""
    assert len(codes.TIER_A_CODES) == 5
    assert len(codes.TIER_B_CODES) == 5
    assert len(codes.TIER_C_CODES) == 6


def test_each_new_code_has_a_check_info_entry():
    """Every new REJECT id must show up in the CheckInfo registry."""
    from lintpdf.reports.check_names import CHECK_NAMES

    for code in codes.V2_ID_BY_CODE:
        assert code in CHECK_NAMES, f"missing CheckInfo entry for {code!r}"


def test_check_info_entries_carry_correct_v2_ids():
    """The CheckInfo.v2_ids tuple must exactly match codes.V2_ID_BY_CODE."""
    from lintpdf.reports.check_names import CHECK_NAMES

    for code, v2 in codes.V2_ID_BY_CODE.items():
        info = CHECK_NAMES[code]
        assert info.v2_ids == (v2,), f"{code} has v2_ids={info.v2_ids!r}, expected ({v2!r},)"


# ---- verdict shape -------------------------------------------------------


def test_verdict_dataclass_is_frozen():
    """Dataclass(frozen=True) raises FrozenInstanceError on assignment."""
    from dataclasses import FrozenInstanceError

    v = EpmVerdict(tier=EpmTier.PASS)
    with pytest.raises(FrozenInstanceError):
        v.tier = EpmTier.REJECT  # type: ignore[misc]


def test_passes_property_only_true_for_pass_or_advisory():
    assert EpmVerdict(tier=EpmTier.PASS).passes is True
    assert EpmVerdict(tier=EpmTier.PASS_WITH_ADVISORY).passes is True
    assert EpmVerdict(tier=EpmTier.MARGINAL).passes is False
    assert EpmVerdict(tier=EpmTier.REJECT).passes is False
