"""Page rendering utility for AI analyzers that need rasterized page images."""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# Try to import pdf2image (poppler-based) for rendering
try:
    from pdf2image import convert_from_bytes as _convert_from_bytes

    _HAS_PDF2IMAGE = True
except ImportError:
    _HAS_PDF2IMAGE = False
    _convert_from_bytes = None

# Fallback: try pikepdf + Pillow
try:
    from PIL import Image as _PILImage

    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False
    _PILImage = None  # type: ignore[assignment]


def render_page_to_image(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 300,
) -> bytes:
    """Render a single PDF page to PNG image bytes.

    Args:
        pdf_bytes: Raw PDF file bytes.
        page_num: 1-indexed page number.
        dpi: Resolution for rendering.

    Returns:
        PNG image bytes.

    Raises:
        RuntimeError: If no rendering backend is available.
    """
    if _HAS_PDF2IMAGE:
        images = _convert_from_bytes(
            pdf_bytes,
            first_page=page_num,
            last_page=page_num,
            dpi=dpi,
            fmt="png",
        )
        if not images:
            raise RuntimeError(f"Failed to render page {page_num}")
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        return buf.getvalue()

    raise RuntimeError("No PDF rendering backend available. Install pdf2image and poppler-utils.")


def render_all_pages(
    pdf_bytes: bytes,
    dpi: int = 300,
    max_pages: int = 50,
) -> list[bytes]:
    """Render all pages (up to max_pages) to PNG bytes.

    Args:
        pdf_bytes: Raw PDF file bytes.
        dpi: Resolution for rendering.
        max_pages: Maximum pages to render.

    Returns:
        List of PNG image bytes, one per page.
    """
    if _HAS_PDF2IMAGE:
        images = _convert_from_bytes(
            pdf_bytes,
            dpi=dpi,
            fmt="png",
            last_page=max_pages,
        )
        result = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            result.append(buf.getvalue())
        return result

    raise RuntimeError("No PDF rendering backend available. Install pdf2image and poppler-utils.")


def get_page_count(pdf_bytes: bytes) -> int:
    """Get the number of pages in a PDF."""
    try:
        import pikepdf

        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0
