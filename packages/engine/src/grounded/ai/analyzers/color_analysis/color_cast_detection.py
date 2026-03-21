"""Color cast detection using Gray World algorithm and CLIP-IQA.

GPU-tier analyzer that detects unwanted color casts in rendered PDF pages
by combining the Gray World assumption (statistical analysis of channel
means) with CLIP-IQA perceptual quality assessment for color accuracy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from grounded.ai.base import BaseAIAnalyzer
from grounded.ai.gpu_client import GPUInferenceClient, GPUServiceUnavailableError
from grounded.ai.registry import register_ai_analyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.api.models import TenantAIConfig
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Cast severity thresholds (deviation from neutral)
_SIGNIFICANT_CAST_THRESHOLD = 15.0  # Channel mean deviation above this is significant
_MILD_CAST_THRESHOLD = 8.0  # Above this but below significant is mild


def _get_gpu_client() -> GPUInferenceClient:
    from grounded.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


def _describe_cast_direction(dominant_channel: str) -> str:
    """Return a human-readable description of the cast direction."""
    descriptions: dict[str, str] = {
        "red": "warm/red",
        "green": "green",
        "blue": "cool/blue",
        "yellow": "yellow (red+green)",
        "cyan": "cyan (green+blue)",
        "magenta": "magenta (red+blue)",
    }
    return descriptions.get(dominant_channel, dominant_channel)


@register_ai_analyzer
class ColorCastDetectionAnalyzer(BaseAIAnalyzer):
    """Detect unwanted color casts using Gray World and CLIP-IQA analysis."""

    category = "color_analysis"
    feature_slug = "color_cast_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        from grounded.ai.rendering import render_all_pages

        try:
            page_images = render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("color_cast_detection: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu._post("/inference/color-cast", png_bytes)
            except GPUServiceUnavailableError:
                logger.debug("color_cast_detection: GPU service unavailable, skipping")
                return []

            deviation = float(result.get("max_deviation", 0.0))
            deviation = round(deviation, 2)
            dominant_channel: str = result.get("dominant_channel", "unknown")
            clip_iqa_score = float(result.get("clip_iqa_score", 1.0))
            cast_direction = _describe_cast_direction(dominant_channel)

            if deviation >= _SIGNIFICANT_CAST_THRESHOLD:
                findings.append(
                    self._make_finding(
                        inspection_id="GRD_AI_CAST_001",
                        severity=Severity.SQUALL,
                        message=(
                            f"Significant color cast detected on page {page_num}: "
                            f"{cast_direction} cast (deviation {deviation}, "
                            f"CLIP-IQA score {clip_iqa_score:.2f})"
                        ),
                        page_num=page_num,
                        details={
                            "max_deviation": deviation,
                            "dominant_channel": dominant_channel,
                            "cast_direction": cast_direction,
                            "clip_iqa_score": round(clip_iqa_score, 3),
                            "threshold": _SIGNIFICANT_CAST_THRESHOLD,
                            "channel_means": result.get("channel_means", {}),
                        },
                        object_type="image",
                    )
                )
            elif deviation >= _MILD_CAST_THRESHOLD:
                findings.append(
                    self._make_finding(
                        inspection_id="GRD_AI_CAST_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Mild color cast detected on page {page_num}: "
                            f"{cast_direction} cast (deviation {deviation})"
                        ),
                        page_num=page_num,
                        details={
                            "max_deviation": deviation,
                            "dominant_channel": dominant_channel,
                            "cast_direction": cast_direction,
                            "clip_iqa_score": round(clip_iqa_score, 3),
                            "threshold": _MILD_CAST_THRESHOLD,
                            "channel_means": result.get("channel_means", {}),
                        },
                        object_type="image",
                    )
                )

        return findings
