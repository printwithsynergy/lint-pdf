"""Unit tests for the regulatory-compliance category gate
introduced in WS-3."""

from __future__ import annotations

from dataclasses import dataclass

from lintpdf.ai.analyzers.regulatory_compliance._gates import (
    is_ghs_applicable,
    is_pharma_applicable,
)


@dataclass
class _Cfg:
    """Minimal stand-in for ``TenantAIConfig`` — gate only reads
    ``industry_type``, so a dataclass is enough."""

    industry_type: str | None = None


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
