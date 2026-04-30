"""Image quality assessment analyzer — GPU-based perceptual quality scoring.

Uses MUSIQ/TOPIQ models on the GPU inference service to assign a perceptual
quality score (0-100) to each raster image embedded in the PDF.  Images below
the tenant's configured minimum score threshold generate a WARNING finding.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.ai.types import (
    GPUServiceNotConfiguredError,
    GPUServiceRateLimitedError,
    GPUServiceUnavailableError,
)
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)


@register_ai_analyzer
class ImageQualityAnalyzer(BaseAIAnalyzer):
    """Assess perceptual quality of raster images embedded in the PDF."""

    category = "image_analysis"
    feature_slug = "image_quality_assessment"
    tier = "gpu"
    credits_per_run = 2

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 beta-stream: SaaS coupling routed through ctx.services.
        pdf_bytes = ctx.pdf_bytes
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        services = ctx.services
        if services is None or services.gpu_client is None or services.renderer is None:
            logger.debug("image_quality: ctx.services unavailable, skipping")
            return []

        min_score = 50
        if ai_config is not None:
            min_score = int(getattr(ai_config, "min_image_quality_score", 50) or 50)

        try:
            page_images = services.renderer.render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("image_quality: PDF rendering backend unavailable")
            return []

        gpu = services.gpu_client
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu.assess_image_quality(png_bytes)
            except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
                logger.debug("image_quality: GPU service not configured, skipping")
                return findings
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
