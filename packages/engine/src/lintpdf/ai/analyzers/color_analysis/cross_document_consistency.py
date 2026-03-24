"""Cross-document color consistency tracking.

GPU-tier analyzer that extracts spot color information from the document
and reports an inventory for cross-document consistency tracking.  Tracks
spot color Lab values across submissions from the same tenant to enable
drift detection over time.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.gpu_client import GPUInferenceClient, GPUServiceUnavailableError
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)


def _get_gpu_client() -> GPUInferenceClient:
    from lintpdf.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


def _extract_spot_colors(document: SemanticDocument) -> list[dict[str, Any]]:
    """Extract spot color inventory from document color spaces.

    Returns a list of dicts with colorant name, color space type, and
    page numbers where the color appears.
    """
    spot_map: dict[str, dict[str, Any]] = {}

    for page in document.pages:
        for cs_name, cs in page.color_spaces.items():
            if cs.cs_type not in ("Separation", "DeviceN"):
                continue
            if not cs.colorant_names:
                continue

            for colorant in cs.colorant_names:
                if not colorant or colorant in ("All", "None"):
                    continue

                key = colorant.lower()
                if key not in spot_map:
                    spot_map[key] = {
                        "colorant_name": colorant,
                        "color_space_type": cs.cs_type,
                        "pages": [],
                        "color_space_names": [],
                    }

                if page.page_num not in spot_map[key]["pages"]:
                    spot_map[key]["pages"].append(page.page_num)
                if cs_name not in spot_map[key]["color_space_names"]:
                    spot_map[key]["color_space_names"].append(cs_name)

    return list(spot_map.values())


@register_ai_analyzer
class CrossDocumentConsistencyAnalyzer(BaseAIAnalyzer):
    """Track spot color inventory for cross-document consistency analysis."""

    category = "color_analysis"
    feature_slug = "cross_document_consistency"
    tier = "gpu"
    credits_per_run = 2

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        findings: list[Finding] = []
        spot_colors = _extract_spot_colors(document)

        if not spot_colors:
            return findings

        # Attempt GPU-based Lab value extraction for more precise tracking
        lab_values: dict[str, dict[str, float]] = {}
        try:
            from lintpdf.ai.rendering import render_all_pages

            page_images = render_all_pages(pdf_bytes, dpi=150)
            gpu = _get_gpu_client()

            if page_images:
                try:
                    result = gpu._post("/inference/extract-lab", page_images[0])
                    lab_values = result.get("lab_values", {})
                except GPUServiceUnavailableError:
                    logger.debug("cross_document_consistency: GPU unavailable for Lab extraction")
        except RuntimeError:
            logger.debug("cross_document_consistency: PDF rendering backend unavailable")

        # Build spot color inventory summary
        color_names = [sc["colorant_name"] for sc in spot_colors]
        summary = ", ".join(color_names)

        # Enrich spot colors with Lab values if available
        for sc in spot_colors:
            key = sc["colorant_name"].lower()
            if key in lab_values:
                sc["lab"] = lab_values[key]

        findings.append(
            self._make_finding(
                inspection_id="LPDF_AI_CDCC_001",
                severity=Severity.ADVISORY,
                message=(
                    f"Spot color inventory for cross-document tracking: {summary} "
                    f"({len(spot_colors)} spot color(s) found)"
                ),
                details={
                    "spot_colors": spot_colors,
                    "total_spot_colors": len(spot_colors),
                    "lab_values_available": bool(lab_values),
                },
            )
        )

        return findings
