"""Banding artifact detection using GPU-based CAMBI algorithm.

Detects visible banding artifacts (contour-like gradients) in raster images
rendered from PDF pages.  Uses the CAMBI (Contrast Aware Multiscale Banding
Index) algorithm via the GPU inference service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from grounded.ai.base import BaseAIAnalyzer
from grounded.ai.gpu_client import GPUInferenceClient, GPUServiceUnavailableError
from grounded.ai.registry import register_ai_analyzer
from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.api.models import TenantAIConfig
    from grounded.semantic.events import ContentStreamEvent
    from grounded.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# CAMBI score thresholds
_BANDING_THRESHOLD = 5.0  # Above this indicates visible banding
_MILD_BANDING_THRESHOLD = 2.0  # Below _BANDING but above this is mild


def _get_gpu_client() -> GPUInferenceClient:
    from grounded.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


@register_ai_analyzer
class BandingDetectionAnalyzer(BaseAIAnalyzer):
    """Detect banding artifacts in PDF page renders using CAMBI algorithm."""

    category = "color_analysis"
    feature_slug = "banding_detection"
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
            logger.debug("banding_detection: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu._post("/inference/cambi", png_bytes)
            except GPUServiceUnavailableError:
                logger.debug("banding_detection: GPU service unavailable, skipping")
                return []

            cambi_score = float(result.get("cambi_score", 0.0))
            cambi_score = round(cambi_score, 3)

            if cambi_score >= _BANDING_THRESHOLD:
                findings.append(
                    self._make_finding(
                        inspection_id="GRD_AI_BAND_001",
                        severity=Severity.WARNING,
                        message=(
                            f"Visible banding detected on page {page_num}: "
                            f"CAMBI score {cambi_score} exceeds threshold "
                            f"({_BANDING_THRESHOLD})"
                        ),
                        page_num=page_num,
                        details={
                            "cambi_score": cambi_score,
                            "threshold": _BANDING_THRESHOLD,
                            "regions": result.get("regions", []),
                        },
                        object_type="image",
                    )
                )
            elif cambi_score >= _MILD_BANDING_THRESHOLD:
                findings.append(
                    self._make_finding(
                        inspection_id="GRD_AI_BAND_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Mild banding detected on page {page_num}: CAMBI score {cambi_score}"
                        ),
                        page_num=page_num,
                        details={
                            "cambi_score": cambi_score,
                            "threshold": _BANDING_THRESHOLD,
                        },
                        object_type="image",
                    )
                )

        return findings
