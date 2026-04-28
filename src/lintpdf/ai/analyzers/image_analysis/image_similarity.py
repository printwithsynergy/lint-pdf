"""Image similarity search analyzer — GPU-based visual embedding comparison.

Uses DINOv2 on the GPU inference service to generate image embeddings for
each page, enabling downstream visual similarity search against an index
of known artwork.  Reports embedding metadata as ADVISORY findings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.gpu_client import (
    GPUInferenceClient,
    GPUServiceNotConfiguredError,
    GPUServiceRateLimitedError,
    GPUServiceUnavailableError,
)
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)


def _get_gpu_client() -> GPUInferenceClient:
    # Delegates to the process-level shared client so the circuit breaker
    # accumulates failures across analyzers (see gpu_client.get_gpu_client).
    from lintpdf.ai.gpu_client import get_gpu_client

    return get_gpu_client()


@register_ai_analyzer
class ImageSimilarityAnalyzer(BaseAIAnalyzer):
    """Generate visual embeddings for similarity search across documents."""

    category = "image_analysis"
    feature_slug = "image_similarity_search"
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
            logger.debug("image_similarity: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
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
