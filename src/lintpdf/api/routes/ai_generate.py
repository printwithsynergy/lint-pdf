"""Natural language Preflight Profile generation endpoint."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.ai_schemas import NLPreflightProfileRequest, NLPreflightProfileResponse
from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db

if TYPE_CHECKING:
    from lintpdf.api.models import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/preflight-profiles", tags=["ai-generate"])

# System prompt for NL preflight profile generation
_SYSTEM_PROMPT = """You are an expert prepress technician generating LintPDF preflight Rulesets.

A Ruleset is a JSON configuration that controls which preflight checks run on a PDF file.

Available fields:
- name: Human-readable name
- description: What this profile checks for
- version: "1.0"
- conformance: "pdfx4" or null
- workflow: "CMYK", "RGB", or "auto"
- checks: {enabled: ["LPDF_*"], disabled: [], severity_overrides: {}}
- thresholds: {min_dpi, max_dpi, tac_limit, min_bleed_mm, hairline_threshold, small_text_threshold, very_small_text_threshold, safety_margin_mm, max_file_size_mb, barcode_min_dpi, barcode_min_grade, barcode_quiet_zone_mm}
- ai: {enabled: true/false, categories: ["all" or specific], features: [], language_for_reports: "en"}

Available AI categories: barcode_detection, content_quality, file_comparison, color_compliance, trend_analysis, dieline_detection, regulatory_compliance, image_analysis, document_classification, logo_verification, spatial_analysis, text_analysis, symbol_detection

Respond with ONLY valid JSON matching the Preflight Profile schema. No explanation outside the JSON."""


@router.post("/generate", response_model=NLPreflightProfileResponse)
async def generate_preflight_profile(
    request: NLPreflightProfileRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> NLPreflightProfileResponse:
    """Generate a Preflight Profile from a natural language description.

    Uses an LLM to interpret the description and produce a valid
    Preflight Profile JSON configuration.
    """
    from lintpdf.ai.access import check_ai_access

    check_ai_access(tenant, db)

    # Try to use Claude API for generation
    try:
        preflight_profile = _generate_with_llm(request.description)
    except Exception:
        logger.exception("LLM preflight profile generation failed")
        # Fall back to rule-based generation
        preflight_profile = _generate_rule_based(request.description)

    # Validate the generated plan against our schema
    from lintpdf.profiles.schema import PreflightProfile

    try:
        validated = PreflightProfile.model_validate(preflight_profile)
        preflight_profile = validated.model_dump()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generated preflight profile failed validation: {exc}",
        ) from exc

    return NLPreflightProfileResponse(
        preflight_profile=preflight_profile,
        explanation=f"Generated Preflight Profile based on: {request.description}",
        confidence=0.85,
    )


def _generate_with_llm(description: str) -> dict[str, Any]:
    """Generate a preflight profile using an LLM."""
    try:
        import anthropic

        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": description}],
        )
        text = message.content[0].text
        result: dict[str, Any] = json.loads(text)
        return result
    except ImportError:
        raise RuntimeError("anthropic package not installed") from None


def _generate_rule_based(description: str) -> dict[str, Any]:  # skipcq: PY-R1000
    """Fallback rule-based preflight profile generation from keywords."""
    desc_lower = description.lower()

    plan: dict[str, Any] = {
        "name": "Generated Preflight Profile",
        "description": description,
        "version": "1.0",
        "conformance": None,
        "workflow": "CMYK",
        "checks": {"enabled": ["LPDF_*"], "disabled": [], "severity_overrides": {}},
        "thresholds": {},
        "ai": {"enabled": False, "categories": [], "features": [], "language_for_reports": "en"},
    }

    # Detect workflow
    if "rgb" in desc_lower:
        plan["workflow"] = "RGB"

    # Detect conformance
    if "pdf/x-4" in desc_lower or "pdfx4" in desc_lower or "pdf/x" in desc_lower:
        plan["conformance"] = "pdfx4"
        plan["checks"]["enabled"] = ["LPDF_*", "PDFX4-*"]

    # DPI thresholds
    if "300 dpi" in desc_lower or "300dpi" in desc_lower:
        plan["thresholds"]["min_dpi"] = 300.0
    if "150 dpi" in desc_lower:
        plan["thresholds"]["min_dpi"] = 150.0

    # AI features
    ai_categories: list[str] = []
    if any(w in desc_lower for w in ["barcode", "qr code", "ean", "upc"]):
        ai_categories.append("barcode_detection")
    if any(w in desc_lower for w in ["fda", "nutrition facts", "food label"]):
        ai_categories.append("regulatory_compliance")
        plan["ai"]["features"] = [*plan["ai"].get("features", []), "fda_nutrition_facts"]
    if any(w in desc_lower for w in ["eu", "fir 1169", "allergen"]):
        ai_categories.append("regulatory_compliance")
        plan["ai"]["features"] = [*plan["ai"].get("features", []), "eu_fir_1169"]
    if any(w in desc_lower for w in ["ghs", "clp", "chemical", "hazard"]):
        ai_categories.append("regulatory_compliance")
        plan["ai"]["features"] = [*plan["ai"].get("features", []), "ghs_clp_compliance"]
    if any(w in desc_lower for w in ["pharma", "pharmaceutical", "drug"]):
        ai_categories.append("regulatory_compliance")
    if any(w in desc_lower for w in ["brand", "palette", "color compliance"]):
        ai_categories.append("color_compliance")
    if any(w in desc_lower for w in ["spell", "grammar", "language"]):
        ai_categories.append("content_quality")
    if any(w in desc_lower for w in ["logo", "brand mark"]):
        ai_categories.append("logo_verification")
    if any(w in desc_lower for w in ["die line", "dieline", "packaging"]):
        ai_categories.append("dieline_detection")
    if any(w in desc_lower for w in ["nsfw", "explicit", "inappropriate"]):
        ai_categories.append("image_analysis")
    if any(w in desc_lower for w in ["wcag", "contrast", "accessibility"]):
        ai_categories.append("color_compliance")

    if ai_categories:
        plan["ai"]["enabled"] = True
        plan["ai"]["categories"] = list(set(ai_categories))

    # Full AI scan keywords
    if "full ai" in desc_lower or "all ai" in desc_lower or "every ai" in desc_lower:
        plan["ai"]["enabled"] = True
        plan["ai"]["categories"] = ["all"]

    return plan
