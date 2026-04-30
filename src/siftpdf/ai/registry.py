"""AI analyzer registry — discovers and filters AI analyzers by category/feature."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siftpdf.ai.base import BaseAIAnalyzer

logger = logging.getLogger(__name__)

# Global registry of AI analyzer classes
_REGISTRY: list[type[BaseAIAnalyzer]] = []


def register_ai_analyzer(cls: type[BaseAIAnalyzer]) -> type[BaseAIAnalyzer]:
    """Decorator to register an AI analyzer class."""
    _REGISTRY.append(cls)
    return cls


def get_all_ai_analyzers() -> list[type[BaseAIAnalyzer]]:
    """Return all registered AI analyzer classes."""
    return list(_REGISTRY)


def get_ai_analyzers(  # skipcq: PY-R1000
    categories: list[str] | None = None,
    features: list[str] | None = None,
    tier: str | None = None,
) -> list[BaseAIAnalyzer]:
    """Instantiate and return AI analyzers matching the given filters.

    Args:
        categories: Category slugs to include. ["all"] or None means all.
        features: Specific feature slugs (takes precedence over categories if non-empty).
        tier: Filter by tier ("cpu" or "gpu"). None means all tiers.

    Returns:
        List of instantiated analyzer objects.
    """
    _ensure_registered()

    analyzers: list[BaseAIAnalyzer] = []
    use_all = categories is None or "all" in categories

    for cls in _REGISTRY:
        # Tier filter
        if tier is not None and cls.tier != tier:
            continue

        # Feature-level filter takes precedence
        if features:
            if cls.feature_slug in features:
                analyzers.append(cls())
            continue

        # Category-level filter
        if use_all or (categories and cls.category in categories):
            analyzers.append(cls())

    return analyzers


def get_available_categories() -> list[dict[str, str]]:
    """Return list of available AI categories with metadata."""
    _ensure_registered()

    seen: dict[str, dict[str, str]] = {}
    for cls in _REGISTRY:
        if cls.category not in seen:
            seen[cls.category] = {
                "slug": cls.category,
                "tier": cls.tier,
            }
    return list(seen.values())


def get_available_features() -> list[dict[str, str]]:
    """Return list of all available AI features."""
    _ensure_registered()

    return [
        {
            "slug": cls.feature_slug,
            "category": cls.category,
            "tier": cls.tier,
            "credits": str(cls.credits_per_run),
        }
        for cls in _REGISTRY
    ]


_registry_state: dict[str, bool] = {"registered": False}


def _ensure_registered() -> None:
    """Ensure all AI analyzer modules have been imported (lazy registration)."""
    if _registry_state["registered"]:
        return
    _registry_state["registered"] = True

    # Import all analyzer modules to trigger @register_ai_analyzer decorators
    try:
        import siftpdf.ai.analyzers  # noqa: F401
    except ImportError:
        logger.debug("AI analyzer modules not yet available")
