"""Color cast detection using Gray World algorithm and CLIP-IQA.

GPU-tier analyzer that detects unwanted color casts in rendered PDF pages
by combining the Gray World assumption (statistical analysis of channel
means) with CLIP-IQA perceptual quality assessment for color accuracy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.ai.types import GPUInferenceClient, GPUServiceUnavailableError
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)

# Cast severity thresholds (deviation from neutral)
_SIGNIFICANT_CAST_THRESHOLD = 15.0  # Channel mean deviation above this is significant
_MILD_CAST_THRESHOLD = 8.0  # Above this but below significant is mild


def _get_gpu_client() -> GPUInferenceClient:
    # Delegates to the process-level shared client so the circuit breaker
    # accumulates failures across analyzers (see gpu_client.get_gpu_client).
    from lintpdf.ai.types import get_gpu_client

    return get_gpu_client()


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

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 α-stream: signature migration. Internal globals
        # (_get_gpu_client, lazy lintpdf.ai.rendering import,
        # lintpdf.ai.text_mask import) intentionally unchanged in
        # α — they migrate to ctx.services.gpu_client in β-stream.
        # ai_config parameter was declared but never used; dropped.
        document = ctx.document
        pdf_bytes = ctx.pdf_bytes

        from lintpdf.ai.rendering import render_all_pages

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

            # PR C Slot 3A: when the page is text-heavy (>40 % of area
            # covered by detected text), channel-mean deviations are
            # often artefacts of text-stroke edge antialiasing rather
            # than real color casts. Demote severity by one level.
            text_density = 0.0
            page_obj = (
                document.pages[page_idx]
                if document.pages and page_idx < len(document.pages)
                else None
            )
            if page_obj is not None:
                from lintpdf.ai.text_mask import text_density_ratio

                text_density = text_density_ratio(page_obj)
            text_heavy = text_density > 0.40

            if deviation >= _SIGNIFICANT_CAST_THRESHOLD and not text_heavy:
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_AI_CAST_001",
                        severity=Severity.WARNING,
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
                            "text_density": round(text_density, 3),
                        },
                        object_type="image",
                    )
                )
            elif deviation >= _SIGNIFICANT_CAST_THRESHOLD and text_heavy:
                # Demote significant→advisory; the deviation is likely an
                # artefact of text-stroke edge sampling.
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_AI_CAST_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Possible color cast on page {page_num}: "
                            f"{cast_direction} cast (deviation {deviation}); "
                            "page is text-heavy so deviation may be a "
                            "text-edge artefact — verify visually"
                        ),
                        page_num=page_num,
                        details={
                            "max_deviation": deviation,
                            "dominant_channel": dominant_channel,
                            "cast_direction": cast_direction,
                            "clip_iqa_score": round(clip_iqa_score, 3),
                            "threshold": _SIGNIFICANT_CAST_THRESHOLD,
                            "channel_means": result.get("channel_means", {}),
                            "text_density": round(text_density, 3),
                            "demoted_for_text_edges": True,
                        },
                        object_type="image",
                    )
                )
            elif deviation >= _MILD_CAST_THRESHOLD and not text_heavy:
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_AI_CAST_001",
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
