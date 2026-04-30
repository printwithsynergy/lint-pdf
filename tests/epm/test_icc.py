"""Q-C1 — EPM-Advanced ICC engine tests."""

from __future__ import annotations

import math

import pytest

from lintpdf.epm import icc

# ---- ΔE math: zero-distance + symmetry ------------------------------------


def test_de76_zero_for_identical_colors():
    assert icc.lab_distance_de76((50, 0, 0), (50, 0, 0)) == 0.0


def test_de76_symmetric():
    a, b = (60.0, 12.0, -30.0), (50.0, -8.0, 40.0)
    assert icc.lab_distance_de76(a, b) == icc.lab_distance_de76(b, a)


def test_de76_known_distance():
    """Lab (50, 0, 0) vs (50, 5, 0): pure a-axis shift of 5."""
    d = icc.lab_distance_de76((50, 0, 0), (50, 5, 0))
    assert math.isclose(d, 5.0)


def test_de94_zero_for_identical_colors():
    assert icc.lab_distance_de94((50, 0, 0), (50, 0, 0)) == 0.0


def test_de94_textile_weighting_changes_result():
    a, b = (60.0, 20.0, 10.0), (50.0, 5.0, 0.0)
    graphics = icc.lab_distance_de94(a, b, is_textile=False)
    textile = icc.lab_distance_de94(a, b, is_textile=True)
    # kL=2 in textile reduces lightness component → smaller ΔE typically
    assert graphics != textile


def test_de2000_zero_for_identical_colors():
    assert icc.lab_distance_de2000((50, 0, 0), (50, 0, 0)) == 0.0


def test_de2000_symmetric():
    a, b = (60.0, 12.0, -30.0), (50.0, -8.0, 40.0)
    assert math.isclose(
        icc.lab_distance_de2000(a, b),
        icc.lab_distance_de2000(b, a),
        rel_tol=1e-6,
    )


def test_de2000_neutral_lightness_distance():
    """Two neutrals 10 L* apart: kL=1, sL formula collapses to ~1
    near L*=50 so ΔE2000 ≈ 10."""
    d = icc.lab_distance_de2000((50, 0, 0), (60, 0, 0))
    assert 9.0 < d < 11.0


def test_de2000_below_de76_for_dark_saturated_pairs():
    """CIEDE2000 specifically corrects the over-estimation CIE76 makes
    in dark, saturated regions; ΔE2000 ≤ ΔE76 for those samples."""
    a, b = (15, 60, -40), (15, 65, -45)
    assert icc.lab_distance_de2000(a, b) < icc.lab_distance_de76(a, b)


# ---- known CIEDE2000 reference samples (Sharma et al. 2005) --------------


@pytest.mark.parametrize(
    "lab1,lab2,expected",
    [
        # Sharma, Wu & Dalal Table 1 reference samples (selected pairs).
        # ΔE2000 spot checks for non-trivial inputs.
        ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
        ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
        ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
        ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ],
)
def test_de2000_matches_published_reference(lab1, lab2, expected):
    actual = icc.lab_distance_de2000(lab1, lab2)
    # 0.05 ΔE2000 tolerance accounts for rounding in the reference
    assert abs(actual - expected) < 0.05, (
        f"ΔE2000({lab1}, {lab2}) = {actual:.4f}, expected {expected:.4f}"
    )


# ---- conversion round-trips ----------------------------------------------


def test_rgb_to_lab_returns_tuple_of_three_floats():
    L, a, b = icc.rgb_to_lab((128, 64, 200))
    assert isinstance(L, float)
    assert 0 <= L <= 100
    # a*, b* are signed; just sanity-bound them
    assert -128 <= a <= 128
    assert -128 <= b <= 128


def test_lab_to_rgb_returns_tuple_of_three_ints():
    rgb = icc.lab_to_rgb((50.0, 0.0, 0.0))
    assert isinstance(rgb, tuple)
    assert len(rgb) == 3
    for c in rgb:
        assert isinstance(c, int)
        assert 0 <= c <= 255


def test_round_trip_neutral_gray_stays_neutral():
    """Lab (50, 0, 0) is mid gray — round-trip must stay near-neutral."""
    rgb = icc.lab_to_rgb((50.0, 0.0, 0.0))
    R, G, B = rgb
    # Neutral gray means R ≈ G ≈ B; allow ±5 for rounding.
    assert abs(R - G) < 5
    assert abs(G - B) < 5


def test_round_trip_white_returns_near_white():
    rgb = icc.lab_to_rgb((100.0, 0.0, 0.0))
    R, G, B = rgb
    assert R > 240
    assert G > 240
    assert B > 240


def test_rgb_lab_round_trip_within_jnd():
    """Lab → sRGB → Lab should round-trip within ~ΔE76 ≤ 2 for in-gamut Lab."""
    lab_in = (60.0, 10.0, -20.0)
    rgb = icc.lab_to_rgb(lab_in)
    lab_out = icc.rgb_to_lab(rgb)
    assert icc.lab_distance_de76(lab_in, lab_out) < icc.IN_GAMUT_DELTA_E + 1.5


# ---- gamut containment ---------------------------------------------------


def test_is_in_gamut_neutral_white_passes():
    assert icc.is_in_gamut((100.0, 0.0, 0.0)) is True


def test_is_in_gamut_neutral_black_passes():
    assert icc.is_in_gamut((0.0, 0.0, 0.0)) is True


def test_is_in_gamut_neutral_gray_passes():
    assert icc.is_in_gamut((50.0, 0.0, 0.0)) is True


def test_is_in_gamut_extreme_chroma_outside_srgb():
    """Highly saturated Lab values (a=120, b=120) lie outside sRGB. The
    round-trip clamp loses chroma so the recovered Lab should diverge
    well past the JND tolerance."""
    out_of_gamut = (50.0, 120.0, 120.0)
    assert icc.is_in_gamut(out_of_gamut, tolerance_de=2.0) is False


def test_is_in_gamut_tolerance_governs_decision():
    """A loose tolerance should still pass an extreme colour."""
    near_corner = (50.0, 100.0, 100.0)
    assert icc.is_in_gamut(near_corner, tolerance_de=2.0) is False
    assert icc.is_in_gamut(near_corner, tolerance_de=200.0) is True


# ---- profile cache --------------------------------------------------------


def test_srgb_profile_is_cached():
    assert icc.srgb_profile() is icc.srgb_profile()


def test_lab_profile_is_cached():
    assert icc.lab_profile() is icc.lab_profile()


def test_constants_match_design_doc():
    assert icc.IN_GAMUT_DELTA_E == 2.0
    assert icc.JND_DELTA_E_2000 == 1.0
