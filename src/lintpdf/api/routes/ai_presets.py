"""AI preset listing endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, status  # noqa: E402
from sqlalchemy.orm import Session  # noqa: TC002, E402

from lintpdf.api.ai_schemas import (  # noqa: E402
    AIPresetFeature,
    AIPresetListResponse,
    AIPresetResponse,
)
from lintpdf.api.auth import get_current_tenant  # noqa: E402
from lintpdf.api.database import get_db  # noqa: E402

if TYPE_CHECKING:
    from lintpdf.api.models import Tenant

router = APIRouter(prefix="/api/v1/ai/presets", tags=["ai-presets"])

# Pre-built AI presets
_AI_PRESETS: dict[str, dict[str, Any]] = {
    "fda-food-label": {
        "name": "FDA Food Label",
        "description": "FDA Nutrition Facts panel validation (21 CFR 101.9) plus barcode and content checks.",
        "features": [
            "fda_nutrition_facts",
            "barcode_decode",
            "barcode_dimension_validation",
            "barcode_content_validation",
            "spell_check",
            "language_detection",
        ],
    },
    "eu-food-label": {
        "name": "EU Food Label",
        "description": "EU Food Information Regulation 1169/2011 compliance plus barcode and content checks.",
        "features": [
            "eu_fir_1169",
            "barcode_decode",
            "barcode_dimension_validation",
            "spell_check",
            "language_detection",
        ],
    },
    "pharma-eu": {
        "name": "Pharma EU",
        "description": "European pharmaceutical packaging compliance including serialization and font validation.",
        "features": [
            "pharma_serialization_validation",
            "pharma_font_compliance",
            "barcode_decode",
            "spell_check",
            "language_detection",
            "regulatory_symbol_detection",
        ],
    },
    "ghs-chemical": {
        "name": "GHS Chemical",
        "description": "GHS/CLP chemical label compliance (EU Regulation 1272/2008).",
        "features": [
            "ghs_clp_compliance",
            "barcode_decode",
            "spell_check",
            "regulatory_symbol_detection",
        ],
    },
    "packaging-qc": {
        "name": "Packaging QC",
        "description": "Comprehensive packaging quality control with die line detection, barcodes, logos, and spatial analysis.",
        "features": [
            "dieline_by_name",
            "barcode_decode",
            "barcode_dimension_validation",
            "logo_detection",
            "safe_zone_violations",
            "file_classification",
            "duplicate_detection",
            "image_quality_assessment",
        ],
    },
    "brand-compliance": {
        "name": "Brand Compliance",
        "description": "Brand color palette verification, logo detection, spell checking, and WCAG contrast validation.",
        "features": [
            "brand_palette_check",
            "logo_detection",
            "spell_check",
            "wcag_contrast_check",
            "version_diff",
        ],
    },
    "full-ai-scan": {
        "name": "Full AI Scan",
        "description": "Every available Tier 1 and Tier 2 AI inspection enabled.",
        "features": ["all"],
    },
}


def _get_feature_info(slug: str) -> AIPresetFeature:
    """Look up feature category and tier from registry."""
    try:
        from lintpdf.ai.registry import get_available_features

        for f in get_available_features():
            if f["slug"] == slug:
                return AIPresetFeature(slug=slug, category=f["category"], tier=f["tier"])
    except Exception:
        logger.debug("Failed to look up AI feature %s from registry", slug, exc_info=True)
    return AIPresetFeature(slug=slug, category="unknown", tier="unknown")


@router.get("", response_model=AIPresetListResponse)
async def list_presets(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AIPresetListResponse:
    """List available AI presets."""
    presets = []
    for slug, data in _AI_PRESETS.items():
        features = data.get("features", [])
        presets.append(
            AIPresetResponse(
                slug=slug,
                name=str(data["name"]),
                description=str(data["description"]),
                features=[_get_feature_info(f) for f in features if isinstance(f, str)],
            )
        )
    return AIPresetListResponse(presets=presets)


@router.get("/{slug}", response_model=AIPresetResponse)
async def get_preset(
    slug: str,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AIPresetResponse:
    """Get details of a specific AI preset."""
    if slug not in _AI_PRESETS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI preset '{slug}' not found.",
        )

    data = _AI_PRESETS[slug]
    features = data.get("features", [])

    return AIPresetResponse(
        slug=slug,
        name=str(data["name"]),
        description=str(data["description"]),
        features=[_get_feature_info(f) for f in features if isinstance(f, str)],
    )
