"""K-strip simulator tests.

EPM-A1 / A2 analyzers ask "does dropping the K plate keep this
colour close enough to the original?" The naive CMYK→Lab path is
deterministic + dependency-free; press-accurate alternatives plug
in via the substrate loader.
"""

from __future__ import annotations

import pytest

from siftpdf.epm import icc

# ---- cmyk_to_lab_naive: extremes -----------------------------------------


def test_cmyk_white_paper_is_near_lab_white():
    """100% paper white = (0,0,0,0) → near Lab (100, 0, 0)."""
    L, a, b = icc.cmyk_to_lab_naive((0, 0, 0, 0))
    assert L > 90
    # Neutral white ≈ a* and b* both near zero
    assert abs(a) < 5
    assert abs(b) < 5


def test_cmyk_pure_black_is_near_lab_black():
    """100% K alone → near Lab (0, 0, 0)."""
    L, _, _ = icc.cmyk_to_lab_naive((0, 0, 0, 100))
    assert L < 5


def test_cmyk_full_solid_is_near_lab_black():
    """All four channels at 100% → near Lab black."""
    L, _, _ = icc.cmyk_to_lab_naive((100, 100, 100, 100))
    assert L < 5


def test_cmyk_clamps_negative_values():
    """Negative inputs clamp to 0 — defensive against malformed PDF data."""
    out_of_range = icc.cmyk_to_lab_naive((-50, 0, 0, 0))
    in_range = icc.cmyk_to_lab_naive((0, 0, 0, 0))
    assert out_of_range == in_range


def test_cmyk_clamps_above_100():
    """Values above 100% clamp to 100% — same defensive guard."""
    out_of_range = icc.cmyk_to_lab_naive((150, 0, 0, 0))
    in_range = icc.cmyk_to_lab_naive((100, 0, 0, 0))
    assert out_of_range == in_range


# ---- K-strip ΔE: zero-impact cases ---------------------------------------


def test_no_k_present_gives_zero_strip_delta():
    """If K is already 0, stripping is a no-op."""
    assert icc.cmy_strip_k_delta_e((50, 30, 20, 0)) == 0.0


def test_only_k_drops_to_paper():
    """Pure K → strip yields paper white. Big shift."""
    delta = icc.cmy_strip_k_delta_e((0, 0, 0, 100))
    # Black → white is the maximum possible Lab shift
    assert delta > 50


def test_rich_black_strip_visible_shift():
    """Rich black 40/30/30/100 with K stripped reads as a CMY composite.
    Should produce a substantial ΔE2000."""
    delta = icc.cmy_strip_k_delta_e((40, 30, 30, 100))
    assert delta > 20


# ---- ΔE metric selector --------------------------------------------------


@pytest.mark.parametrize("metric", ["de76", "de94", "de2000"])
def test_strip_delta_supports_each_metric(metric: str):
    """All three metrics return a non-negative number on a non-trivial input."""
    delta = icc.cmy_strip_k_delta_e((40, 20, 20, 80), metric=metric)
    assert delta >= 0


def test_strip_delta_unknown_metric_raises():
    with pytest.raises(ValueError, match="unknown ΔE metric"):
        icc.cmy_strip_k_delta_e((40, 20, 20, 80), metric="unknown_metric")


def test_strip_delta_de76_and_de2000_agree_on_zero():
    """Identical inputs → ΔE = 0 across all metrics."""
    cmyk = (60, 20, 10, 0)
    assert icc.cmy_strip_k_delta_e(cmyk, metric="de76") == 0.0
    assert icc.cmy_strip_k_delta_e(cmyk, metric="de94") == 0.0
    assert icc.cmy_strip_k_delta_e(cmyk, metric="de2000") == 0.0


# ---- is_k_strip_safe ----------------------------------------------------


def test_no_k_is_always_safe():
    assert icc.is_k_strip_safe((50, 30, 10, 0)) is True


def test_full_k_is_unsafe_under_default_tolerance():
    assert icc.is_k_strip_safe((0, 0, 0, 100)) is False


def test_low_k_within_tolerance():
    """Tiny K (1%) shouldn't move the colour past the JND threshold."""
    safe = icc.is_k_strip_safe((30, 20, 15, 1), tolerance_de=2.0)
    assert safe is True


def test_loose_tolerance_passes_anything():
    """A 200 ΔE tolerance is wider than the entire Lab cube."""
    assert icc.is_k_strip_safe((0, 0, 0, 100), tolerance_de=200.0) is True


def test_default_tolerance_matches_in_gamut_constant():
    """The default tolerance for is_k_strip_safe matches IN_GAMUT_DELTA_E
    so callers using the same threshold for gamut + K-strip agree."""
    # Pure K should fail at default tolerance — strongest negative case.
    assert icc.is_k_strip_safe((0, 0, 0, 100)) is False
    # Zero K → identical Lab, well within any tolerance.
    assert icc.is_k_strip_safe((30, 20, 10, 0)) is True


# ---- monotonicity sanity checks -----------------------------------------


def test_strip_delta_increases_with_k():
    """More K → bigger strip shift, holding C/M/Y constant."""
    base = (30, 20, 10, 0)
    a = icc.cmy_strip_k_delta_e((30, 20, 10, 25))
    b = icc.cmy_strip_k_delta_e((30, 20, 10, 50))
    c = icc.cmy_strip_k_delta_e((30, 20, 10, 75))
    assert icc.cmy_strip_k_delta_e(base) == 0.0
    assert a < b < c
