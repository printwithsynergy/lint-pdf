"""Build a numpy boolean mask of OCR-detected text regions for use by
color analyzers (banding, color cast, skin tone) so they can exclude
text-edge pixels from sampling.

PR #295 added :class:`SemanticPage.detected_text_regions` (PDF-point
bboxes from PaddleOCR via ``ai.text_region_pass``). This helper inverts
the conversion to pixel space at the analyzer's render DPI, dilates each
bbox by a small antialiasing margin, and rasterises into a uint8 array
that downstream code can boolean-AND against the rendered page.

Usage::

    from siftpdf.ai.text_mask import build_text_mask

    mask = build_text_mask(page, dpi=150, dilation_px=10)
    if mask is not None:
        # mask shape: (height, width) uint8; 255 = exclude text region.
        sample_pixels[mask == 0]

Returns ``None`` when:

* The page has no ``detected_text_regions`` (pass not run / GPU offline).
* The mask would be empty (no regions intersect the page).
* numpy is unavailable in the runtime environment.

Best-effort: never raises. Color analyzers treat ``None`` as "no mask
to apply" and sample the full page (existing pre-PR behaviour).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

    from siftpdf.semantic.model import SemanticPage

logger = logging.getLogger(__name__)


def build_text_mask(
    page: SemanticPage,
    dpi: int = 150,
    dilation_px: int = 10,
) -> np.ndarray | None:
    """Return a uint8 (H, W) array marking detected-text regions as 255.

    Args:
        page: ``SemanticPage`` with ``detected_text_regions`` populated by
            ``ai.text_region_pass``.
        dpi: Render DPI used by the caller. The pixel dimensions of the
            mask are derived from the page's MediaBox at this DPI so the
            caller can boolean-AND against its render output directly.
        dilation_px: Margin (pixels) to grow each bbox by, catching
            antialiasing halos that color analyzers otherwise pick up
            as edge artefacts.

    Returns:
        ``np.ndarray`` of shape ``(height_px, width_px)`` and dtype
        ``uint8`` where ``255`` marks text-region pixels, ``0`` marks
        clean sampling pixels. Or ``None`` when the mask can't be
        built.
    """
    regions = getattr(page, "detected_text_regions", None)
    if not regions:
        return None
    try:
        import numpy as np
    except ImportError:  # pragma: no cover — color analyzers always have numpy
        return None

    media = getattr(page, "media_box", None)
    if media is None:
        return None
    page_w_pt = float(getattr(media, "width", 0) or 0)
    page_h_pt = float(getattr(media, "height", 0) or 0)
    if page_w_pt <= 0 or page_h_pt <= 0:
        return None

    width_px = max(1, round(page_w_pt * dpi / 72.0))
    height_px = max(1, round(page_h_pt * dpi / 72.0))

    mask = np.zeros((height_px, width_px), dtype=np.uint8)
    pt_to_px_x = width_px / page_w_pt
    pt_to_px_y = height_px / page_h_pt
    any_marked = False
    for region in regions:
        bbox = getattr(region, "bbox", None)
        if bbox is None:
            continue
        try:
            x0_pt = float(bbox.x0)
            y0_pt = float(bbox.y0)
            x1_pt = float(bbox.x1)
            y1_pt = float(bbox.y1)
        except (AttributeError, TypeError, ValueError):
            continue
        # Convert PDF points (origin bottom-left) to pixel space
        # (origin top-left). The y-axis flip mirrors what
        # ``text_region_pass._scale_bbox`` did when writing the
        # field — the inverse here.
        x0_px = max(0, int(x0_pt * pt_to_px_x) - dilation_px)
        x1_px = min(width_px, int(x1_pt * pt_to_px_x) + dilation_px)
        y0_px_top = max(0, int((page_h_pt - y1_pt) * pt_to_px_y) - dilation_px)
        y1_px_top = min(height_px, int((page_h_pt - y0_pt) * pt_to_px_y) + dilation_px)
        if x0_px >= x1_px or y0_px_top >= y1_px_top:
            continue
        mask[y0_px_top:y1_px_top, x0_px:x1_px] = 255
        any_marked = True

    return mask if any_marked else None


def text_density_ratio(page: SemanticPage) -> float:
    """Return the fraction of the page (0.0-1.0) covered by detected text.

    Used by color analyzers (cast, skin tone) that emit a global per-page
    metric rather than per-region results. When the page is text-heavy
    (>40 %), channel-mean / skin-tone deviations can be artefacts of
    text-stroke edge antialiasing rather than real image-quality issues,
    so the analyzer can demote severity.

    Returns 0.0 when no detected_text_regions are populated (pass not
    run / GPU offline) — preserves existing pre-PR behaviour.
    """
    regions = getattr(page, "detected_text_regions", None)
    if not regions:
        return 0.0
    media = getattr(page, "media_box", None)
    if media is None:
        return 0.0
    page_w = float(getattr(media, "width", 0) or 0)
    page_h = float(getattr(media, "height", 0) or 0)
    if page_w <= 0 or page_h <= 0:
        return 0.0
    page_area = page_w * page_h
    text_area = 0.0
    for region in regions:
        bbox = getattr(region, "bbox", None)
        if bbox is None:
            continue
        try:
            w = float(bbox.x1) - float(bbox.x0)
            h = float(bbox.y1) - float(bbox.y0)
        except (AttributeError, TypeError, ValueError):
            continue
        if w > 0 and h > 0:
            text_area += w * h
    return min(1.0, text_area / page_area) if page_area > 0 else 0.0


def filter_regions_by_text_mask(
    regions: list,
    page: SemanticPage,
    dpi: int = 150,
) -> tuple[list, int]:
    """Drop GPU-emitted regions whose centre falls inside a detected-text
    bbox. Returns ``(kept_regions, dropped_count)``.

    Used by color analyzers (banding, color cast, skin tone) so banding
    "artefacts" along text-stroke edges and color-cast / skin-tone
    samples that fell on text aren't reported as image-quality issues.

    When the page has no detected_text_regions or numpy is unavailable,
    returns the input unchanged.
    """
    if not regions or not isinstance(regions, list):
        return regions or [], 0
    mask = build_text_mask(page, dpi=dpi)
    if mask is None:
        return regions, 0
    kept: list = []
    dropped = 0
    h, w = mask.shape
    for r in regions:
        bbox = r.get("bbox") if isinstance(r, dict) else None
        if not (isinstance(bbox, (list, tuple)) and len(bbox) >= 4):
            kept.append(r)
            continue
        try:
            x0, y0, x1, y1 = (float(v) for v in bbox[:4])
        except (TypeError, ValueError):
            kept.append(r)
            continue
        cx = max(0, min(w - 1, int((x0 + x1) / 2)))
        cy = max(0, min(h - 1, int((y0 + y1) / 2)))
        if mask[cy, cx] == 255:
            dropped += 1
            continue
        kept.append(r)
    return kept, dropped
