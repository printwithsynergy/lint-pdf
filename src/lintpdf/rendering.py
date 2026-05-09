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

import logging

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
    "get_page_count",
    "render_all_pages",
    "render_isolated_layer_tile",
    "render_page_to_image",
]
