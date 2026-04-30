"""Shared OCR text-region detection pass.

Single responsibility: for each page that the trigger heuristic selects,
render at the configured DPI, ask the GPU client for OCR text regions,
convert pixel-space bboxes to PDF-point coordinates, and stash the result
on ``SemanticPage.detected_text_regions``.

Multiple downstream consumers read this field:

* ``ai.analyzers.spatial_analysis.safe_zone_violations`` — text-near-edge
  detection (DINO call drops ``text.`` from the prompt).
* ``analyzers.legibility_composite`` + ``analyzers.hairline`` —
  measured-glyph-height signal alongside ``TextRenderedEvent.font_size_pt``.
* ``ai.analyzers.color_analysis.{color_cast,banding,skin_tone}`` — text mask
  to exclude from sample regions.
* ``ai.analyzers.text_analysis.text_as_outlines`` — replaces its private OCR
  call with a read of this field.

Ground rules:

* On GPU outage (``GPUServiceUnavailableError``) or any unexpected exception,
  leave the field as ``None`` for affected pages and log a warning. Don't fail
  the job — the consumer analyzers all treat ``None`` as "pass not run".
* Reuse the existing ``check_cap_or_raise`` cost-cap pattern around the
  ``"ocr"`` AI feature. PR2 deliberately does not introduce a new
  ``detect_text_regions`` feature flag — the metering line is the same.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from siftpdf.ai.gpu_client import (
    GPUServiceNotConfiguredError,
    GPUServiceRateLimitedError,
    GPUServiceUnavailableError,
)
from siftpdf.semantic.events import ImagePlacedEvent, PathPaintingEvent, TextRenderedEvent
from siftpdf.semantic.model import DetectedTextRegion, PdfBox

if TYPE_CHECKING:
    from siftpdf.api.models import TenantAIConfig
    from siftpdf.semantic.events import ContentStreamEvent
    from siftpdf.semantic.model import SemanticDocument, SemanticPage

logger = logging.getLogger(__name__)

_DEFAULT_DPI = 200

# Trigger thresholds, mirrored from text_as_outlines.py:
_PATH_HEAVY_THRESHOLD = 50
_TEXT_LIGHT_THRESHOLD = 10
_PLACED_IMAGE_AREA_RATIO = 0.25


def should_run_for_page(page: SemanticPage, events: list[ContentStreamEvent]) -> bool:
    """Return True when this page passes the trigger heuristic.

    Two qualifying conditions:

    * **Image-heavy:** placed-image area > 25% of page area (RGB scans,
      photo-product layouts where image content can hide outlined captions).
    * **Path-heavy / text-light:** ≥50 path events AND ≤10 extractable text
      characters — the same heuristic ``text_as_outlines`` already used.
    """
    page_num = page.page_num
    page_area = page.media_box.width * page.media_box.height
    if page_area <= 0:
        return False

    image_area = 0.0
    path_count = 0
    text_chars = 0

    for event in events:
        if event.page_num != page_num:
            continue
        if isinstance(event, ImagePlacedEvent):
            ctm = event.ctm
            # Approximate placed footprint via the CTM scaling factors.
            scale_x = abs(getattr(ctm, "a", 1.0))
            scale_y = abs(getattr(ctm, "d", 1.0))
            image_area += scale_x * scale_y
        elif isinstance(event, PathPaintingEvent):
            path_count += 1
        elif isinstance(event, TextRenderedEvent):
            text_chars += len(getattr(event, "text", "") or "")

    if image_area / page_area > _PLACED_IMAGE_AREA_RATIO:
        return True
    return path_count >= _PATH_HEAVY_THRESHOLD and text_chars <= _TEXT_LIGHT_THRESHOLD


def _scale_bbox(
    bbox: dict, image_width: float, image_height: float, page: SemanticPage
) -> tuple[PdfBox, tuple[tuple[float, float], ...] | None]:
    """Convert pixel-space {x1,y1,x2,y2,polygon} to PDF points.

    Pixel space has origin top-left; PDF user space has origin bottom-left.
    Mirrors the pattern used in ``safe_zone_violations.py``.
    """
    page_w_pt = page.media_box.width
    page_h_pt = page.media_box.height
    sx = page_w_pt / image_width if image_width else 1.0
    sy = page_h_pt / image_height if image_height else 1.0

    x0_px = float(bbox.get("x1", 0))
    y0_px = float(bbox.get("y1", 0))
    x1_px = float(bbox.get("x2", x0_px))
    y1_px = float(bbox.get("y2", y0_px))

    x0_pt = x0_px * sx
    x1_pt = x1_px * sx
    # Flip the y axis so the bbox lands in PDF user-space (origin bottom-left).
    y0_pt = page_h_pt - (y1_px * sy)
    y1_pt = page_h_pt - (y0_px * sy)
    if x1_pt <= x0_pt:
        x1_pt = x0_pt + 1e-3
    if y1_pt <= y0_pt:
        y1_pt = y0_pt + 1e-3
    pdf_box = PdfBox(x0_pt, y0_pt, x1_pt, y1_pt)

    polygon_raw = bbox.get("polygon")
    polygon: tuple[tuple[float, float], ...] | None = None
    if isinstance(polygon_raw, list) and len(polygon_raw) >= 3:
        pts: list[tuple[float, float]] = []
        for p in polygon_raw:
            if not isinstance(p, (list, tuple)) or len(p) < 2:
                continue
            px = float(p[0]) * sx
            py = page_h_pt - float(p[1]) * sy
            pts.append((px, py))
        if len(pts) >= 3:
            polygon = tuple(pts)

    return pdf_box, polygon


def run(
    document: SemanticDocument,
    events: list[ContentStreamEvent],
    pdf_bytes: bytes,
    ai_config: TenantAIConfig | None = None,
    dpi: int = _DEFAULT_DPI,
) -> None:
    """Mutate ``document`` in place: populate ``page.detected_text_regions``.

    Pages that don't pass the trigger heuristic remain at ``None``.
    Pages that pass but where the GPU call fails also remain at ``None``
    (consumers treat that as "pass not run, can't decide").
    """
    # Lazy imports keep this module importable in unit-test sandboxes that
    # don't have httpx / pillow / paddleocr available.
    from siftpdf.ai.gpu_client import get_gpu_client
    from siftpdf.rendering import render_page_to_image

    pages_to_run: list[SemanticPage] = [
        page for page in document.pages if should_run_for_page(page, events)
    ]
    if not pages_to_run:
        return

    try:
        gpu = get_gpu_client()
    except Exception as exc:
        logger.warning("text_region_pass: cannot init GPU client: %s", exc)
        return

    # NOTE: cost-cap metering — the orchestrator caller is expected to wrap
    # this function with ``check_cap_or_raise(db, tenant_id)`` since that
    # signature requires a DB session this module doesn't have. The pass
    # piggybacks on the existing ``ocr`` AI feature in
    # ``TenantAIConfig.ai_features`` rather than introducing a new flag.

    for page in pages_to_run:
        try:
            png = render_page_to_image(pdf_bytes, page_num=page.page_num, dpi=dpi)
        except (RuntimeError, OSError) as exc:
            logger.debug("text_region_pass: rendering failed for page %d: %s", page.page_num, exc)
            continue

        try:
            result = gpu.detect_outlines(png)
        except (
            GPUServiceUnavailableError,
            GPUServiceNotConfiguredError,
            GPUServiceRateLimitedError,
        ) as exc:
            logger.warning("text_region_pass: GPU unavailable on page %d: %s", page.page_num, exc)
            continue
        except Exception as exc:
            logger.warning("text_region_pass: GPU error on page %d: %s", page.page_num, exc)
            continue

        text_regions_raw = (result or {}).get("text_regions") or []
        # PaddleOCR doesn't surface image dims directly — the caller has the
        # rendered PNG, so we read its size from the metadata or assume a
        # safe default tied to the DPI we requested.
        image_width = float(result.get("image_width") or page.media_box.width * dpi / 72.0)
        image_height = float(result.get("image_height") or page.media_box.height * dpi / 72.0)

        regions: list[DetectedTextRegion] = []
        for raw in text_regions_raw:
            bbox_raw = raw.get("bbox")
            if not isinstance(bbox_raw, dict):
                continue
            try:
                pdf_box, polygon = _scale_bbox(bbox_raw, image_width, image_height, page)
            except Exception:
                continue
            regions.append(
                DetectedTextRegion(
                    bbox=pdf_box,
                    text=(raw.get("text") or None),
                    confidence=float(raw.get("confidence") or 0.0),
                    polygon=polygon,
                    source="paddleocr",
                )
            )

        page.detected_text_regions = regions
