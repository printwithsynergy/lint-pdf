"""Page annotation renderer — render PDF pages with finding overlays.

Renders PDF pages to images using pdf2image/Poppler, then draws
severity-colored bounding boxes and numbered callout markers using
Pillow.  Output is used by the HTML/PDF report generators to embed
annotated page screenshots.
"""

from __future__ import annotations

import base64
import io
import logging
import shutil
from dataclasses import dataclass, field
from typing import Any

import pikepdf
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_poppler_checked = False
_poppler_available = False


def _check_poppler() -> bool:
    """Verify that Poppler's pdftoppm is installed (required by pdf2image)."""
    global _poppler_checked, _poppler_available
    if _poppler_checked:
        return _poppler_available
    _poppler_checked = True
    _poppler_available = shutil.which("pdftoppm") is not None
    if not _poppler_available:
        logger.error(
            "poppler-utils is not installed (pdftoppm not found on PATH). "
            "Page screenshots will NOT be rendered. Install poppler-utils."
        )
    return _poppler_available


# ---------------------------------------------------------------------------
# Severity colors (matching annotated_pdf_report.py)
# ---------------------------------------------------------------------------

SEVERITY_FILL: dict[str, tuple[int, int, int, int]] = {
    "error": (239, 68, 68, 50),
    "warning": (245, 158, 11, 45),
    "advisory": (59, 130, 246, 40),
}

SEVERITY_STROKE: dict[str, tuple[int, int, int, int]] = {
    "error": (220, 38, 38, 220),
    "warning": (217, 119, 6, 220),
    "advisory": (37, 99, 235, 220),
}

SEVERITY_BADGE_BG: dict[str, tuple[int, int, int]] = {
    "error": (220, 38, 38),
    "warning": (217, 119, 6),
    "advisory": (37, 99, 235),
}

DEFAULT_DPI = 150
MAX_PAGES = 50
STROKE_WIDTH = 3
BADGE_RADIUS = 14
BADGE_FONT_SIZE = 16
BADGE_OFFSET = 4  # pixels from top-right corner of bbox


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CalloutInfo:
    """A numbered callout on an annotated page image."""

    number: int
    severity: str
    inspection_id: str
    message: str
    object_id: str | None = None
    object_type: str | None = None
    source: str = "engine"
    category: str | None = None
    bbox_present: bool = True


@dataclass
class AnnotatedPageResult:
    """Result of rendering a single annotated page."""

    page_num: int
    image_bytes: bytes
    image_base64: str
    width: int
    height: int
    callouts: list[CalloutInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------


def _get_page_media_box(pdf_bytes: bytes, page_num: int) -> tuple[float, float, float, float]:
    """Read the MediaBox for *page_num* (1-indexed)."""
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_num - 1]
        mb = page.get("/MediaBox")
        if mb is None:
            mb = [0, 0, 612, 792]  # fallback US Letter
        vals = [float(v) for v in mb]
        return (vals[0], vals[1], vals[2], vals[3])


def _pdf_bbox_to_pixels(
    bbox: tuple[float, float, float, float],
    media_box: tuple[float, float, float, float],
    img_width: int,
    img_height: int,
) -> tuple[int, int, int, int]:
    """Convert a PDF-coordinate bbox to image-pixel coordinates.

    PDF coordinate system: origin bottom-left, Y increases upward.
    Image coordinate system: origin top-left, Y increases downward.
    """
    mb_x0, mb_y0, mb_x1, mb_y1 = media_box
    page_w = mb_x1 - mb_x0
    page_h = mb_y1 - mb_y0

    if page_w <= 0 or page_h <= 0:
        return (0, 0, 0, 0)

    scale_x = img_width / page_w
    scale_y = img_height / page_h

    bx0, by0, bx1, by1 = bbox

    # Convert & flip Y
    px_x0 = int((bx0 - mb_x0) * scale_x)
    px_y0 = int(img_height - (by1 - mb_y0) * scale_y)
    px_x1 = int((bx1 - mb_x0) * scale_x)
    px_y1 = int(img_height - (by0 - mb_y0) * scale_y)

    # Clamp to image bounds
    px_x0 = max(0, min(px_x0, img_width))
    px_y0 = max(0, min(px_y0, img_height))
    px_x1 = max(0, min(px_x1, img_width))
    px_y1 = max(0, min(px_y1, img_height))

    return (px_x0, px_y0, px_x1, px_y1)


# ---------------------------------------------------------------------------
# Font helper
# ---------------------------------------------------------------------------

_cached_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None


def _get_badge_font(size: int = BADGE_FONT_SIZE) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a suitable font for callout badges, with fallback."""
    global _cached_font
    if _cached_font is not None:
        return _cached_font

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in font_paths:
        try:
            _cached_font = ImageFont.truetype(path, size)
            return _cached_font
        except OSError:
            continue

    _cached_font = ImageFont.load_default()
    return _cached_font


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------


def _draw_annotations(
    img: Image.Image,
    findings: list[dict[str, Any]],
    media_box: tuple[float, float, float, float],
) -> list[CalloutInfo]:
    """Draw bounding box rectangles and numbered callout badges on *img*.

    Returns the list of callouts so the template can render a matching legend.
    """
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _get_badge_font()

    callouts: list[CalloutInfo] = []
    callout_num = 0

    for f in findings:
        severity = f.get("severity", "advisory")
        bbox = f.get("bbox")
        has_bbox = bbox is not None and len(bbox) == 4 and bbox[0] is not None

        callout_num += 1
        callout = CalloutInfo(
            number=callout_num,
            severity=severity,
            inspection_id=f.get("inspection_id", ""),
            message=f.get("message", ""),
            object_id=f.get("object_id"),
            object_type=f.get("object_type"),
            source=f.get("source", "engine"),
            category=f.get("category"),
            bbox_present=has_bbox,
        )
        callouts.append(callout)

        if not has_bbox:
            # Draw a small severity-colored flag on the left edge so findings
            # without precise bounding boxes are still visible on the page.
            flag_y = 20 + (callout_num - 1) * (BADGE_RADIUS * 2 + 8)
            flag_y = min(flag_y, img.size[1] - BADGE_RADIUS - 4)
            badge_bg = SEVERITY_BADGE_BG.get(severity, SEVERITY_BADGE_BG["advisory"])
            _draw_badge(draw, font, callout_num, BADGE_RADIUS + 6, flag_y, badge_bg, img.size)
            continue

        px = _pdf_bbox_to_pixels(
            tuple(bbox),  # type: ignore[arg-type]
            media_box,
            img.width,
            img.height,
        )
        px_x0, px_y0, px_x1, px_y1 = px

        # Skip degenerate boxes
        if px_x1 - px_x0 < 2 or px_y1 - px_y0 < 2:
            continue

        fill = SEVERITY_FILL.get(severity, SEVERITY_FILL["advisory"])
        stroke = SEVERITY_STROKE.get(severity, SEVERITY_STROKE["advisory"])
        badge_bg = SEVERITY_BADGE_BG.get(severity, SEVERITY_BADGE_BG["advisory"])

        # Draw filled rectangle
        draw.rectangle([px_x0, px_y0, px_x1, px_y1], fill=fill, outline=stroke, width=STROKE_WIDTH)

        # Draw numbered badge at top-right of bbox
        badge_x = px_x1 - BADGE_OFFSET
        badge_y = px_y0 - BADGE_OFFSET
        _draw_badge(draw, font, callout_num, badge_x, badge_y, badge_bg, img.size)

    # Composite the overlay onto the original image
    img_rgba = img.convert("RGBA") if img.mode != "RGBA" else img
    composited = Image.alpha_composite(img_rgba, overlay)
    # Copy result back to original image object
    final = composited.convert("RGB")
    img.paste(final)

    return callouts


def _draw_badge(
    draw: ImageDraw.Draw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    number: int,
    cx: int,
    cy: int,
    bg_color: tuple[int, int, int],
    img_size: tuple[int, int],
) -> None:
    """Draw a numbered circle badge at (cx, cy)."""
    r = BADGE_RADIUS
    # Clamp to image bounds with padding
    cx = max(r + 2, min(cx, img_size[0] - r - 2))
    cy = max(r + 2, min(cy, img_size[1] - r - 2))

    # Draw circle with slight shadow
    shadow_offset = 2
    draw.ellipse(
        [
            cx - r + shadow_offset,
            cy - r + shadow_offset,
            cx + r + shadow_offset,
            cy + r + shadow_offset,
        ],
        fill=(0, 0, 0, 80),
    )
    # Main circle
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(*bg_color, 230),
        outline=(255, 255, 255, 255),
        width=2,
    )

    # Draw number text centered
    text = str(number)
    try:
        text_bbox = font.getbbox(text)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]
    except AttributeError:
        tw, th = draw.textsize(text, font=font)  # type: ignore[attr-defined]

    tx = cx - tw // 2
    ty = cy - th // 2 - 1
    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_annotated_page(
    pdf_bytes: bytes,
    page_num: int,
    findings: list[dict[str, Any]],
    *,
    dpi: int = DEFAULT_DPI,
) -> AnnotatedPageResult:
    """Render a single PDF page with finding annotations overlaid.

    Args:
        pdf_bytes: Raw PDF bytes.
        page_num: 1-indexed page number.
        findings: Findings for this page (must include ``bbox`` and ``severity``).
        dpi: Render resolution.

    Returns:
        AnnotatedPageResult with the image and callout information.
    """
    from lintpdf.ai.rendering import render_page_to_image

    # Render page to PNG
    png_bytes = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")

    # Get page dimensions for coordinate conversion
    media_box = _get_page_media_box(pdf_bytes, page_num)

    # Draw annotations
    callouts = _draw_annotations(img, findings, media_box)

    # Encode result
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    result_bytes = buf.getvalue()
    b64 = base64.b64encode(result_bytes).decode("ascii")

    return AnnotatedPageResult(
        page_num=page_num,
        image_bytes=result_bytes,
        image_base64=b64,
        width=img.width,
        height=img.height,
        callouts=callouts,
    )


def render_annotated_pages(
    pdf_bytes: bytes,
    findings_by_page: dict[int, list[dict[str, Any]]],
    *,
    dpi: int = DEFAULT_DPI,
    max_pages: int = MAX_PAGES,
) -> dict[int, AnnotatedPageResult]:
    """Render multiple PDF pages with annotations.

    Only pages present in *findings_by_page* are rendered. Pages where
    ``page_num < 1`` (document-level findings) are skipped.

    Args:
        pdf_bytes: Raw PDF bytes.
        findings_by_page: ``{page_num: [finding_dict, ...]}``
        dpi: Render resolution.
        max_pages: Cap on pages to render (safety limit).

    Returns:
        ``{page_num: AnnotatedPageResult}``
    """
    results: dict[int, AnnotatedPageResult] = {}
    rendered = 0

    if not _check_poppler():
        return results

    # Get total page count for validation
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
    except Exception:
        logger.warning("Failed to open PDF for page count — skipping annotation rendering")
        return results

    for page_num in sorted(findings_by_page.keys()):
        if page_num < 1:
            continue  # skip document-level findings
        if page_num > total_pages:
            logger.warning(
                "Finding references page %d but PDF only has %d pages", page_num, total_pages
            )
            continue
        if rendered >= max_pages:
            logger.info("Reached max_pages=%d limit for annotated rendering", max_pages)
            break

        try:
            result = render_annotated_page(pdf_bytes, page_num, findings_by_page[page_num], dpi=dpi)
            results[page_num] = result
            rendered += 1
        except Exception:
            logger.exception("Failed to render annotated page %d", page_num)

    return results


def render_page_thumbnail(
    pdf_bytes: bytes,
    page_num: int,
    *,
    dpi: int = 72,
) -> str:
    """Render a plain page thumbnail (no annotations) as base64 PNG.

    Used for pages that have findings but no bounding boxes,
    to still give visual context.
    """
    from lintpdf.ai.rendering import render_page_to_image

    try:
        png_bytes = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
        return base64.b64encode(png_bytes).decode("ascii")
    except Exception:
        logger.debug("Failed to render thumbnail for page %d", page_num)
        return ""


def render_page_thumbnail_grid(
    pdf_bytes: bytes,
    *,
    max_pages: int = 12,
    dpi: int = 72,
) -> list[str]:
    """Render small page thumbnails for the summary page cover sheet.

    Returns a list of base64-encoded PNGs (one per page, up to max_pages).
    """
    try:
        page_count = len(pikepdf.Pdf.open(io.BytesIO(pdf_bytes)).pages)
    except Exception:
        return []

    result: list[str] = []
    for i in range(1, min(page_count + 1, max_pages + 1)):
        thumb = render_page_thumbnail(pdf_bytes, i, dpi=dpi)
        result.append(thumb)
    return result


# ---------------------------------------------------------------------------
# Per-finding cropped thumbnails
# ---------------------------------------------------------------------------

THUMB_PADDING = 60  # pixels around bbox in cropped thumbnail
THUMB_MAX_W = 240
THUMB_MAX_H = 180


def _crop_finding_thumbnail(
    page_img: Image.Image,
    finding: dict[str, Any],
    media_box: tuple[float, float, float, float],
) -> str:
    """Crop a page image around a finding's bbox and draw a severity highlight.

    Returns a base64-encoded PNG of the cropped area, or an empty string
    if the finding has no bounding box.
    """
    bbox = finding.get("bbox")
    has_bbox = bbox is not None and len(bbox) == 4 and bbox[0] is not None
    severity = finding.get("severity", "advisory")

    if has_bbox:
        px = _pdf_bbox_to_pixels(
            tuple(bbox),  # type: ignore[arg-type]
            media_box,
            page_img.width,
            page_img.height,
        )
        px_x0, px_y0, px_x1, px_y1 = px

        # Skip degenerate boxes — fall back to center crop
        if px_x1 - px_x0 < 4 or px_y1 - px_y0 < 4:
            has_bbox = False

    if has_bbox:
        # Crop around bbox with padding
        crop_x0 = max(0, px_x0 - THUMB_PADDING)
        crop_y0 = max(0, px_y0 - THUMB_PADDING)
        crop_x1 = min(page_img.width, px_x1 + THUMB_PADDING)
        crop_y1 = min(page_img.height, px_y1 + THUMB_PADDING)

        cropped = page_img.crop((crop_x0, crop_y0, crop_x1, crop_y1)).copy()

        # Draw severity highlight on the cropped image
        overlay = Image.new("RGBA", cropped.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        fill = SEVERITY_FILL.get(severity, SEVERITY_FILL["advisory"])
        stroke = SEVERITY_STROKE.get(severity, SEVERITY_STROKE["advisory"])

        # Bbox position relative to crop
        rel_x0 = px_x0 - crop_x0
        rel_y0 = px_y0 - crop_y0
        rel_x1 = px_x1 - crop_x0
        rel_y1 = px_y1 - crop_y0
        draw.rectangle([rel_x0, rel_y0, rel_x1, rel_y1], fill=fill, outline=stroke, width=3)

        if cropped.mode != "RGBA":
            cropped = cropped.convert("RGBA")
        composited = Image.alpha_composite(cropped, overlay).convert("RGB")
    else:
        # No bbox — crop center of page with severity-colored border
        cw = min(page_img.width, THUMB_MAX_W * 2)
        ch = min(page_img.height, THUMB_MAX_H * 2)
        cx = page_img.width // 2
        cy = page_img.height // 3  # bias toward top of page
        crop_x0 = max(0, cx - cw // 2)
        crop_y0 = max(0, cy - ch // 2)
        crop_x1 = min(page_img.width, crop_x0 + cw)
        crop_y1 = min(page_img.height, crop_y0 + ch)
        composited = page_img.crop((crop_x0, crop_y0, crop_x1, crop_y1)).copy()
        if composited.mode != "RGB":
            composited = composited.convert("RGB")
        # Draw severity-colored border around the thumbnail
        stroke = SEVERITY_STROKE.get(severity, SEVERITY_STROKE["advisory"])
        draw = ImageDraw.Draw(composited)
        for i in range(3):
            draw.rectangle(
                [i, i, composited.width - 1 - i, composited.height - 1 - i],
                outline=stroke,
                width=1,
            )

    # Resize to thumbnail
    composited.thumbnail((THUMB_MAX_W, THUMB_MAX_H), Image.LANCZOS)

    buf = io.BytesIO()
    composited.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_finding_thumbnails(
    pdf_bytes: bytes,
    findings: list[dict[str, Any]],
    *,
    dpi: int = 120,
    max_pages: int = MAX_PAGES,
) -> None:
    """Render cropped thumbnails for each finding, in-place.

    Adds ``thumbnail_base64`` key to each finding dict. Caches page images
    so each page is rendered only once regardless of how many findings it has.

    Args:
        pdf_bytes: Raw PDF bytes.
        findings: List of finding dicts (modified in-place).
        dpi: Render resolution for page images.
        max_pages: Max distinct pages to render.
    """
    if not _check_poppler():
        return

    from lintpdf.ai.rendering import render_page_to_image

    # Cache rendered page images + media boxes
    page_cache: dict[int, tuple[Image.Image, tuple[float, float, float, float]]] = {}
    rendered_pages = 0

    for finding in findings:
        page_num = finding.get("page_num", 0)
        if page_num < 1:
            finding["thumbnail_base64"] = ""
            continue

        # Render page if not cached
        if page_num not in page_cache:
            if rendered_pages >= max_pages:
                finding["thumbnail_base64"] = ""
                continue
            try:
                png_bytes = render_page_to_image(pdf_bytes, page_num, dpi=dpi)
                img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
                media_box = _get_page_media_box(pdf_bytes, page_num)
                page_cache[page_num] = (img, media_box)
                rendered_pages += 1
            except Exception:
                logger.debug("Failed to render page %d for thumbnails", page_num)
                finding["thumbnail_base64"] = ""
                continue

        img, media_box = page_cache[page_num]

        try:
            finding["thumbnail_base64"] = _crop_finding_thumbnail(img, finding, media_box)
        except Exception:
            logger.debug("Failed to crop thumbnail for finding on page %d", page_num)
            finding["thumbnail_base64"] = ""
