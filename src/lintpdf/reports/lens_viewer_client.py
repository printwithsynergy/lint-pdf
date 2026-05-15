"""HTTP client for delegating viewer-rendering calls to lens-server.

Viewer-rendering capabilities (separation channel rasters, composite page
images, TAC heatmap PNGs, densitometer) belong to lens-server — not
lint-pdf.  This module is the thin HTTP adapter: it uploads the PDF once
per job (lens-server caches by jobId), then calls the appropriate
endpoint and returns the raw bytes.

S3 caching lives in the *viewer routes*, not here.  This client is
stateless: every call either hits lens-server or raises, and the caller
decides whether to consult S3 first.

Environment variables:
    LENS_SERVER_URL  Base URL of the running lens-server instance
                     (default: http://localhost:3001).
    LENS_VIEWER_TIMEOUT  Per-request timeout in seconds (default: 30).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_LENS_URL = os.environ.get("LENS_SERVER_URL", "http://localhost:3001").rstrip("/")
_TIMEOUT = int(os.environ.get("LENS_VIEWER_TIMEOUT", "30"))


def _session():
    import requests

    s = requests.Session()
    s.headers["User-Agent"] = "lintpdf-viewer-client/1.0"
    return s


# ---------------------------------------------------------------------------
# Source registration
# ---------------------------------------------------------------------------


def ensure_pdf_registered(job_id: str, pdf_bytes: bytes) -> None:
    """Upload *pdf_bytes* to lens-server under *job_id*.

    Idempotent — re-uploading overwrites the stored source and clears the
    lens-server render cache for that job, which is fine: the S3 tile
    cache in lint-pdf persists across lens-server restarts, so we only pay
    the re-render cost when the S3 cache is also cold.
    """
    resp = _session().post(
        f"{_LENS_URL}/jobs/{job_id}/source",
        data=pdf_bytes,
        headers={"Content-Type": "application/pdf"},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Rendering endpoints
# ---------------------------------------------------------------------------


def list_channels(job_id: str, page_num: int, dpi: int = 72) -> list[dict[str, Any]]:
    """Return the ink channels available for *page_num* at *dpi*.

    Calls ``GET /jobs/{job_id}/channels`` and wraps the result in the same
    shape that ``codex_render.list_separations`` would return so callers can
    switch between the two without changing their parsing code.
    """
    resp = _session().get(
        f"{_LENS_URL}/jobs/{job_id}/channels",
        params={"page": page_num, "dpi": dpi},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    raw = resp.json()
    channels: list[str] = raw.get("channels", [])
    _cmyk = {"Cyan", "Magenta", "Yellow", "Black"}
    return [{"name": ch, "type": "process" if ch in _cmyk else "spot"} for ch in channels]


def get_channel_png(
    job_id: str,
    page_num: int,
    channel_name: str,
    dpi: int = 150,
) -> bytes:
    """Return a grayscale PNG for a single ink channel.

    Calls ``GET /jobs/{job_id}/channel/{channel_name}.png``.
    """
    from urllib.parse import quote

    resp = _session().get(
        f"{_LENS_URL}/jobs/{job_id}/channel/{quote(channel_name, safe='')}.png",
        params={"page": page_num, "dpi": dpi},
        timeout=_TIMEOUT,
    )
    if resp.status_code == 404:
        raise RuntimeError(
            f"Channel '{channel_name}' not available on page {page_num} (lens-server 404)."
        )
    resp.raise_for_status()
    return resp.content


def get_composite_png(
    job_id: str,
    page_num: int,
    dpi: int = 150,
) -> bytes:
    """Return a composite RGB PNG for a page.

    Calls ``GET /jobs/{job_id}/page/{page_num}.png``.
    """
    resp = _session().get(
        f"{_LENS_URL}/jobs/{job_id}/page/{page_num}.png",
        params={"dpi": dpi},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.content


def get_tac_png(
    job_id: str,
    page_num: int,
    dpi: int = 150,
    tac_limit: float = 300,
) -> bytes:
    """Return an RGBA TAC heatmap PNG.

    Calls ``GET /jobs/{job_id}/tac.png``.
    """
    resp = _session().get(
        f"{_LENS_URL}/jobs/{job_id}/tac.png",
        params={"page": page_num, "dpi": dpi, "limit": tac_limit},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.content


def sample_density(
    job_id: str,
    page_num: int,
    *,
    x: float,
    y: float,
    page_width_pts: float,
    page_height_pts: float,
    dpi: int = 300,
    tac_limit: float = 300,
) -> dict[str, Any]:
    """Sample per-channel ink coverage + TAC at a PDF point.

    Calls ``POST /jobs/{job_id}/density`` and returns the response body.
    The returned dict has keys ``channels`` (list of {name, percent}),
    ``tac``, ``tac_limit``, ``limit_exceeded``.
    """
    resp = _session().post(
        f"{_LENS_URL}/jobs/{job_id}/density",
        json={
            "page": page_num,
            "x": x,
            "y": y,
            "pageWidthPts": page_width_pts,
            "pageHeightPts": page_height_pts,
            "dpi": dpi,
            "tacLimit": tac_limit,
        },
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
