"""Logo detection and verification analyzer — GPU-based logo matching.

Uses YOLOv8 + CLIP on the GPU inference service to detect logos in the
document and compare them against the tenant's reference logos.  Missing
expected logos generate a WARNING finding; detected logos are reported as
ADVISORY with match confidence.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from siftpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
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
class LogoDetectionAnalyzer(BaseAIAnalyzer):
    """Detect and verify logos against tenant's reference logo set."""

    category = "logo_verification"
    feature_slug = "logo_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 beta-stream: SaaS coupling routed through ctx.services.
        pdf_bytes = ctx.pdf_bytes
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        services = ctx.services
        if services is None or services.gpu_client is None or services.renderer is None:
            logger.debug("logo_detection: ctx.services unavailable, skipping")
            return []

        # Extract reference logos from tenant AI config
        reference_logos: list[dict[str, Any]] = []
        if ai_config is not None and ai_config.reference_logos:
            reference_logos = list(ai_config.reference_logos)

        try:
            page_images = services.renderer.render_all_pages(pdf_bytes, dpi=200)
        except RuntimeError:
            logger.debug("logo_detection: PDF rendering backend unavailable")
            return []

        gpu = services.gpu_client
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
