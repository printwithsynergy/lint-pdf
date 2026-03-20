"""Text-as-outlines detection analyzer — hybrid PDF structure + GPU OCR.

Detects text that has been converted to outlines (paths) in the PDF by
combining two approaches:

1. **PDF structure analysis (CPU):** Scans for pages that have many path
   objects but little or no extractable text — a hallmark of outlined text.
2. **GPU OCR verification:** Renders suspect pages and runs OCR via the GPU
   inference service to confirm that visible text exists as paths rather
   than font glyphs.

Outlined text that should be live text generates a SQUALL finding.
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

# Thresholds for heuristic detection
_MIN_PATH_COUNT_FOR_SUSPECT = 50  # Pages with many paths but no text
_MAX_TEXT_CHARS_FOR_SUSPECT = 10  # Negligible extractable text


def _get_gpu_client() -> GPUInferenceClient:
    from grounded.api.config import get_settings

    settings = get_settings()
    return GPUInferenceClient(settings.gpu_inference_url)


def _count_path_and_text_events(events: list[ContentStreamEvent], page_num: int) -> tuple[int, int]:
    """Count path painting events and text characters on a page."""
    from grounded.semantic.events import PathPaintingEvent, TextRenderedEvent

    path_count = 0
    text_char_count = 0

    for event in events:
        if event.page_num != page_num:
            continue
        if isinstance(event, PathPaintingEvent):
            path_count += 1
        elif isinstance(event, TextRenderedEvent):
            text_char_count += len(getattr(event, "text", "") or "")

    return path_count, text_char_count


def _extract_page_text(document: SemanticDocument, page_num: int) -> str:
    """Extract any text content from a specific page."""
    for page in document.pages:
        if page.page_num == page_num:
            if hasattr(page, "text_content") and page.text_content:
                return str(page.text_content)
            if hasattr(page, "content_stream") and page.content_stream:
                raw = page.content_stream
                if isinstance(raw, bytes):
                    try:
                        return raw.decode("latin-1")
                    except Exception:
                        return ""
                return str(raw)
    return ""


@register_ai_analyzer
class TextAsOutlinesAnalyzer(BaseAIAnalyzer):
    """Detect text that has been converted to outlines (vector paths)."""

    category = "text_analysis"
    feature_slug = "text_as_outlines_detection"
    tier = "gpu"
    credits_per_run = 2

    def analyze(  # skipcq: PY-R1000
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
        pdf_bytes: bytes,
        ai_config: TenantAIConfig | None = None,
    ) -> list[Finding]:
        from grounded.ai.rendering import render_page_to_image

        findings: list[Finding] = []
        suspect_pages: list[int] = []

        # Phase 1: CPU-based heuristic — find pages with many paths but
        # little extractable text, which suggests text has been outlined
        for page in document.pages:
            page_num = page.page_num
            path_count, text_char_count = _count_path_and_text_events(events, page_num)

            if (
                path_count >= _MIN_PATH_COUNT_FOR_SUSPECT
                and text_char_count <= _MAX_TEXT_CHARS_FOR_SUSPECT
            ):
                suspect_pages.append(page_num)

        if not suspect_pages:
            return []

        # Phase 2: GPU OCR verification — render suspect pages and run OCR
        # to confirm that visible text is stored as paths, not font glyphs
        gpu = _get_gpu_client()

        for page_num in suspect_pages:
            try:
                png_bytes = render_page_to_image(pdf_bytes, page_num=page_num, dpi=200)
            except RuntimeError:
                logger.debug("text_as_outlines: rendering failed for page %d", page_num)
                continue

            try:
                result = gpu.detect_outlines(png_bytes)
            except GPUServiceUnavailableError as exc:
                findings.append(
                    self._make_finding(
                        inspection_id="AI_TAO_001",
                        severity=Severity.ADVISORY,
                        message=(
                            "GPU inference service unavailable for text-as-outlines "
                            f"verification: {exc}"
                        ),
                        page_num=page_num,
                        details={"reason": "gpu_unavailable"},
                    )
                )
                return findings

            ocr_text = result.get("detected_text", "")
            ocr_confidence = float(result.get("confidence", 0))
            outlined_regions = result.get("outlined_regions", [])

            # If OCR detected significant text on a page with no extractable
            # text events, the text is almost certainly outlined
            if len(ocr_text.strip()) > 20 and ocr_confidence > 0.5:
                # Get path/text counts for details
                path_count, text_char_count = _count_path_and_text_events(events, page_num)

                findings.append(
                    self._make_finding(
                        inspection_id="AI_TAO_002",
                        severity=Severity.SQUALL,
                        message=(
                            f"Page {page_num} contains text converted to outlines. "
                            f"OCR detected {len(ocr_text)} characters of visible "
                            f"text but only {text_char_count} characters are "
                            f"extractable as live text."
                        ),
                        page_num=page_num,
                        details={
                            "ocr_text_length": len(ocr_text),
                            "ocr_confidence": round(ocr_confidence, 4),
                            "extractable_text_chars": text_char_count,
                            "path_count": path_count,
                            "outlined_region_count": len(outlined_regions),
                            "ocr_text_preview": ocr_text[:200],
                        },
                        object_type="text",
                    )
                )

                # Report individual outlined regions if available
                for region in outlined_regions:
                    bbox_raw = region.get("bbox")
                    region_text = region.get("text", "")
                    bbox = (
                        tuple(float(v) for v in bbox_raw)
                        if bbox_raw and len(bbox_raw) == 4
                        else None
                    )
                    if region_text:
                        findings.append(
                            self._make_finding(
                                inspection_id="AI_TAO_003",
                                severity=Severity.SQUALL,
                                message=(
                                    f"Outlined text region on page {page_num}: '{region_text[:80]}'"
                                ),
                                page_num=page_num,
                                details={
                                    "region_text": region_text,
                                },
                                bbox=bbox,  # type: ignore[arg-type]
                                object_type="text",
                            )
                        )

        return findings
