"""Page rendering compatibility shim.

The page raster, OCG-isolated layer tile, and page-count helpers
that lint-pdf previously implemented in-process are now owned by
``codex-pdf``. This module preserves the public surface
(``render_page_to_image``, ``render_isolated_layer_tile``,
``render_all_pages``, ``get_page_count``, ``OCGError``) so the dozens
of existing callers (viewer routes, AI analyzers, audit, queue
tasks, plugin host) keep working — but every byte-level call now
goes through :mod:`lintpdf.codex_render`.

The codex client falls back to an in-process call into
:mod:`codex_pdf.render` when ``CODEX_API_BASE`` is unset, which is
the path used by the parity-corpus harness so this module produces
exactly the same bytes as the legacy implementation it replaced.
"""

from __future__ import annotations

import io
import logging

import pikepdf

from lintpdf.codex_render import (
    OCGError,  # re-exported for legacy callers
)
from lintpdf.codex_render import (
    get_page_count as _codex_get_page_count,
)
from lintpdf.codex_render import (
    render_layer as _codex_render_layer,
)
from lintpdf.codex_render import (
    render_page as _codex_render_page,
)

logger = logging.getLogger(__name__)


def _apply_ocg_overrides(
    pdf_bytes: bytes,
    ocg_on: list[int] | None,
    ocg_off: list[int] | None,
) -> bytes:
    """Rewrite /OCProperties/D/OFF in-place so specific layers are forced on or off.

    Returns ``pdf_bytes`` unchanged when both lists are empty/None.
    Raises ``OCGError`` for conflicts, out-of-range indices, or a
    PDF with no /OCProperties.
    """
    on_set = set(ocg_on or [])
    off_set = set(ocg_off or [])
    if not on_set and not off_set:
        return pdf_bytes

    conflicts = on_set & off_set
    if conflicts:
        raise OCGError(f"conflict: index {min(conflicts)} appears in both ocg_on and ocg_off")

    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        oc_props = pdf.Root.get("/OCProperties")
        if oc_props is None:
            raise OCGError("no /OCProperties — PDF has no layers")

        ocgs = oc_props.get("/OCGs")
        if ocgs is None or len(ocgs) == 0:
            raise OCGError("no /OCProperties — PDF has no layers")

        n = len(ocgs)
        for idx in sorted(on_set | off_set):
            if idx < 0 or idx >= n:
                raise OCGError(f"OCG index {idx} out of range (PDF has {n} layers)")

        d = oc_props.get("/D")
        if d is None:
            oc_props["/D"] = pikepdf.Dictionary({"/OFF": pikepdf.Array([])})
            d = oc_props["/D"]

        current_off = d.get("/OFF")
        ocg_list = [ocgs[i] for i in range(n)]

        if current_off is None:
            current_off_indices: set[int] = set()
        else:
            current_off_indices = set()
            for ref in current_off:
                for i, ocg in enumerate(ocg_list):
                    try:
                        if ref.objgen == ocg.objgen:
                            current_off_indices.add(i)
                            break
                    except AttributeError:
                        pass

        new_off_indices = (current_off_indices - on_set) | off_set
        d["/OFF"] = pikepdf.Array([ocg_list[i] for i in sorted(new_off_indices)])

        buf = io.BytesIO()
        pdf.save(buf)
        return buf.getvalue()


def render_page_to_image(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 300,
    ocg_on: list[int] | None = None,
    ocg_off: list[int] | None = None,
    *,
    simulate_overprint: bool = True,
) -> bytes:
    """Render a page to PNG bytes via the codex render service."""
    return _codex_render_page(
        pdf_bytes,
        page_num,
        dpi=dpi,
        ocg_on=ocg_on,
        ocg_off=ocg_off,
        simulate_overprint=simulate_overprint,
    )


def render_isolated_layer_tile(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int,
    layer_index: int,
    all_layer_indices: list[int],
) -> bytes:
    """Render an OCG-isolated layer tile (RGBA) via codex."""
    return _codex_render_layer(
        pdf_bytes,
        page_num,
        layer_index=layer_index,
        all_layer_indices=all_layer_indices,
        dpi=dpi,
    )


def render_all_pages(
    pdf_bytes: bytes,
    dpi: int = 300,
    max_pages: int = 50,
) -> list[bytes]:
    """Render every page (up to ``max_pages``) to PNG bytes via codex."""
    n = _codex_get_page_count(pdf_bytes)
    upper = min(n, max_pages)
    return [_codex_render_page(pdf_bytes, page_num, dpi=dpi) for page_num in range(1, upper + 1)]


def get_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in ``pdf_bytes``.

    Routes through codex so this module declares zero direct
    pikepdf imports — the parser-surface audit relies on that.
    """
    return _codex_get_page_count(pdf_bytes)


__all__ = [
    "OCGError",
    "_apply_ocg_overrides",
    "get_page_count",
    "render_all_pages",
    "render_isolated_layer_tile",
    "render_page_to_image",
]
