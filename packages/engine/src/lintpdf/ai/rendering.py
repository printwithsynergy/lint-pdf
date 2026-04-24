"""Page rendering utility for AI analyzers that need rasterized page images."""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess
import tempfile

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


# Ghostscript availability — required for overprint-faithful previews of
# spot-color / packaging artwork. The engine Dockerfile installs
# ``ghostscript`` alongside ``poppler-utils``; fall back to poppler when
# ``gs`` is missing (dev laptops, CI without GS) at the cost of losing
# overprint simulation in the preview tile.
_gs_checked = False
_has_gs = False


def _has_ghostscript() -> bool:
    global _gs_checked, _has_gs
    if _gs_checked:
        return _has_gs
    _gs_checked = True
    _has_gs = shutil.which("gs") is not None
    if not _has_gs:
        logger.warning(
            "Ghostscript ('gs') not on PATH — preview tiles will use pdftoppm "
            "without overprint simulation. Spot-color artwork will render "
            "incorrectly. Install ghostscript for faithful previews.",
        )
    return _has_gs


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


def _render_page_via_ghostscript(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int,
) -> bytes:
    """Rasterize one page with Ghostscript + overprint simulation on.

    Packaging PDFs routinely combine spot inks with overprint set true
    (``/OP true`` / ``/op true``) — the result is the classic ink
    stack-up where a yellow "AMALGAM" on top of a blue splatter actually
    blends rather than knocking out. pdftoppm (poppler) ignores
    overprint in RGB mode, so a 9-spot label renders as a single tinted
    page, which is what surfaced on the Amalgam_Catalyst viewer tile.

    Ghostscript's ``png16m`` device + ``-dSimulateOverprint=true``
    (falling back to ``-dOverprint=/simulate`` on older builds) honours
    overprint against the intended process/spot stack, so the preview
    matches what would actually print. Slightly slower than pdftoppm on
    simple CMYK (roughly 1.5-2x), but the tile cache absorbs the extra
    cost - this only runs on cache miss.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        png_path = os.path.join(tmpdir, "page.png")
        with open(pdf_path, "wb") as fh:
            fh.write(pdf_bytes)

        # WS-17A — ``-sColorConversionStrategy=RGB`` forces every
        # device colour space (DeviceCMYK, DeviceN, Separation
        # alternates) to convert to DeviceRGB at composition time.
        # Without it, Ghostscript can render a spot-heavy page (the
        # 2026-04-23 Test3 DailyFiber 10-up + Amalgam_Catalyst
        # surfaces) as a single tinted shade because the page's
        # Separation alternates collapse onto the same intermediate
        # CMYK channel. ``-dRenderIntent=0`` (perceptual) keeps
        # gamut mapping smooth so highly saturated spots stay
        # distinguishable in the RGB preview.
        #
        # ``-dSimulateOverprint=true`` is the current flag; older GS
        # builds (9.x) only honour ``-dOverprint=/simulate``. Passing
        # both is safe — unknown flags are ignored.
        cmd = [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-sDEVICE=png16m",
            "-sColorConversionStrategy=RGB",
            "-dRenderIntent=0",
            "-dSimulateOverprint=true",
            "-dOverprint=/simulate",
            "-dTextAlphaBits=4",
            "-dGraphicsAlphaBits=4",
            f"-r{dpi}",
            f"-dFirstPage={page_num}",
            f"-dLastPage={page_num}",
            f"-sOutputFile={png_path}",
            pdf_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Ghostscript render timed out for page {page_num}",
            ) from exc
        if proc.returncode != 0:
            stderr = proc.stderr.decode(errors="replace")[:500]
            raise RuntimeError(
                f"Ghostscript render failed (rc={proc.returncode}): {stderr}"
            )
        if not os.path.exists(png_path):
            raise RuntimeError(
                f"Ghostscript produced no output for page {page_num}"
            )
        with open(png_path, "rb") as fh:
            return fh.read()


def render_page_to_image(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 300,
    ocg_on: list[int] | None = None,
    ocg_off: list[int] | None = None,
    *,
    simulate_overprint: bool = True,
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
        simulate_overprint: When True (default), use Ghostscript's
            ``-dSimulateOverprint=true`` so spot-color / overprinting
            artwork renders the way it would print. Falls through to
            pdftoppm when Ghostscript isn't installed. Set False to
            force the legacy pdftoppm path (e.g. in unit tests that
            can't rely on GS being present).

    Returns:
        PNG image bytes.

    Raises:
        RuntimeError: If no rendering backend is available.
        OCGError: ``ocg_on`` / ``ocg_off`` cannot be applied
            (non-layered PDF, index out of range, or conflict).
    """
    if ocg_on or ocg_off:
        pdf_bytes = _apply_ocg_overrides(pdf_bytes, ocg_on, ocg_off)

    if simulate_overprint and _has_ghostscript():
        try:
            return _render_page_via_ghostscript(pdf_bytes, page_num, dpi)
        except RuntimeError:
            # Don't give up entirely — fall back to pdftoppm so the
            # viewer still shows *something* even if GS hiccuped on a
            # single page. Overprint fidelity is better than a 500.
            logger.exception(
                "Ghostscript render failed; falling back to pdftoppm for page %d",
                page_num,
            )

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


def render_isolated_layer_tile(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int,
    layer_index: int,
    all_layer_indices: list[int],
) -> bytes:
    """Render a single OCG (layer) in isolation against a transparent
    background. WS-17C uses these per-layer tiles to give the viewer
    instant layer-toggle response — the browser fetches one PNG per
    layer once, then composites the active subset client-side via
    canvas ``source-over`` blending. Toggling a layer afterwards is
    a single canvas redraw with no API round-trip.

    The "isolation" is achieved by hiding every OCG except the
    requested one. Ghostscript ``pngalpha`` device emits an RGBA
    image, so non-layer pixels (and gaps inside the layer's
    geometry) come back transparent — exactly what the browser
    compositor needs.

    Args:
        pdf_bytes: Raw PDF file bytes.
        page_num: 1-indexed page number.
        dpi: Render resolution.
        layer_index: Index into ``/Root/OCProperties/OCGs`` for the
            layer to keep visible. Same indices as
            :func:`viewer.list_layers` returns as ``ocg_index``.
        all_layer_indices: Every OCG index on the page; everything
            other than ``layer_index`` is forced hidden.

    Returns:
        PNG bytes (RGBA, transparent where the layer doesn't paint).

    Raises:
        OCGError: ``layer_index`` is out of range / not an OCG.
        RuntimeError: Ghostscript not available or failed.
    """
    if not _has_ghostscript():
        raise RuntimeError(
            "render_isolated_layer_tile requires Ghostscript. "
            "Install ghostscript >= 9.50."
        )
    if layer_index not in all_layer_indices:
        raise OCGError(
            f"layer_index={layer_index} not in all_layer_indices={all_layer_indices}"
        )

    ocg_off = [i for i in all_layer_indices if i != layer_index]
    pdf_isolated = _apply_ocg_overrides(pdf_bytes, [layer_index], ocg_off)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        png_path = os.path.join(tmpdir, "page.png")
        with open(pdf_path, "wb") as fh:
            fh.write(pdf_isolated)

        # ``pngalpha`` keeps non-painted pixels transparent so the
        # browser compositor can layer multiple isolated tiles via
        # ``ctx.drawImage`` without darkening accumulating areas.
        cmd = [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-sDEVICE=pngalpha",
            "-sColorConversionStrategy=RGB",
            "-dRenderIntent=0",
            "-dSimulateOverprint=true",
            "-dOverprint=/simulate",
            "-dTextAlphaBits=4",
            "-dGraphicsAlphaBits=4",
            f"-r{dpi}",
            f"-dFirstPage={page_num}",
            f"-dLastPage={page_num}",
            f"-sOutputFile={png_path}",
            pdf_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Ghostscript layer-tile render timed out for page "
                f"{page_num} layer {layer_index}",
            ) from exc
        if proc.returncode != 0:
            stderr = proc.stderr.decode(errors="replace")[:500]
            raise RuntimeError(
                f"Ghostscript layer-tile render failed (rc={proc.returncode}): {stderr}"
            )
        if not os.path.exists(png_path):
            raise RuntimeError(
                f"Ghostscript produced no output for page {page_num} layer {layer_index}"
            )
        with open(png_path, "rb") as fh:
            return fh.read()


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
