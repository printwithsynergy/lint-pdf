"""Image similarity search analyzer — GPU-based visual embedding comparison.

Uses DINOv2 on the GPU inference service to generate image embeddings for
each page, enabling downstream visual similarity search against an index
of known artwork.  Reports embedding metadata as ADVISORY findings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from siftpdf.ai.base import BaseAIAnalyzer
from siftpdf.ai.registry import register_ai_analyzer
from siftpdf.ai.types import (
    GPUServiceNotConfiguredError,
    GPUServiceRateLimitedError,
    GPUServiceUnavailableError,
)
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)


@register_ai_analyzer
class ImageSimilarityAnalyzer(BaseAIAnalyzer):
    """Generate visual embeddings for similarity search across documents."""

    category = "image_analysis"
    feature_slug = "image_similarity_search"
    tier = "gpu"
    credits_per_run = 2

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 beta-stream: SaaS coupling routed through ctx.services.
        pdf_bytes = ctx.pdf_bytes

        services = ctx.services
        if services is None or services.gpu_client is None or services.renderer is None:
            logger.debug("image_similarity: ctx.services unavailable, skipping")
            return []

        try:
            page_images = services.renderer.render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("image_similarity: PDF rendering backend unavailable")
            return []

        gpu = services.gpu_client
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu.embed_image(png_bytes)
            except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
                logger.debug("image_similarity: GPU service not configured, skipping")
                return findings
            except GPUServiceUnavailableError as exc:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_SIM_001",
                        severity=Severity.ADVISORY,
                        message=(
                            "GPU inference service unavailable for image "
                            f"similarity embedding: {exc}"
                        ),
                        page_num=page_num,
                        details={"reason": "gpu_unavailable"},
                    )
                )
                return findings

            embedding = result.get("embedding", [])
            embedding_dim = len(embedding) if isinstance(embedding, list) else 0
            model_name = result.get("model", "dinov2")

            # Store embedding dimension and model info as advisory finding.
            # The actual similarity matching is performed by the orchestrator
            # against the tenant's artwork index.
            findings.append(
                self._make_finding(
                    inspection_id="AI_SIM_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Generated visual embedding for page {page_num} "
                        f"({embedding_dim}-dimensional, model: {model_name})"
                    ),
                    page_num=page_num,
                    details={
                        "embedding_dim": embedding_dim,
                        "model": model_name,
                        "embedding": embedding,
                    },
                    object_type="image",
                )
            )

        return findings
