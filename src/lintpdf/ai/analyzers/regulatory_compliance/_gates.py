"""Category gates for regulatory-compliance rules.

The 2026-04-23 Opus audit flagged 7 false-positive ``AI_PHARMA_001``
rows on a dietary-supplement pouch (Nutrops) and 1 false-positive
``AI_GHS_003`` row where Prop 65 cautionary text on the same
supplement was conflated with CLP/GHS hazard labelling. These
regulations simply don't apply to food / dietary supplement /
cosmetic / pet-food products, so a tenant whose
``TenantAIConfig.industry_type`` lands in the exclusion set should
see those rules no-op.

The helper is deliberately conservative: when the tenant's
``industry_type`` is unknown (``None``) the gate returns ``True``
so the rule still runs. Over-reporting is strictly better than
silent misses on tenants who haven't configured the field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig

# Product categories where EU pharma font rules (1.4mm x-height,
# 7pt Didot minimum) and CLP/GHS hazard labelling do NOT apply.
# These are food-grade / OTC-grade categories regulated under
# different instruments (FIR 1169/2011, FDA Food Labeling, etc.).
_NON_HAZMAT_CATEGORIES: frozenset[str] = frozenset(
    {
        "dietary_supplement",
        "supplement",
        "food",
        "beverage",
        "nutraceutical",
        "cosmetic",
        "personal_care",
        "pet_food",
        "animal_feed",
    }
)


def _normalise(raw: str | None) -> str | None:
    """Lowercase + strip + underscore-collapse so ``"Dietary Supplement"``,
    ``"dietary-supplement"`` and ``"DIETARY_SUPPLEMENT"`` all map to
    the same canonical key."""
    if not raw:
        return None
    return raw.strip().lower().replace("-", "_").replace(" ", "_")


# Markets we treat as "definitely non-EU" — when ``regulatory_market``
# names one of these, EU-specific rules (FIR 1169 x-height, EU pharma
# font, CLP/GHS hazard labelling) should NOT fire. The lists are
# deliberately permissive to absorb tenant-side spelling variants.
_NON_EU_MARKETS: frozenset[str] = frozenset(
    {
        "us",
        "usa",
        "us_fda",
        "fda",
        "ca",
        "can",
        "canada",
        "ca_cfia",
        "cfia",
        "health_canada",
        "uk",
        "uk_mhra",
        "mhra",  # post-Brexit, not in EU
        "intl",
        "international",
        "global",
        "row",
    }
)

# Markets we treat as "definitely EU".
_EU_MARKETS: frozenset[str] = frozenset(
    {
        "eu",
        "eu_fir",
        "eu_clp",
        "europe",
        "ema",
        "ec",
        "european_union",
    }
)


def _market(ai_config: TenantAIConfig | None) -> str | None:
    """Return the normalised regulatory market or None if unset."""
    if ai_config is None:
        return None
    return _normalise(getattr(ai_config, "regulatory_market", None))


def is_pharma_applicable(ai_config: TenantAIConfig | None) -> bool:
    """True when ``AI_PHARMA_001`` should fire on this tenant.

    * ``regulatory_market`` explicitly non-EU → False (still skip; pharma
      x-height gate doesn't apply outside EU even on chemical tenants).
    * Unknown / unset ``industry_type`` → True (over-report by
      default; conservative on uncategorised tenants).
    * ``industry_type`` in the exclusion set → False (skip the
      rule entirely; emit no finding).
    * Any other value → True (explicitly configured, assume the
      operator wants the pharma check).
    """
    if _market(ai_config) in _NON_EU_MARKETS:
        return False
    if ai_config is None:
        return True
    normalised = _normalise(getattr(ai_config, "industry_type", None))
    if normalised is None:
        return True
    return normalised not in _NON_HAZMAT_CATEGORIES


def is_ghs_applicable(ai_config: TenantAIConfig | None) -> bool:
    """True when ``AI_GHS_003`` (H-statements without pictograms)
    should fire. Same exclusion set as pharma — CLP/GHS labelling
    regulates chemicals, not food / supplements / cosmetics."""
    return is_pharma_applicable(ai_config)


def is_eu_food_applicable(ai_config: TenantAIConfig | None) -> bool:
    """True when ``AI_EU1169_001`` (FIR 1169/2011) should fire.

    Mirrors :func:`is_pharma_applicable` but inverted around the EU axis:

    * ``regulatory_market`` in :data:`_NON_EU_MARKETS` → False (skip;
      FIR 1169 is a pure-EU instrument and doesn't apply to US/CA/UK
      labelling). This was the dominant false-positive source on the
      2026-04-27 Opus audit (28 of 95 disagreements).
    * ``regulatory_market`` in :data:`_EU_MARKETS` → True (run the rule).
    * Both ``regulatory_market`` AND ``industry_type`` unset → True
      (over-report by default; the operator hasn't told us anything).
    * ``industry_type`` set to a food/beverage/supplement category and
      market is unset → True (food categories are the rule's target;
      run by default).
    * Any other combination (e.g. industry_type=cosmetic, market unset)
      → False (FIR 1169 is food-specific, so cosmetic / pet-food / etc.
      tenants without an explicit EU market shouldn't see it).
    """
    market = _market(ai_config)
    if market in _NON_EU_MARKETS:
        return False
    if market in _EU_MARKETS:
        return True
    if ai_config is None:
        return True
    industry = _normalise(getattr(ai_config, "industry_type", None))
    if industry is None:
        # No market, no industry — over-report (existing behaviour).
        return True
    # Food/beverage/supplement industry without an explicit market →
    # run (FIR 1169 is the right rule for these categories).
    return industry in {"food", "beverage", "dietary_supplement", "supplement", "nutraceutical"}


def is_cosmetic_applicable(ai_config: TenantAIConfig | None) -> bool:
    """True when ``AI_COSM_001`` / ``AI_COSM_002`` (cosmetic / personal-
    care label rules) should fire on this tenant.

    The 2026-04-27 Opus audit flagged 4 false positives where cosmetic
    rules fired on US dietary-supplement Nutrops labels — the analyzer's
    structural detection (``Ingredients:`` header + INCI patterns)
    overlaps with food/supplement labels.

    * ``industry_type`` in {cosmetic, personal_care} → True.
    * ``industry_type`` in the food/supplement exclusion set → False
      (skip; cosmetic rules do not apply to food/supplement products).
    * Unknown / unset → True (over-report; existing default-fire
      posture preserved for uncategorised tenants).
    """
    if ai_config is None:
        return True
    industry = _normalise(getattr(ai_config, "industry_type", None))
    if industry is None:
        return True
    if industry in {"cosmetic", "personal_care"}:
        return True
    # Food / supplement / beverage / pet-food / nutraceutical -> not a
    # cosmetic; suppress. Anything else (pharmaceutical / chemical /
    # unknown other) -> leave the rule running, the analyzer's
    # structural patterns are the safety net.
    return industry not in _NON_HAZMAT_CATEGORIES


# Document-level supplement / dietary-product signals. These are the
# fallback when ``ai_config`` is unavailable or detached at runtime
# (which happens in the worker after the DB session closes — the
# 2026-04-28 Opus audit showed the cosmetic + FDA gates not engaging
# despite ``industry_type=dietary_supplement`` being set on the
# tenant). The signals come straight from the page content stream
# so they survive any ORM detachment.
import re as _re  # noqa: E402

_SUPPLEMENT_DOCUMENT_PATTERNS: tuple[_re.Pattern[str], ...] = (
    _re.compile(r"\bSupplement\s+Facts\b", _re.IGNORECASE),
    _re.compile(r"\bDietary\s+Supplement\b", _re.IGNORECASE),
    _re.compile(r"\bSupplemental\s+Facts\b", _re.IGNORECASE),
)


def is_supplement_document(document) -> bool:  # type: ignore[no-untyped-def]
    """True when any page's content stream contains a supplement-
    panel marker (``Supplement Facts`` header or ``Dietary
    Supplement`` claim).

    Used by ``CosmeticsLabelingAnalyzer``, ``FdaNutritionAnalyzer``,
    and ``EuFir1169Analyzer`` as a content-derived fallback when the
    tenant's ``ai_config.industry_type`` isn't accessible (detached
    SQLAlchemy session in the worker, etc.).

    * ``Supplement Facts`` panel → governed by 21 CFR 101.36 (DSHEA),
      not 101.9 (Nutrition Facts). Also not a cosmetic, also not a
      conventional food (FIR 1169 doesn't apply).
    * ``Dietary Supplement`` claim text → same conclusion.
    """
    pages = getattr(document, "pages", None) or []
    for page in pages:
        raw = getattr(page, "content_stream", None)
        if not raw:
            continue
        if isinstance(raw, bytes):
            try:
                text = raw.decode("latin-1")
            except Exception:
                continue
        else:
            text = str(raw)
        for pat in _SUPPLEMENT_DOCUMENT_PATTERNS:
            if pat.search(text):
                return True
    return False
