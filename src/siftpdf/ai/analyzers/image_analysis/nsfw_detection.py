"""NSFW content detection analyzer — GPU-based explicit content screening.

Uses NudeNet on the GPU inference service to detect inappropriate content
in PDF page images.  Explicit content triggers an ERROR finding; suggestive
content triggers a WARNING finding.
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


@register_ai_analyzer
class NSFWDetectionAnalyzer(BaseAIAnalyzer):
    """Detect NSFW / explicit content in PDF page images."""

    category = "image_analysis"
    feature_slug = "nsfw_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 beta-stream: SaaS coupling routed through ctx.services.
        pdf_bytes = ctx.pdf_bytes

        services = ctx.services
        if services is None or services.gpu_client is None or services.renderer is None:
            logger.debug("nsfw_detection: ctx.services unavailable, skipping")
            return []

        try:
            page_images = services.renderer.render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("nsfw_detection: PDF rendering backend unavailable")
            return []

        gpu = services.gpu_client
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu.detect_nsfw(png_bytes)
            except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
                logger.debug("nsfw_detection: GPU service not configured, skipping")
                return findings
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
