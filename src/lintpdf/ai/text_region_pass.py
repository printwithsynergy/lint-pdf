"""Shared OCR text-region detection pass.

Single responsibility: for each page that the trigger heuristic selects,
delegate to ``codex_pdf.extract.text_regions`` (in-process) and map the
results onto ``SemanticPage.detected_text_regions``.

OCR is Codex's responsibility — this module is a thin adapter that reads
Codex's output. Codex uses PyMuPDF for selectable text and Tesseract
(CPU, no external service) for pages where PyMuPDF finds nothing (outlined
or rasterized text). No LLM calls and no GPU services are made here.

Multiple downstream consumers read ``SemanticPage.detected_text_regions``:

* ``ai.analyzers.spatial_analysis.safe_zone_violations`` — text-near-edge
  detection.
* ``analyzers.legibility_composite`` + ``analyzers.hairline`` —
  glyph-height signal.
* ``ai.analyzers.color_analysis.{color_cast,banding,skin_tone}`` — text mask.
* ``ai.analyzers.text_analysis.text_as_outlines`` — outlined-text detection.

Ground rules:

* Delegates entirely to ``codex_pdf.extract.text_regions`` (in-process,
  no HTTP). If the package is not importable the field stays ``None`` and
  consumer analyzers skip gracefully.
* Pages that don't pass the trigger heuristic are never processed.
* Any per-page failure is logged and skipped; the job never fails here.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lintpdf.semantic.events import ImagePlacedEvent, PathPaintingEvent, TextRenderedEvent
from lintpdf.semantic.model import DetectedTextRegion, PdfBox

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument, SemanticPage

logger = logging.getLogger(__name__)

_DEFAULT_DPI = 150

# Trigger thresholds — same heuristic as text_as_outlines.py:
_PATH_HEAVY_THRESHOLD = 50
_TEXT_LIGHT_THRESHOLD = 10
_PLACED_IMAGE_AREA_RATIO = 0.25


def should_run_for_page(page: SemanticPage, events: list[ContentStreamEvent]) -> bool:
    """Return True when this page passes the trigger heuristic.

    Two qualifying conditions:

    * **Image-heavy:** placed-image area > 25% of page area.
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

    Retained for callers that still pass pixel-space bbox dicts (e.g. the
    codex HTTP path via ``codex_client.populate_text_regions_via_codex``).
    Not used by the primary in-process codex path.
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
    ai_config: object | None = None,
    dpi: int = _DEFAULT_DPI,
) -> None:
    """Mutate ``document`` in place: populate ``page.detected_text_regions``.

    Delegates to ``codex_pdf.extract.text_regions.extract_text_regions_for_page``
    (in-process, no HTTP). Codex handles both selectable text (PyMuPDF) and
    outlined/rasterized text (Tesseract CPU fallback) so no OCR happens in lint.

    Pages that don't pass the trigger heuristic remain at ``None``.
    Pages where extraction fails also remain at ``None`` — consumers treat
    that as "pass not run, can't decide".
    """
    pages_to_run: list[SemanticPage] = [
        page for page in document.pages if should_run_for_page(page, events)
    ]
    if not pages_to_run:
        return

    try:
        from codex_pdf.extract.text_regions import extract_text_regions_for_page
    except ImportError:
        logger.debug("text_region_pass: codex_pdf not importable; pass skipped")
        return

    for page in pages_to_run:
        try:
            codex_regions = extract_text_regions_for_page(pdf_bytes, page.page_num - 1, dpi=dpi)
        except Exception as exc:
            logger.warning(
                "text_region_pass: codex extraction failed for page %d: %s",
                page.page_num,
                exc,
            )
            continue

        regions: list[DetectedTextRegion] = []
        for cr in codex_regions:
            b = cr.bbox
            x0, y0, x1, y1 = float(b.x0), float(b.y0), float(b.x1), float(b.y1)
            if x1 <= x0:
                x1 = x0 + 1e-3
            if y1 <= y0:
                y1 = y0 + 1e-3
            polygon: tuple[tuple[float, float], ...] | None = None
            if cr.polygon and len(cr.polygon) >= 3:
                polygon = tuple((float(pt[0]), float(pt[1])) for pt in cr.polygon)
            regions.append(
                DetectedTextRegion(
                    bbox=PdfBox(x0, y0, x1, y1),
                    text=cr.text or None,
                    confidence=float(cr.confidence),
                    polygon=polygon,
                    source=str(cr.source),
                )
            )

        page.detected_text_regions = regions
        logger.debug(
            "text_region_pass: page %d → %d regions (via codex)",
            page.page_num,
            len(regions),
        )
