"""File classification analyzer — Vision-based document type detection.

Uses DiT (Document Image Transformer) on the Vision inference service to classify
the document type (e.g. packaging artwork, technical drawing, label, leaflet).
Reports the classification result as an ADVISORY finding that downstream
analyzers and the auto_voyage_plan module can consume.
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


def _get_gpu_client() -> GPUInferenceClient:
    from grounded.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


@register_ai_analyzer
class FileClassificationAnalyzer(BaseAIAnalyzer):
    """Classify document type using visual document classification model."""

    category = "document_classification"
    feature_slug = "file_classification"
    tier = "gpu"
    credits_per_run = 2

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        from grounded.ai.rendering import render_page_to_image

        # Classify based on the first page (most representative)
        try:
            first_page_png = render_page_to_image(pdf_bytes, page_num=1, dpi=150)
        except RuntimeError:
            logger.debug("file_classification: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()

        try:
            result = gpu.classify_document(first_page_png)
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
