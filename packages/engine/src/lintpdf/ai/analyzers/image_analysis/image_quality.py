"""Image quality assessment analyzer — GPU-based perceptual quality scoring.

Uses MUSIQ/TOPIQ models on the GPU inference service to assign a perceptual
quality score (0-100) to each raster image embedded in the PDF.  Images below
the tenant's configured minimum score threshold generate a WARNING finding.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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


@register_ai_analyzer
class ImageQualityAnalyzer(BaseAIAnalyzer):
    """Assess perceptual quality of raster images embedded in the PDF."""

    category = "image_analysis"
    feature_slug = "image_quality_assessment"
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

        min_score = 50
        if ai_config is not None:
            min_score = int(getattr(ai_config, "min_image_quality_score", 50) or 50)

        try:
            page_images = render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("image_quality: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu.assess_image_quality(png_bytes)
            except GPUServiceUnavailableError as exc:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_IQ_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"GPU inference service unavailable for image quality assessment: {exc}"
                        ),
                        page_num=page_num,
                        details={"reason": "gpu_unavailable"},
                    )
                )
                return findings  # No point continuing if GPU is down

            score = float(result.get("score", 0))
            score = round(score, 2)

            if score < min_score:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_IQ_002",
                        severity=Severity.WARNING,
                        message=(
                            f"Page {page_num} image quality score {score} is below "
                            f"minimum threshold ({min_score})"
                        ),
                        page_num=page_num,
                        details={
                            "quality_score": score,
                            "min_threshold": min_score,
                            "model": result.get("model", "unknown"),
                        },
                        object_type="image",
                    )
                )
            else:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_IQ_003",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Page {page_num} image quality score: {score} (threshold: {min_score})"
                        ),
                        page_num=page_num,
                        details={
                            "quality_score": score,
                            "min_threshold": min_score,
                            "model": result.get("model", "unknown"),
                        },
                        object_type="image",
                    )
                )

        return findings
