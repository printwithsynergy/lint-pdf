"""File classification analyzer — Vision-based document type detection.

Uses DiT (Document Image Transformer) on the Vision inference service to classify
the document type (e.g. packaging artwork, technical drawing, label, leaflet).
Reports the classification result as an ADVISORY finding that downstream
analyzers and the auto_preflight_profile module can consume.
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
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)


def _get_gpu_client() -> GPUInferenceClient:
    # Delegates to the process-level shared client so the circuit breaker
    # accumulates failures across analyzers (see gpu_client.get_gpu_client).
    from lintpdf.ai.types import get_gpu_client

    return get_gpu_client()


@register_ai_analyzer
class FileClassificationAnalyzer(BaseAIAnalyzer):
    """Classify document type using visual document classification model."""

    category = "document_classification"
    feature_slug = "file_classification"
    tier = "gpu"
    credits_per_run = 2

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses pdf_bytes
        # only. document + events + ai_config declared but never used.
        pdf_bytes = ctx.pdf_bytes

        from lintpdf.ai.rendering import render_page_to_image

        # Classify based on the first page (most representative)
        try:
            first_page_png = render_page_to_image(pdf_bytes, page_num=1, dpi=150)
        except RuntimeError:
            logger.debug("file_classification: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()

        try:
            result = gpu.classify_document(first_page_png)
        except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
            logger.debug("file_classification: GPU service not configured, skipping")
            return []
        except GPUServiceUnavailableError as exc:
            return [
                self._make_finding(
                    inspection_id="AI_FCLASS_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"GPU inference service unavailable for document classification: {exc}"
                    ),
                    details={"reason": "gpu_unavailable"},
                )
            ]

        predicted_class = result.get("predicted_class", "unknown")
        confidence = float(result.get("confidence", 0))
        all_scores = result.get("scores", {})

        findings: list[Finding] = [
            self._make_finding(
                inspection_id="AI_FCLASS_002",
                severity=Severity.ADVISORY,
                message=(
                    f"Document classified as '{predicted_class}' (confidence: {confidence:.0%})"
                ),
                details={
                    "predicted_class": predicted_class,
                    "confidence": round(confidence, 4),
                    "all_scores": all_scores,
                    "model": result.get("model", "dit"),
                },
            )
        ]

        # Low-confidence classification warrants a note
        if confidence < 0.5:
            findings.append(
                self._make_finding(
                    inspection_id="AI_FCLASS_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Low confidence in document classification "
                        f"({confidence:.0%}). Document type could not be "
                        f"reliably determined."
                    ),
                    details={
                        "predicted_class": predicted_class,
                        "confidence": round(confidence, 4),
                    },
                )
            )

        return findings
