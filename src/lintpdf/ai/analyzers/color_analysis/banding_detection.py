"""Banding artifact detection using GPU-based CAMBI algorithm.

Detects visible banding artifacts (contour-like gradients) in raster images
rendered from PDF pages.  Uses the CAMBI (Contrast Aware Multiscale Banding
Index) algorithm via the GPU inference service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.ai.base import BaseAIAnalyzer
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.ai.types import GPUServiceUnavailableError
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)

# CAMBI score thresholds
_BANDING_THRESHOLD = 5.0  # Above this indicates visible banding
_MILD_BANDING_THRESHOLD = 2.0  # Below _BANDING but above this is mild


@register_ai_analyzer
class BandingDetectionAnalyzer(BaseAIAnalyzer):
    """Detect banding artifacts in PDF page renders using CAMBI algorithm."""

    category = "color_analysis"
    feature_slug = "banding_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        # Phase 2 beta-stream: SaaS coupling routed through
        # ctx.services. _get_gpu_client() and lazy lintpdf.ai.rendering
        # imports replaced with ctx.services.gpu_client and
        # ctx.services.renderer respectively. text_mask remains a
        # direct import (CPU-only helper, not SaaS-coupled — η6
        # tracks it but it doesn't need a Service).
        document = ctx.document
        pdf_bytes = ctx.pdf_bytes

        services = ctx.services
        if services is None or services.gpu_client is None or services.renderer is None:
            logger.debug("banding_detection: ctx.services unavailable, skipping")
            return []

        try:
            page_images = services.renderer.render_all_pages(pdf_bytes, dpi=150)
        except RuntimeError:
            logger.debug("banding_detection: PDF rendering backend unavailable")
            return []

        gpu = services.gpu_client
        findings: list[Finding] = []

        for page_idx, png_bytes in enumerate(page_images):
            page_num = page_idx + 1
            try:
                result = gpu._post("/inference/cambi", png_bytes)
            except GPUServiceUnavailableError:
                logger.debug("banding_detection: GPU service unavailable, skipping")
                return []

            cambi_score = float(result.get("cambi_score", 0.0))
            cambi_score = round(cambi_score, 3)

            # PR C Slot 3A: filter regions overlapping detected text,
            # which often gets misread as banding by CAMBI on small
            # label copy edges. If the bulk of flagged regions sit
            # inside text boxes, demote/suppress the finding.
            page_obj = (
                document.pages[page_idx]
                if document.pages and page_idx < len(document.pages)
                else None
            )
            raw_regions = result.get("regions", [])
            kept_regions, dropped = (raw_regions, 0)
            if page_obj is not None:
                from lintpdf.ai.text_mask import filter_regions_by_text_mask

                kept_regions, dropped = filter_regions_by_text_mask(raw_regions, page_obj, dpi=150)
            text_dominated = (
                isinstance(raw_regions, list)
                and len(raw_regions) > 0
                and dropped >= max(1, int(0.7 * len(raw_regions)))
            )

            if cambi_score >= _BANDING_THRESHOLD and not text_dominated:
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_AI_BAND_001",
                        severity=Severity.WARNING,
                        message=(
                            f"Visible banding detected on page {page_num}: "
                            f"CAMBI score {cambi_score} exceeds threshold "
                            f"({_BANDING_THRESHOLD})"
                        ),
                        page_num=page_num,
                        details={
                            "cambi_score": cambi_score,
                            "threshold": _BANDING_THRESHOLD,
                            "regions": kept_regions,
                            "regions_dropped_text_mask": dropped,
                        },
                        object_type="image",
                    )
                )
            elif cambi_score >= _MILD_BANDING_THRESHOLD:
                findings.append(
                    self._make_finding(
                        inspection_id="LPDF_AI_BAND_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Mild banding detected on page {page_num}: CAMBI score {cambi_score}"
                        ),
                        page_num=page_num,
                        details={
                            "cambi_score": cambi_score,
                            "threshold": _BANDING_THRESHOLD,
                        },
                        object_type="image",
                    )
                )

        return findings
