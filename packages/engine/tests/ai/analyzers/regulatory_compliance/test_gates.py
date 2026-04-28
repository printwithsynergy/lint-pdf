"""Unit tests for the regulatory-compliance category gate
introduced in WS-3."""

from __future__ import annotations

from dataclasses import dataclass

from lintpdf.ai.analyzers.regulatory_compliance._gates import (
    is_cosmetic_applicable,
    is_eu_food_applicable,
    is_ghs_applicable,
    is_pharma_applicable,
)


@dataclass
class _Cfg:
    """Minimal stand-in for ``TenantAIConfig`` — gate reads
    ``industry_type`` + ``regulatory_market``, so a dataclass is enough."""

    industry_type: str | None = None
    regulatory_market: str | None = None


def test_unknown_industry_runs_by_default() -> None:
    assert is_pharma_applicable(None) is True
    assert is_pharma_applicable(_Cfg(industry_type=None)) is True
    assert is_ghs_applicable(None) is True


def test_dietary_supplement_skips_pharma_and_ghs() -> None:
    cfg = _Cfg(industry_type="dietary_supplement")
    assert is_pharma_applicable(cfg) is False
    assert is_ghs_applicable(cfg) is False


def test_normalisation_is_case_and_space_insensitive() -> None:
    for val in (
        "Dietary Supplement",
        "DIETARY-SUPPLEMENT",
        "  dietary_supplement  ",
        "Supplement",
    ):
        assert is_pharma_applicable(_Cfg(industry_type=val)) is False, val


def test_food_beverage_cosmetic_pet_food_all_skip() -> None:
    for val in ("food", "beverage", "cosmetic", "pet_food", "nutraceutical"):
        assert is_pharma_applicable(_Cfg(industry_type=val)) is False, val
        assert is_ghs_applicable(_Cfg(industry_type=val)) is False, val


def test_pharmaceutical_runs() -> None:
    cfg = _Cfg(industry_type="pharmaceutical")
    assert is_pharma_applicable(cfg) is True
    assert is_ghs_applicable(cfg) is True


def test_chemical_runs() -> None:
    cfg = _Cfg(industry_type="chemical")
    assert is_ghs_applicable(cfg) is True


# ---------------------------------------------------------------------------
# regulatory_market gating (added 2026-04-27 after second Opus audit)
# ---------------------------------------------------------------------------


def test_pharma_skipped_when_market_is_non_eu_even_for_chemical_tenant() -> None:
    """Even an explicit chemical tenant shouldn't see EU pharma rules
    if their target market is the US — the rule is EU-specific."""
    for market in ("us_fda", "ca_cfia", "uk_mhra", "intl"):
        cfg = _Cfg(industry_type="pharmaceutical", regulatory_market=market)
        assert is_pharma_applicable(cfg) is False, market


def test_pharma_runs_when_market_is_eu() -> None:
    for market in ("eu", "europe", "ema"):
        cfg = _Cfg(industry_type="pharmaceutical", regulatory_market=market)
        assert is_pharma_applicable(cfg) is True, market


def test_eu_food_skipped_for_us_ca_markets() -> None:
    """The dominant 2026-04-27 false-positive class: AI_EU1169_001
    firing on Canadian/US supplement labels."""
    for market in ("us_fda", "ca_cfia", "uk_mhra", "intl"):
        cfg = _Cfg(industry_type="dietary_supplement", regulatory_market=market)
        assert is_eu_food_applicable(cfg) is False, market


def test_eu_food_runs_when_market_is_eu() -> None:
    for market in ("eu", "europe", "eu_fir"):
        cfg = _Cfg(industry_type="food", regulatory_market=market)
        assert is_eu_food_applicable(cfg) is True, market


def test_eu_food_runs_when_market_unset_and_industry_is_food() -> None:
    """No market hint, but industry IS food → run (FIR 1169 is the
    right rule)."""
    for industry in ("food", "beverage", "dietary_supplement", "supplement"):
        cfg = _Cfg(industry_type=industry, regulatory_market=None)
        assert is_eu_food_applicable(cfg) is True, industry


def test_eu_food_skipped_when_industry_is_non_food_and_market_unset() -> None:
    """Cosmetic / pet-food / chemical tenants don't get FIR 1169
    flagged unless their market is explicitly EU."""
    for industry in ("cosmetic", "pet_food", "chemical"):
        cfg = _Cfg(industry_type=industry, regulatory_market=None)
        assert is_eu_food_applicable(cfg) is False, industry


def test_eu_food_unset_everything_runs_default() -> None:
    """Both unset → over-report (existing default-fire posture)."""
    assert is_eu_food_applicable(None) is True
    assert is_eu_food_applicable(_Cfg()) is True


# ---------------------------------------------------------------------------
# is_cosmetic_applicable — added 2026-04-28 after second Opus audit
# ---------------------------------------------------------------------------


def test_cosmetic_skipped_for_dietary_supplement() -> None:
    """The dominant 2026-04-27 cosmetic-rule false-positive class:
    AI_COSM_001/002 firing on Nutrops dietary-supplement labels."""
    cfg = _Cfg(industry_type="dietary_supplement")
    assert is_cosmetic_applicable(cfg) is False


def test_cosmetic_skipped_for_food_beverage() -> None:
    for industry in ("food", "beverage", "supplement", "nutraceutical", "pet_food"):
        assert is_cosmetic_applicable(_Cfg(industry_type=industry)) is False, industry


def test_cosmetic_runs_for_cosmetic_industry() -> None:
    for industry in ("cosmetic", "personal_care"):
        assert is_cosmetic_applicable(_Cfg(industry_type=industry)) is True, industry


def test_cosmetic_unknown_runs_default() -> None:
    """Unknown / unset → over-report (structural patterns are the
    safety net)."""
    assert is_cosmetic_applicable(None) is True
    assert is_cosmetic_applicable(_Cfg(industry_type=None)) is True


def test_cosmetic_pharmaceutical_runs() -> None:
    """Categorised as pharmaceutical (not in food bucket) → still
    runs; the analyzer's structural patterns sort it out."""
    assert is_cosmetic_applicable(_Cfg(industry_type="pharmaceutical")) is True
