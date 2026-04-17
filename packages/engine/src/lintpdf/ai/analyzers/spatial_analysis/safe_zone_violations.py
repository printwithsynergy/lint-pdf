"""Safe zone violations analyzer — GPU-based object detection for margin safety.

Uses Grounding DINO on the GPU inference service to detect text, logos, and
barcodes, then checks whether any detected object falls within the configured
safe zone margin.  Objects encroaching the safe zone trigger WARNING findings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.gpu_client import (
    GPUInferenceClient,
    GPUServiceNotConfiguredError,
    GPUServiceUnavailableError,
)
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.api.models import TenantAIConfig
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Conversion constant: 1 mm = 2.8346 points at 72 dpi
_MM_TO_PT = 2.8346


def _get_gpu_client() -> GPUInferenceClient:
    from lintpdf.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


def _px_to_pt(px: float, dpi: int) -> float:
    """Convert pixel coordinate to PDF points."""
    return px * 72.0 / dpi


@register_ai_analyzer
class SafeZoneViolationsAnalyzer(BaseAIAnalyzer):
    """Detect objects that encroach the safe zone margins."""

    category = "spatial_analysis"
    feature_slug = "safe_zone_violations"
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

        # Get safe zone margin in mm, convert to points
        safe_zone_mm = 3.0
        if ai_config is not None:
            safe_zone_mm = float(getattr(ai_config, "default_safe_zone_mm", 3.0) or 3.0)
        safe_zone_pt = safe_zone_mm * _MM_TO_PT

        render_dpi = 200

        try:
            page_images = render_all_pages(pdf_bytes, dpi=render_dpi)
        except RuntimeError:
            logger.debug("safe_zone_violations: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1

            # Determine page dimensions in points from the semantic document
            page_width_pt = 612.0  # default US Letter
            page_height_pt = 792.0
            if document.pages and page_idx < len(document.pages):
                page_obj = document.pages[page_idx]
                if hasattr(page_obj, "width_pt") and page_obj.width_pt:
                    page_width_pt = float(page_obj.width_pt)
                if hasattr(page_obj, "height_pt") and page_obj.height_pt:
                    page_height_pt = float(page_obj.height_pt)

            try:
                result = gpu.detect_objects(png_bytes, prompt="text. logo. barcode.")
            except GPUServiceNotConfiguredError:
                logger.debug("safe_zone_violations: GPU service not configured, skipping")
                return findings
            except GPUServiceUnavailableError as exc:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_SZ_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"GPU inference service unavailable for safe zone analysis: {exc}"
                        ),
                        page_num=page_num,
                        details={"reason": "gpu_unavailable"},
                    )
                )
                return findings

            detections = result.get("detections", [])
            image_width = float(result.get("image_width", 1))
            image_height = float(result.get("image_height", 1))

            for detection in detections:
                label = detection.get("label", "object")
                confidence = float(detection.get("confidence", 0))
                bbox_raw = detection.get("bbox", [])

                if len(bbox_raw) != 4 or confidence < 0.3:
                    continue

                # Convert pixel bbox to points
                x0_px, y0_px, x1_px, y1_px = (float(v) for v in bbox_raw)

                # Scale from image pixel space to page point space
                scale_x = page_width_pt / image_width if image_width else 1.0
                scale_y = page_height_pt / image_height if image_height else 1.0

                x0_pt = x0_px * scale_x
                y0_pt = y0_px * scale_y
                x1_pt = x1_px * scale_x
                y1_pt = y1_px * scale_y

                # Check if any edge of the detected object is within the
                # safe zone margin from the page edge
                violations: list[str] = []
                margins: dict[str, float] = {
                    "left": round(x0_pt, 2),
                    "top": round(y0_pt, 2),
                    "right": round(page_width_pt - x1_pt, 2),
                    "bottom": round(page_height_pt - y1_pt, 2),
                }

                for edge, distance in margins.items():
                    if distance < safe_zone_pt:
                        violations.append(f"{edge} ({distance:.1f}pt, need {safe_zone_pt:.1f}pt)")

                if violations:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_SZ_002",
                            severity=Severity.WARNING,
                            message=(
                                f"'{label}' on page {page_num} encroaches the "
                                f"safe zone ({safe_zone_mm}mm): " + "; ".join(violations)
                            ),
                            page_num=page_num,
                            details={
                                "label": label,
                                "confidence": round(confidence, 4),
                                "bbox_pt": [
                                    round(x0_pt, 2),
                                    round(y0_pt, 2),
                                    round(x1_pt, 2),
                                    round(y1_pt, 2),
                                ],
                                "margins_pt": margins,
                                "safe_zone_mm": safe_zone_mm,
                                "safe_zone_pt": round(safe_zone_pt, 2),
                                "violated_edges": [v.split(" ")[0] for v in violations],
                            },
                            bbox=(x0_pt, y0_pt, x1_pt, y1_pt),
                            object_type=label,
                        )
                    )

        return findings
