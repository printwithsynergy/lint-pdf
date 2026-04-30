"""Logo detection and verification analyzer — GPU-based logo matching.

Uses YOLOv8 + CLIP on the GPU inference service to detect logos in the
document and compare them against the tenant's reference logos.  Missing
expected logos generate a WARNING finding; detected logos are reported as
ADVISORY with match confidence.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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
    from lintpdf.ai.types import AIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)


def _get_gpu_client() -> GPUInferenceClient:
    # Delegates to the process-level shared client so the circuit breaker
    # accumulates failures across analyzers (see gpu_client.get_gpu_client).
    from lintpdf.ai.gpu_client import get_gpu_client

    return get_gpu_client()


@register_ai_analyzer
class LogoDetectionAnalyzer(BaseAIAnalyzer):
    """Detect and verify logos against tenant's reference logo set."""

    category = "logo_verification"
    feature_slug = "logo_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: AIConfig = None,
    ) -> list[Finding]:
        from lintpdf.ai.rendering import render_all_pages

        # Extract reference logos from tenant AI config
        reference_logos: list[dict[str, Any]] = []
        if ai_config is not None and ai_config.reference_logos:
            reference_logos = list(ai_config.reference_logos)

        try:
            page_images = render_all_pages(pdf_bytes, dpi=200)
        except RuntimeError:
            logger.debug("logo_detection: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        # Track which reference logos have been matched across all pages
        matched_reference_names: set[str] = set()

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu.detect_logos(
                    png_bytes,
                    reference_embeddings=reference_logos if reference_logos else None,
                )
            except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
                # Either the service isn't configured
                # (LINTPDF_GPU_INFERENCE_URL unset) or we exhausted the
                # retry budget on HTTP 429s — both are transient/infra
                # conditions that no reviewer can act on. Skip silently;
                # the circuit-breaker metrics cover the ops dashboard.
                logger.debug(
                    "logo_detection: GPU service unavailable (unconfigured or rate-limited), skipping"
                )
                return findings
            except GPUServiceUnavailableError as exc:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_LOGO_001",
                        severity=Severity.ADVISORY,
                        message=(f"GPU inference service unavailable for logo detection: {exc}"),
                        page_num=page_num,
                        details={"reason": "gpu_unavailable"},
                    )
                )
                return findings

            detections = result.get("detections", [])
            for detection in detections:
                label = detection.get("label", "unknown")
                confidence = float(detection.get("confidence", 0))
                bbox_raw = detection.get("bbox")
                bbox = (
                    tuple(float(v) for v in bbox_raw) if bbox_raw and len(bbox_raw) == 4 else None
                )
                matched_ref = detection.get("matched_reference")

                if matched_ref:
                    matched_reference_names.add(matched_ref)

                findings.append(
                    self._make_finding(
                        inspection_id="AI_LOGO_002",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Logo detected on page {page_num}: '{label}' "
                            f"(confidence: {confidence:.0%})"
                            + (f", matched reference: '{matched_ref}'" if matched_ref else "")
                        ),
                        page_num=page_num,
                        details={
                            "label": label,
                            "confidence": round(confidence, 4),
                            "matched_reference": matched_ref,
                        },
                        bbox=bbox,  # type: ignore[arg-type]
                        object_type="image",
                    )
                )

        # Check for missing expected logos
        if reference_logos:
            for ref_logo in reference_logos:
                ref_name = ref_logo.get("name", "unnamed")
                required = ref_logo.get("required", True)
                if required and ref_name not in matched_reference_names:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_LOGO_003",
                            severity=Severity.WARNING,
                            message=(
                                f"Expected logo '{ref_name}' was not detected in the document"
                            ),
                            details={
                                "missing_logo": ref_name,
                                "total_reference_logos": len(reference_logos),
                                "matched_logos": sorted(matched_reference_names),
                            },
                        )
                    )

        return findings
