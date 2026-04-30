"""Safe zone violations analyzer — GPU-based object detection for margin safety.

Uses Grounding DINO on the GPU inference service to detect text, logos, and
barcodes, then checks whether any detected object falls within the configured
safe zone margin.  Objects encroaching the safe zone trigger WARNING findings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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

# Conversion constant: 1 mm = 2.8346 points at 72 dpi
_MM_TO_PT = 2.8346


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

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 beta-stream: SaaS coupling routed through ctx.services.
        document = ctx.document
        pdf_bytes = ctx.pdf_bytes
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        services = ctx.services
        if services is None or services.gpu_client is None or services.renderer is None:
            logger.debug("safe_zone_violations: ctx.services unavailable, skipping")
            return []

        # Get safe zone margin in mm, convert to points
        safe_zone_mm = 3.0
        if ai_config is not None:
            safe_zone_mm = float(getattr(ai_config, "default_safe_zone_mm", 3.0) or 3.0)
        safe_zone_pt = safe_zone_mm * _MM_TO_PT

        render_dpi = 200

        try:
            page_images = services.renderer.render_all_pages(pdf_bytes, dpi=render_dpi)
        except RuntimeError:
            logger.debug("safe_zone_violations: PDF rendering backend unavailable")
            return []

        gpu = services.gpu_client
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

            # DINO call now asks only for "logo." and "barcode." — text bbox
            # detection is served from the orchestrator's shared OCR pass via
            # ``page.detected_text_regions``. One fewer GPU call per page.
            try:
                result = gpu.detect_objects(png_bytes, prompt="logo. barcode.")
            except (GPUServiceNotConfiguredError, GPUServiceRateLimitedError):
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

            detections = list(result.get("detections", []))
            image_width = float(result.get("image_width", 1))
            image_height = float(result.get("image_height", 1))

            # Splice in text-region detections from the shared OCR pass.
            # The pass already converted to PDF points, so we round-trip back
            # to pixel space via the same scale_x/scale_y the loop below expects.
            page_obj_ts = (
                document.pages[page_idx]
                if document.pages and page_idx < len(document.pages)
                else None
            )
            if page_obj_ts is not None and page_obj_ts.detected_text_regions:
                # Inverse-scale PDF points back to pixel space so the existing
                # loop can keep its pixel-space arithmetic. Tiny indirection
                # but avoids a second loop body for one detection family.
                inv_sx = image_width / page_width_pt if page_width_pt else 1.0
                inv_sy = image_height / page_height_pt if page_height_pt else 1.0
                for region in page_obj_ts.detected_text_regions:
                    bx0 = region.bbox.x0 * inv_sx
                    by1 = (page_height_pt - region.bbox.y0) * inv_sy
                    bx1 = region.bbox.x1 * inv_sx
                    by0 = (page_height_pt - region.bbox.y1) * inv_sy
                    detections.append(
                        {
                            "label": "text",
                            "confidence": region.confidence,
                            "bbox": [bx0, min(by0, by1), bx1, max(by0, by1)],
                        }
                    )

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
