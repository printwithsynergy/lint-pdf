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


def is_pharma_applicable(ai_config: TenantAIConfig | None) -> bool:
    """True when ``AI_PHARMA_001`` should fire on this tenant.

    * Unknown / unset ``industry_type`` → True (over-report by
      default; conservative on uncategorised tenants).
    * ``industry_type`` in the exclusion set → False (skip the
      rule entirely; emit no finding).
    * Any other value → True (explicitly configured, assume the
      operator wants the pharma check).
    """
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
