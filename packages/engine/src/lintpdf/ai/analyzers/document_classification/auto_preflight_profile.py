"""Auto preflight profile recommendation analyzer — suggests inspection profiles.

Uses the file classification result (from file_classification analyzer) and
document metadata to recommend an appropriate preflight profile (inspection profile)
for the document.  This is purely advisory: the orchestrator or user makes the
final decision.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.ai.types import (
    GPUInferenceClient,
    GPUServiceNotConfiguredError,
    GPUServiceRateLimitedError,
    GPUServiceUnavailableError,
)
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.ai.types import AIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Mapping from document classification labels to recommended preflight profiles
_CLASS_TO_PROFILE: dict[str, dict[str, str]] = {
    "packaging_artwork": {
        "plan": "packaging_full",
        "description": "Full packaging artwork inspection (barcode, color, text, regulatory)",
    },
    "label": {
        "plan": "label_standard",
        "description": "Label inspection (text, regulatory, barcode, safe zones)",
    },
    "leaflet": {
        "plan": "leaflet_standard",
        "description": "Leaflet/insert inspection (text, regulatory, folding marks)",
    },
    "carton": {
        "plan": "carton_full",
        "description": "Carton inspection (dieline, barcode, text, color, safe zones)",
    },
    "technical_drawing": {
        "plan": "technical_review",
        "description": "Technical drawing review (dimensions, annotations, dieline)",
    },
    "promotional": {
        "plan": "promo_review",
        "description": "Promotional material review (brand compliance, image quality, text)",
    },
}

_DEFAULT_PLAN = {
    "plan": "general_preflight",
    "description": "General preflight inspection (standard checks)",
}


def _get_gpu_client() -> GPUInferenceClient:
    # Delegates to the process-level shared client so the circuit breaker
    # accumulates failures across analyzers (see gpu_client.get_gpu_client).
    from lintpdf.ai.types import get_gpu_client

    return get_gpu_client()


@register_ai_analyzer
class AutoPreflightProfileAnalyzer(BaseAIAnalyzer):
    """Recommend a preflight profile based on document classification."""

    category = "document_classification"
    feature_slug = "auto_preflight_profile_recommendation"
    tier = "gpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        from lintpdf.ai.rendering import render_page_to_image

        # Perform classification to drive the recommendation
        try:
            first_page_png = render_page_to_image(pdf_bytes, page_num=1, dpi=150)
        except RuntimeError:
            logger.debug("auto_preflight_profile: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()

        try:
            result = gpu.classify_document(first_page_png)
        except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
            logger.debug("auto_preflight_profile: GPU service not configured, skipping")
            return []
        except GPUServiceUnavailableError as exc:
            return [
                self._make_finding(
                    inspection_id="AI_AFP_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"GPU inference service unavailable for preflight profile recommendation: {exc}"
                    ),
                    details={"reason": "gpu_unavailable"},
                )
            ]

        predicted_class = result.get("predicted_class", "unknown")
        confidence = float(result.get("confidence", 0))

        # Look up the recommended preflight profile
        plan_info = _CLASS_TO_PROFILE.get(predicted_class, _DEFAULT_PLAN)

        # Factor in page count for plan refinement
        page_count = len(document.pages) if document.pages else 0
        plan_name = plan_info["plan"]
        plan_desc = plan_info["description"]

        # Multi-page documents may need additional leaflet/booklet checks
        if page_count > 4 and predicted_class not in ("leaflet", "technical_drawing"):
            plan_name = f"{plan_name}_multipage"
            plan_desc = f"{plan_desc} (multi-page variant)"

        # Factor in tenant industry type for regulatory tailoring
        industry = getattr(ai_config, "industry_type", None) if ai_config else None
        regulatory_market = getattr(ai_config, "regulatory_market", None) if ai_config else None

        if industry == "pharma":
            plan_name = f"{plan_name}_pharma"
            plan_desc = f"{plan_desc} + pharmaceutical regulatory checks"
        elif industry == "food":
            plan_name = f"{plan_name}_food"
            plan_desc = f"{plan_desc} + food labeling regulatory checks"

        findings: list[Finding] = [
            self._make_finding(
                inspection_id="AI_AFP_002",
                severity=Severity.ADVISORY,
                message=(f"Recommended preflight profile: '{plan_name}' — {plan_desc}"),
                details={
                    "recommended_plan": plan_name,
                    "plan_description": plan_desc,
                    "based_on_class": predicted_class,
                    "classification_confidence": round(confidence, 4),
                    "page_count": page_count,
                    "industry_type": industry,
                    "regulatory_market": regulatory_market,
                },
            )
        ]

        if confidence < 0.5:
            findings.append(
                self._make_finding(
                    inspection_id="AI_AFP_003",
                    severity=Severity.ADVISORY,
                    message=(
                        "Preflight profile recommendation has low confidence "
                        f"({confidence:.0%}). Manual selection may be more "
                        "appropriate."
                    ),
                    details={
                        "confidence": round(confidence, 4),
                        "predicted_class": predicted_class,
                    },
                )
            )

        return findings
