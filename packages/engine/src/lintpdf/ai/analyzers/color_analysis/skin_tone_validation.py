"""Skin tone validation using Monk Skin Tone Scale classification.

GPU-tier analyzer that detects skin regions in rendered PDF pages and
classifies them on the Monk Skin Tone (MST) Scale, then assesses whether
the reproduction falls within the pleasing color range for each detected
tone.
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


def _format_skin_tone_summary(detections: list[dict[str, Any]]) -> str:
    """Format detected skin tones into a human-readable summary."""
    if not detections:
        return "No skin tone regions detected."

    parts: list[str] = []
    for det in detections:
        mst_level = det.get("mst_level", "unknown")
        confidence = det.get("confidence", 0.0)
        in_range = det.get("in_pleasing_range", True)
        status = "within pleasing range" if in_range else "outside pleasing range"
        parts.append(f"MST-{mst_level} ({confidence:.0%} confidence, {status})")

    return "; ".join(parts)


@register_ai_analyzer
class SkinToneValidationAnalyzer(BaseAIAnalyzer):
    """Validate skin tone reproduction using Monk Skin Tone Scale classification."""

    category = "color_analysis"
    feature_slug = "skin_tone_validation"
    tier = "gpu"
    credits_per_run = 2

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        from lintpdf.ai.rendering import render_all_pages

        try:
            page_images = render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("skin_tone_validation: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu._post("/inference/skin-tone", png_bytes)
            except GPUServiceUnavailableError:
                logger.debug("skin_tone_validation: GPU service unavailable, skipping")
                return []

            detections: list[dict[str, Any]] = result.get("detections", [])
            if not detections:
                continue

            summary = _format_skin_tone_summary(detections)
            out_of_range = [d for d in detections if not d.get("in_pleasing_range", True)]

            findings.append(
                self._make_finding(
                    inspection_id="LPDF_AI_SKIN_001",
                    severity=Severity.ADVISORY,
                    message=(f"Skin tone analysis for page {page_num}: {summary}"),
                    page_num=page_num,
                    details={
                        "detections": detections,
                        "total_skin_regions": len(detections),
                        "out_of_pleasing_range": len(out_of_range),
                        "mst_levels_found": [d.get("mst_level") for d in detections],
                    },
                    object_type="image",
                )
            )

        return findings
