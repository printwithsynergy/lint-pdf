"""Codex render adapter for lint-pdf.

Single seam between lint-pdf and the codex render engine. Every
non-export raster path in lint-pdf goes through this module — direct
``pikepdf.open`` / Ghostscript subprocess calls outside the export
report writers are forbidden by ``scripts/parser_surface_audit.py``.

The adapter wraps :class:`codex_pdf.client.HttpClient`, which by
default uses HTTP when ``CODEX_API_BASE`` is configured and falls
back to in-process calls into :mod:`codex_pdf.render` otherwise.
That means parity tests can run with no live codex server, and
production deploys can swap to HTTP by setting one env var.
"""

from __future__ import annotations

import io
import logging
import os
from functools import lru_cache
from typing import Any

from codex_pdf.client import HttpClient

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_client() -> HttpClient:
    """Process-wide codex client singleton."""
    return HttpClient(
        route_mode=os.getenv("CODEX_ROUTE_MODE"),
        plant=os.getenv("CODEX_PLANT"),
        affinity_key=os.getenv("CODEX_AFFINITY_KEY"),
    )


# ---------------------------------------------------------------------------
# Public render surface (codex-backed).
# ---------------------------------------------------------------------------


def render_page(
    pdf_bytes: bytes,
    page_num: int,
    *,
    dpi: int = 300,
    ocg_on: list[int] | None = None,
    ocg_off: list[int] | None = None,
    simulate_overprint: bool = True,
) -> bytes:
    """Render a single page to PNG via codex."""
    return get_client().render_page(
        pdf_bytes,
        page=page_num,
        dpi=dpi,
        ocg_on=ocg_on,
        ocg_off=ocg_off,
        simulate_overprint=simulate_overprint,
    )


def render_layer(
    pdf_bytes: bytes,
    page_num: int,
    *,
    layer_index: int,
    all_layer_indices: list[int],
    dpi: int = 150,
) -> bytes:
    return get_client().render_layer(
        pdf_bytes,
        page=page_num,
        layer_index=layer_index,
        all_layer_indices=all_layer_indices,
        dpi=dpi,
    )


def list_separations(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Return the ink channels actually present in the PDF.

    Calls into codex's render core directly. There is no separate
    HTTP endpoint for the inventory because it's a fast pikepdf-only
    scan that the codex client also uses internally; routing it
    through HTTP would add round-trip latency for every page query.
    """
    from codex_pdf.render.separations import list_separations as _ls

    return _ls(pdf_bytes)


def render_separations(
    pdf_bytes: bytes,
    page_num: int,
    *,
    dpi: int = 150,
) -> dict[str, Any]:
    res = get_client().render_separations(pdf_bytes, page=page_num, dpi=dpi)
    return {
        "page_num": res.page_num,
        "dpi": res.dpi,
        "channels": list(res.channels),
    }


def render_separation_channel(
    pdf_bytes: bytes,
    page_num: int,
    channel: str,
    *,
    dpi: int = 150,
) -> bytes | None:
    """Render a single channel as a grayscale PNG (or None if absent)."""
    res = render_separations(pdf_bytes, page_num, dpi=dpi)
    for ch in res["channels"]:
        if str(ch.get("name", "")).lower() == channel.lower():
            return ch.get("png")
    return None


def render_heatmap(
    pdf_bytes: bytes,
    page_num: int,
    *,
    dpi: int = 150,
    tac_limit: float = 300,
) -> dict[str, Any]:
    res = get_client().render_heatmap(pdf_bytes, page=page_num, dpi=dpi, tac_limit=tac_limit)
    return {"png": res.png, "runs": list(res.runs)}


def sample_color(
    pdf_bytes: bytes,
    page_num: int,
    *,
    x: float,
    y: float,
    page_w: float | None = None,
    page_h: float | None = None,
    dpi: int = 300,
) -> dict[str, Any]:
    res = get_client().sample_color(
        pdf_bytes, page=page_num, x=x, y=y, page_w=page_w, page_h=page_h, dpi=dpi
    )
    return {
        "x": res.x,
        "y": res.y,
        "dpi": res.dpi,
        "rgb": list(res.rgb),
        "hex": res.hex,
    }


def sample_density(
    pdf_bytes: bytes,
    page_num: int,
    *,
    x: float,
    y: float,
    page_w: float | None = None,
    page_h: float | None = None,
    dpi: int = 300,
    tac_limit: float = 300,
) -> dict[str, Any]:
    res = get_client().sample_density(
        pdf_bytes,
        page=page_num,
        x=x,
        y=y,
        page_w=page_w,
        page_h=page_h,
        dpi=dpi,
        tac_limit=tac_limit,
    )
    return {
        "x": res.x,
        "y": res.y,
        "dpi": res.dpi,
        "channels": list(res.channels),
        "tac": res.tac,
        "tac_limit": res.tac_limit,
        "limit_exceeded": res.limit_exceeded,
    }


def walk_content_stream(
    pdf_bytes: bytes,
    *,
    page_num: int = 1,
) -> dict[str, Any]:
    return get_client().walk_content_stream(pdf_bytes, page=page_num)


def eval_type4(program: str, *, inputs: list[float] | None = None) -> list[float] | None:
    """Evaluate a PDF Type-4 PostScript function via codex.

    Codex owns the PostScript byte-level evaluation surface. This
    helper exists so analyzers (e.g. ``lintpdf.primitives.color_space``)
    have a clean import target — the parser-surface audit forbids
    direct ``subprocess gs`` invocations elsewhere in lint.

    Returns the post-execution stack as a list of floats, or ``None``
    if codex couldn't verify (Ghostscript missing, timeout, parse
    error). Fast-path constant programs are resolved synchronously
    without a subprocess.
    """
    out = get_client().eval_type4(program, list(inputs or []))
    return out.get("result")


# ---------------------------------------------------------------------------
# Read-only PDF facts that lint-pdf reaches through codex too.
#
# These intentionally call the codex render core in-process even when
# the client is in HTTP mode — they're cheap pikepdf-only operations
# that would otherwise force a network round-trip for every viewer
# tile mint. The codex contract guarantees identical results because
# the same code paths run on the server.
# ---------------------------------------------------------------------------


def get_page_count(pdf_bytes: bytes) -> int:
    from codex_pdf.render._common import get_page_count as _gpc

    return _gpc(pdf_bytes)


def get_page_media_box(pdf_bytes: bytes, page_num: int) -> tuple[float, float, float, float]:
    from codex_pdf.render._common import get_page_media_box as _mb

    return _mb(pdf_bytes, page_num)


# ---------------------------------------------------------------------------
# OCGError re-export so existing handlers (viewer routes etc.) keep
# their `except OCGError:` shape.
# ---------------------------------------------------------------------------


from codex_pdf.render._common import OCGError  # noqa: E402


def _bytes_io(data: bytes) -> io.BytesIO:  # legacy helper retained for callers
    return io.BytesIO(data)


__all__ = [
    "OCGError",
    "eval_type4",
    "get_client",
    "get_page_count",
    "get_page_media_box",
    "list_separations",
    "render_heatmap",
    "render_layer",
    "render_page",
    "render_separation_channel",
    "render_separations",
    "sample_color",
    "sample_density",
    "walk_content_stream",
]
