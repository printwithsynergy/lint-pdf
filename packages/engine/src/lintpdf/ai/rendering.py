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


class OCGError(ValueError):
    """Raised when the caller requests an OCG override that can't be
    applied — either the PDF has no OCG dictionary, or the requested
    indices don't exist in the ``/OCProperties/OCGs`` array.

    Callers (the FastAPI tile handler) should translate this to a
    ``422 Unprocessable Entity`` so the client sees a clear error
    rather than a mysterious 500.
    """


def _apply_ocg_overrides(
    pdf_bytes: bytes,
    ocg_on: list[int] | None,
    ocg_off: list[int] | None,
) -> bytes:
    """Return a copy of ``pdf_bytes`` with its OCG default-visibility
    state rewritten so ``pdf2image`` (poppler) honours the caller's
    toggle mask when it renders.

    Poppler respects ``/Root/OCProperties/D/OFF`` at render time. We
    rewrite that array so it equals
    ``(original_off union explicit_off) minus explicit_on``. Indices
    refer to positions in ``/Root/OCProperties/OCGs`` — the same indices
    that ``viewer.list_layers`` returns as ``ocg_index`` on
    ``LayerInfo``.

    Args:
        pdf_bytes: Source PDF as raw bytes.
        ocg_on: Layer indices to force visible (removed from OFF).
        ocg_off: Layer indices to force hidden (added to OFF).

    Returns:
        The rewritten PDF bytes, or the original ``pdf_bytes`` object
        when both inputs are empty.

    Raises:
        OCGError: The PDF has no OCGs, indices are out of range, or
            an index appears in both ``ocg_on`` and ``ocg_off``.
    """
    import pikepdf

    on = set(ocg_on or [])
    off = set(ocg_off or [])
    if not on and not off:
        return pdf_bytes

    conflict = on & off
    if conflict:
        raise OCGError(f"ocg_on and ocg_off conflict on indices {sorted(conflict)}")

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        catalog = pdf.Root
        oc_props = catalog.get("/OCProperties")
        if oc_props is None:
            raise OCGError("PDF has no /OCProperties dictionary; cannot toggle layers.")
        ocgs = oc_props.get("/OCGs")
        if ocgs is None:
            raise OCGError("/OCProperties has no /OCGs array.")

        max_idx = len(ocgs) - 1
        for idx in on | off:
            if idx < 0 or idx > max_idx:
                raise OCGError(f"OCG index {idx} out of range (0..{max_idx}).")

        d = oc_props.get("/D")
        if d is None:
            # Some PDFs ship without /D; create one so /OFF has a
            # home. Leaves every other default unset (poppler treats
            # that as "all on").
            d = pikepdf.Dictionary()
            oc_props["/D"] = d

        # Map existing /OFF refs back to indices via object id so we
        # can merge with the caller's set.
        existing_off = d.get("/OFF")
        existing_ids: set[int] = set()
        if existing_off is not None:
            ocg_objs = [ocgs[i] for i in range(len(ocgs))]
            for ref in existing_off:
                for i, ocg in enumerate(ocg_objs):
                    if ref.objgen == ocg.objgen:
                        existing_ids.add(i)
                        break

        new_off_ids = (existing_ids | off) - on
        new_off_refs = [ocgs[i] for i in sorted(new_off_ids)]
        d["/OFF"] = pikepdf.Array(new_off_refs)

        buf = io.BytesIO()
        pdf.save(buf)
        return buf.getvalue()


def render_page_to_image(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 300,
    ocg_on: list[int] | None = None,
    ocg_off: list[int] | None = None,
) -> bytes:
    """Render a single PDF page to PNG image bytes.

    Args:
        pdf_bytes: Raw PDF file bytes.
        page_num: 1-indexed page number.
        dpi: Resolution for rendering.
        ocg_on: Optional OCG indices to force visible. The PDF is
            pre-processed via :func:`_apply_ocg_overrides` so poppler
            honours the override at render time.
        ocg_off: Optional OCG indices to force hidden.

    Returns:
        PNG image bytes.

    Raises:
        RuntimeError: If no rendering backend is available.
        OCGError: ``ocg_on`` / ``ocg_off`` cannot be applied
            (non-layered PDF, index out of range, or conflict).
    """
    if _HAS_PDF2IMAGE:
        if ocg_on or ocg_off:
            pdf_bytes = _apply_ocg_overrides(pdf_bytes, ocg_on, ocg_off)
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
