"""Text-as-outlines detection analyzer — hybrid PDF structure + GPU OCR.

Detects text that has been converted to outlines (paths) in the PDF by
combining two approaches:

1. **PDF structure analysis (CPU):** Scans for pages that have many path
   objects but little or no extractable text — a hallmark of outlined text.
2. **GPU OCR verification:** Renders suspect pages and runs OCR via the GPU
   inference service to confirm that visible text exists as paths rather
   than font glyphs.

Outlined text that should be live text generates a WARNING finding.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from siftpdf.ai.base import BaseAIAnalyzer
from siftpdf.ai.registry import register_ai_analyzer
from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.plugin.protocol import AnalyzerContext
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument

logger = logging.getLogger(__name__)

# Thresholds for heuristic detection
_MIN_PATH_COUNT_FOR_SUSPECT = 50  # Pages with many paths but no text
_MAX_TEXT_CHARS_FOR_SUSPECT = 10  # Negligible extractable text


def _count_path_and_text_events(events: list[ContentStreamEvent], page_num: int) -> tuple[int, int]:
    """Count path painting events and text characters on a page."""
    from siftpdf.semantic.events import PathPaintingEvent, TextRenderedEvent

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

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses document
        # + events. pdf_bytes + ai_config declared but never used.
        document = ctx.document
        events = ctx.events

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

        # Phase 2: read the orchestrator's shared text-region pass instead
        # of running our own GPU call. The orchestrator renders each suspect
        # page once and populates ``page.detected_text_regions`` in PDF-point
        # coordinates; this analyzer just reads them. If the field is None the
        # pass didn't run (GPU outage or trigger heuristic gated it) — bail
        # silently; AI_SCAN_001 on the orchestrator records the pipeline state.
        page_index = {page.page_num: page for page in document.pages}

        for page_num in suspect_pages:
            page = page_index.get(page_num)
            if page is None:
                continue
            regions = page.detected_text_regions
            if regions is None:
                # Pass didn't run for this page; can't decide.
                continue
            if not regions:
                # Pass ran but found no text — page is a true vector-art page,
                # not outlined text. Skip.
                continue

            ocr_text = " ".join((r.text or "").strip() for r in regions if r.text).strip()
            ocr_confidence = max((r.confidence for r in regions), default=0.0)

            # Same threshold as before — significant text recognised on a page
            # with negligible extractable-text events implies outlined glyphs.
            if len(ocr_text) > 20 and ocr_confidence > 0.5:
                path_count, text_char_count = _count_path_and_text_events(events, page_num)

                findings.append(
                    self._make_finding(
                        inspection_id="AI_TAO_002",
                        severity=Severity.WARNING,
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
                            "outlined_region_count": len(regions),
                            "ocr_text_preview": ocr_text[:200],
                        },
                        object_type="text",
                    )
                )

                for region in regions:
                    region_text = (region.text or "").strip()
                    if not region_text:
                        continue
                    bbox = (region.bbox.x0, region.bbox.y0, region.bbox.x1, region.bbox.y1)
                    findings.append(
                        self._make_finding(
                            inspection_id="AI_TAO_003",
                            severity=Severity.WARNING,
                            message=(
                                f"Outlined text region on page {page_num}: '{region_text[:80]}'"
                            ),
                            page_num=page_num,
                            details={"region_text": region_text},
                            bbox=bbox,
                            object_type="text",
                        )
                    )

        return findings
