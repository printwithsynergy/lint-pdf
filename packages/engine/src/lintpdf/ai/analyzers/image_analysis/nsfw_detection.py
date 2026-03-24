"""NSFW content detection analyzer — GPU-based explicit content screening.

Uses NudeNet on the GPU inference service to detect inappropriate content
in PDF page images.  Explicit content triggers an ERROR finding; suggestive
content triggers a WARNING finding.
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

# Classification labels from NudeNet mapped to severity tiers
_EXPLICIT_LABELS = frozenset(
    {
        "EXPLICIT_NUDITY",
        "EXPLICIT",
        "NUDE",
        "SEXUAL_ACTIVITY",
    }
)
_SUGGESTIVE_LABELS = frozenset(
    {
        "SUGGESTIVE",
        "PARTIAL_NUDITY",
        "REVEALING",
        "UNDERWEAR",
    }
)


def _get_gpu_client() -> GPUInferenceClient:
    from lintpdf.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


@register_ai_analyzer
class NSFWDetectionAnalyzer(BaseAIAnalyzer):
    """Detect NSFW / explicit content in PDF page images."""

    category = "image_analysis"
    feature_slug = "nsfw_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
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
            logger.debug("nsfw_detection: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu.detect_nsfw(png_bytes)
            except GPUServiceUnavailableError as exc:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_NSFW_001",
                        severity=Severity.ADVISORY,
                        message=(f"GPU inference service unavailable for NSFW detection: {exc}"),
                        page_num=page_num,
                        details={"reason": "gpu_unavailable"},
                    )
                )
                return findings

            detections = result.get("detections", [])
            for detection in detections:
                label = detection.get("label", "").upper()
                confidence = float(detection.get("confidence", 0))
                bbox_raw = detection.get("bbox")
                bbox = (
                    tuple(float(v) for v in bbox_raw) if bbox_raw and len(bbox_raw) == 4 else None
                )

                if label in _EXPLICIT_LABELS and confidence >= 0.5:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_NSFW_002",
                            severity=Severity.ERROR,
                            message=(
                                f"Explicit content detected on page {page_num} "
                                f"(label: {label}, confidence: {confidence:.0%})"
                            ),
                            page_num=page_num,
                            details={
                                "label": label,
                                "confidence": round(confidence, 4),
                                "category": "explicit",
                            },
                            bbox=bbox,  # type: ignore[arg-type]
                            object_type="image",
                        )
                    )
                elif label in _SUGGESTIVE_LABELS and confidence >= 0.6:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_NSFW_003",
                            severity=Severity.WARNING,
                            message=(
                                f"Suggestive content detected on page {page_num} "
                                f"(label: {label}, confidence: {confidence:.0%})"
                            ),
                            page_num=page_num,
                            details={
                                "label": label,
                                "confidence": round(confidence, 4),
                                "category": "suggestive",
                            },
                            bbox=bbox,  # type: ignore[arg-type]
                            object_type="image",
                        )
                    )

        return findings
