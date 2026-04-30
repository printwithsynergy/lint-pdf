"""Regulatory symbol detection analyzer — GPU-based symbol recognition.

Uses a trained symbol detection model on the GPU inference service to identify
regulatory, recycling, and certification symbols (e.g. CE, FDA, recycling
arrows, kosher, halal).  Undersized symbols generate a WARNING finding;
successfully detected symbols are reported as ADVISORY.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.ai.types import GPUInferenceClient, GPUServiceUnavailableError
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)

# Minimum symbol dimensions in mm (per common regulatory requirements)
_MIN_SYMBOL_SIZE_MM: dict[str, float] = {
    "ce_mark": 5.0,
    "recycling": 6.0,
    "fda": 5.0,
    "green_dot": 10.0,
    "tidyman": 10.0,
    "mobius_loop": 6.0,
    "kosher": 3.0,
    "halal": 3.0,
}
_DEFAULT_MIN_SIZE_MM = 5.0

# 1 mm = 2.8346 points
_MM_TO_PT = 2.8346

# Known regulatory symbol categories
_REGULATORY_SYMBOLS = [
    "recycling_mobius",
    "recycling_resin_codes",
    "ce_marking",
    "green_dot",
    "tidyman",
    "fsc",
    "pefc",
    "rainforest_alliance",
    "fairtrade",
    "eu_organic",
    "ghs_pictogram",
    "dot_hazmat",
    "kosher",
    "halal",
    "non_gmo",
    "usda_organic",
]

# Industry-to-expected-symbols mapping
_INDUSTRY_EXPECTED_SYMBOLS: dict[str, list[str]] = {
    "food": ["recycling_mobius", "tidyman"],
    "beverage": ["recycling_mobius", "recycling_resin_codes", "tidyman"],
    "pharmaceutical": ["recycling_mobius", "ce_marking"],
    "cosmetics": ["recycling_mobius", "tidyman"],
    "chemical": ["ghs_pictogram", "recycling_mobius"],
    "electronics": ["ce_marking", "recycling_mobius"],
}


def _get_gpu_client() -> GPUInferenceClient:
    # Delegates to the process-level shared client so the circuit breaker
    # accumulates failures across analyzers (see gpu_client.get_gpu_client).
    from lintpdf.ai.types import get_gpu_client

    return get_gpu_client()


@register_ai_analyzer
class RegulatorySymbolDetectionAnalyzer(BaseAIAnalyzer):
    """Detect regulatory and recycling symbols and check their sizing."""

    category = "symbol_detection"
    feature_slug = "regulatory_symbol_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses document
        # + pdf_bytes + ai_config (.industry_type). Reconstituted
        # via _reconstitute_ai_config to preserve attribute access.
        document = ctx.document
        pdf_bytes = ctx.pdf_bytes
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        from lintpdf.ai.rendering import render_all_pages

        render_dpi = 200
        try:
            page_images = render_all_pages(pdf_bytes, dpi=render_dpi)
        except RuntimeError:
            logger.debug("regulatory_symbols: PDF rendering backend unavailable")
            return []

        gpu = _get_gpu_client()
        findings: list[Finding] = []

        # Determine which symbols are expected based on industry
        expected_symbols: list[str] = []
        if ai_config and ai_config.industry_type:
            expected_symbols = _INDUSTRY_EXPECTED_SYMBOLS.get(ai_config.industry_type, [])

        all_detected_types: set[str] = set()

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1

            # Get page dimensions for size calculation
            page_width_pt = 612.0
            page_height_pt = 792.0
            if document.pages and page_idx < len(document.pages):
                page_obj = document.pages[page_idx]
                if hasattr(page_obj, "width_pt") and page_obj.width_pt:
                    page_width_pt = float(page_obj.width_pt)
                if hasattr(page_obj, "height_pt") and page_obj.height_pt:
                    page_height_pt = float(page_obj.height_pt)

            try:
                result = gpu.detect_symbols(png_bytes)
            except GPUServiceUnavailableError as exc:
                # GPU inference is an infrastructure dependency, not a PDF
                # quality signal. When it's rate-limited (429) or down, we
                # silently bail out of this analyzer — the orchestrator's
                # AI_SCAN_001 audit marker still records that the scan ran,
                # and a separate ops signal will surface the GPU outage.
                # Emitting a per-page finding just pollutes the reviewer's
                # queue with noise they can't act on.
                logger.warning(
                    "GPU service unavailable for regulatory symbol detection "
                    "on page %d: %s — skipping analyzer",
                    page_num,
                    exc,
                )
                return findings

            detections = result.get("detections", [])
            image_width = float(result.get("image_width", 1))
            image_height = float(result.get("image_height", 1))

            for detection in detections:
                label = detection.get("label", "unknown_symbol")
                confidence = float(detection.get("confidence", 0))
                bbox_raw = detection.get("bbox", [])

                if len(bbox_raw) != 4 or confidence < 0.3:
                    continue

                all_detected_types.add(label)
                x0_px, y0_px, x1_px, y1_px = (float(v) for v in bbox_raw)

                # Scale to page points
                scale_x = page_width_pt / image_width if image_width else 1.0
                scale_y = page_height_pt / image_height if image_height else 1.0

                x0_pt = x0_px * scale_x
                y0_pt = y0_px * scale_y
                x1_pt = x1_px * scale_x
                y1_pt = y1_px * scale_y

                width_pt = x1_pt - x0_pt
                height_pt = y1_pt - y0_pt
                width_mm = width_pt / _MM_TO_PT
                height_mm = height_pt / _MM_TO_PT

                # Use the smaller dimension for minimum size check
                actual_size_mm = min(width_mm, height_mm)
                min_size_mm = _MIN_SYMBOL_SIZE_MM.get(
                    label.lower().replace(" ", "_"), _DEFAULT_MIN_SIZE_MM
                )

                bbox = (x0_pt, y0_pt, x1_pt, y1_pt)

                if actual_size_mm < min_size_mm:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_RSYM_002",
                            severity=Severity.WARNING,
                            message=(
                                f"Regulatory symbol '{label}' on page {page_num} "
                                f"is undersized ({actual_size_mm:.1f}mm, "
                                f"minimum: {min_size_mm:.1f}mm)"
                            ),
                            page_num=page_num,
                            details={
                                "symbol": label,
                                "confidence": round(confidence, 4),
                                "width_mm": round(width_mm, 2),
                                "height_mm": round(height_mm, 2),
                                "actual_min_dimension_mm": round(actual_size_mm, 2),
                                "required_min_mm": min_size_mm,
                            },
                            bbox=bbox,
                            object_type="symbol",
                        )
                    )
                else:
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_RSYM_003",
                            severity=Severity.ADVISORY,
                            message=(
                                f"Regulatory symbol '{label}' detected on "
                                f"page {page_num} (confidence: {confidence:.0%}, "
                                f"size: {actual_size_mm:.1f}mm)"
                            ),
                            page_num=page_num,
                            details={
                                "symbol": label,
                                "confidence": round(confidence, 4),
                                "width_mm": round(width_mm, 2),
                                "height_mm": round(height_mm, 2),
                                "actual_min_dimension_mm": round(actual_size_mm, 2),
                                "required_min_mm": min_size_mm,
                            },
                            bbox=bbox,
                            object_type="symbol",
                        )
                    )

        # Check for expected but missing symbols
        for expected in expected_symbols:
            if expected not in all_detected_types:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_RSYM_004",
                        severity=Severity.WARNING,
                        message=(
                            f"Expected regulatory symbol '{expected}' was not "
                            f"detected in the document"
                        ),
                        details={
                            "expected_symbol": expected,
                            "industry_type": (ai_config.industry_type if ai_config else None),
                            "detected_symbols": sorted(all_detected_types),
                        },
                    )
                )

        return findings
