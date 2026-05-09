"""Separation channel rendering — codex-backed.

The byte-level Ghostscript ``tiffsep`` decomposition that was once
implemented here lives in :mod:`codex_pdf.render.separations` now.
This module keeps the per-tenant S3 cache wrappers and public API
(``list_separations``, ``render_separation_channel``,
``render_tac_heatmap``, ``sample_densitometer``,
``render_composite_via_separations``) so existing lint-pdf callers
(viewer routes, queue tasks, audit, AI helpers) keep their imports
unchanged.

Caching layout (unchanged):

- One PNG per (tenant, job, page, dpi, channel) under
  ``tiles/p{page}_d{dpi}_ch_{channel_slug}.png`` in S3.
- Cache hit → serve cached bytes; cache miss → call codex render
  and write result back to S3.

This means lint-pdf no longer shells out to ``gs`` directly; the
parser-surface audit (``scripts/parser_surface_audit.py``) enforces
the boundary on every CI run.
"""

from __future__ import annotations

import io
import logging
import re
from typing import TYPE_CHECKING, TypedDict

from PIL import Image

from lintpdf.codex_render import (
    list_separations as _codex_list_separations,
)
from lintpdf.codex_render import (
    render_heatmap as _codex_render_heatmap,
)
from lintpdf.codex_render import (
    render_separation_channel as _codex_render_separation_channel,
)
from lintpdf.codex_render import (
    render_separations as _codex_render_separations,
)
from lintpdf.codex_render import (
    sample_density as _codex_sample_density,
)

if TYPE_CHECKING:
    import numpy as np

    from lintpdf.api.storage import StorageBackend

logger = logging.getLogger(__name__)


PROCESS_CHANNEL_COLORS: dict[str, tuple[int, int, int]] = {
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Yellow": (255, 255, 0),
    "Black": (0, 0, 0),
}

PROCESS_CHANNEL_ORDER = ["Cyan", "Magenta", "Yellow", "Black"]


class TacRun(TypedDict):
    """PDF-point bbox of a text run with its mean TAC%."""

    x0: float
    y0: float
    x1: float
    y1: float
    mean_tac: float
    limit: float
    exceeds: bool


class TacHeatmap(TypedDict):
    """Result of :func:`render_tac_heatmap`."""

    png: bytes
    runs: list[TacRun]


# ---------------------------------------------------------------------------
# Cache key helpers — unchanged. They drive the per-tenant S3 cache
# layer that wraps codex render results.
# ---------------------------------------------------------------------------


def _safe_channel_slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def channel_cache_key(tenant_id: str, job_id: str, page_num: int, dpi: int, channel: str) -> str:
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}_ch_{_safe_channel_slug(channel)}.png"


def tac_runs_cache_key(tenant_id: str, job_id: str, page_num: int, dpi: int, tac_limit: int) -> str:
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}_tac_l{tac_limit}_runs.json"


# ---------------------------------------------------------------------------
# Pixel ↔ PNG helpers (kept local; no PDF parsing).
# ---------------------------------------------------------------------------


def _pct_array_from_png_bytes(png_bytes: bytes) -> np.ndarray:
    """Load a cached channel PNG back into a 0-100 percent ink array."""
    import numpy as np

    img = Image.open(io.BytesIO(png_bytes)).convert("L")
    arr = 255 - np.array(img, dtype=np.float32)
    return arr * (100.0 / 255.0)


def _pct_array_to_png_bytes(arr: np.ndarray) -> bytes:
    """Encode a 0-100% ink array as a tiffsep-native PNG (0 = full ink)."""
    import numpy as np

    inked = np.clip(arr, 0.0, 100.0) * (255.0 / 100.0)
    gray = (255.0 - inked).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(gray, mode="L").save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def list_separations(pdf_bytes: bytes) -> list[dict]:
    """Return ink channels actually present in the PDF (codex-backed)."""
    return _codex_list_separations(pdf_bytes)


def get_cmyk_channels(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int,
    *,
    tenant_id: str | None = None,
    job_id: str | None = None,
    storage: StorageBackend | None = None,
) -> tuple[list[np.ndarray], list[str]]:
    """Return ``(cmyk_arrays_0_100_percent, channel_names)`` for a page.

    Codex returns the same tiffsep-native PNG bytes the legacy path
    produced; we decode them locally to numpy arrays so the densitometer
    and TAC heatmap callers don't change shape.
    """
    cache_ok = bool(tenant_id and job_id and storage)
    if cache_ok and tenant_id and job_id and storage:
        cached_arrays: list[np.ndarray] = []
        for ch in PROCESS_CHANNEL_ORDER:
            key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch)
            try:
                raw = storage.download_raw(key)
            except Exception:
                raw = None
            if raw is None:
                cached_arrays = []
                break
            cached_arrays.append(_pct_array_from_png_bytes(raw))
        if len(cached_arrays) == 4:
            return cached_arrays, list(PROCESS_CHANNEL_ORDER)

    arrays: list[np.ndarray] = []
    for ch in PROCESS_CHANNEL_ORDER:
        png = _codex_render_separation_channel(pdf_bytes, page_num, ch, dpi=dpi)
        if png is None:
            raise RuntimeError(f"CMYK channel '{ch}' not found via codex")
        arrays.append(_pct_array_from_png_bytes(png))

    if cache_ok and tenant_id and job_id and storage:
        for ch, arr in zip(PROCESS_CHANNEL_ORDER, arrays, strict=True):
            key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch)
            try:
                storage.upload_raw(key, _pct_array_to_png_bytes(arr), content_type="image/png")
            except Exception:
                logger.warning("get_cmyk_channels: failed to cache channel %s key=%s", ch, key)

    return arrays, list(PROCESS_CHANNEL_ORDER)


def render_separation_channel(
    pdf_bytes: bytes,
    page_num: int,
    channel: str,
    dpi: int = 150,
    *,
    tenant_id: str | None = None,
    job_id: str | None = None,
    storage: StorageBackend | None = None,
) -> bytes:
    """Render a single separation channel as a grayscale PNG (codex-backed)."""
    cache_ok = bool(tenant_id and job_id and storage)

    if cache_ok and tenant_id and job_id and storage:
        key = channel_cache_key(tenant_id, job_id, page_num, dpi, channel)
        try:
            raw = storage.download_raw(key)
        except Exception:
            raw = None
        if raw is not None:
            return raw

    png = _codex_render_separation_channel(pdf_bytes, page_num, channel, dpi=dpi)
    if png is None:
        raise RuntimeError(f"Channel '{channel}' not found in codex output for page {page_num}")

    if cache_ok and tenant_id and job_id and storage:
        key = channel_cache_key(tenant_id, job_id, page_num, dpi, channel)
        try:
            storage.upload_raw(key, png, content_type="image/png")
        except Exception:
            logger.warning("render_separation_channel: failed to cache %s key=%s", channel, key)

    return png


def render_tac_heatmap(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 150,
    tac_limit: float = 300,
    *,
    tenant_id: str | None = None,
    job_id: str | None = None,
    storage: StorageBackend | None = None,
) -> TacHeatmap:
    """Generate a TAC heatmap PNG plus per-text-run TAC metadata (codex-backed)."""
    res = _codex_render_heatmap(pdf_bytes, page_num, dpi=dpi, tac_limit=tac_limit)
    runs: list[TacRun] = [TacRun(**run) for run in res["runs"]]  # type: ignore[typeddict-item]
    return TacHeatmap(png=res["png"], runs=runs)


def sample_densitometer(
    pdf_bytes: bytes,
    page_num: int,
    *,
    x: float,
    y: float,
    page_w: float,
    page_h: float,
    dpi: int = 300,
    tac_limit: float = 300,
    tenant_id: str | None = None,
    job_id: str | None = None,
    storage: StorageBackend | None = None,
) -> dict[str, object]:
    """Sample per-channel ink coverage + TAC at a PDF point (codex-backed)."""
    return _codex_sample_density(
        pdf_bytes,
        page_num,
        x=x,
        y=y,
        page_w=page_w,
        page_h=page_h,
        dpi=dpi,
        tac_limit=tac_limit,
    )


# ---------------------------------------------------------------------------
# Subtractive ink model — used by the software composite. Kept here
# because viewer-side SeparationCanvas mirrors the same coefficients
# and we want the lint preview to converge with the browser preview.
# ---------------------------------------------------------------------------


_INK_ABSORPTION_RGB: dict[str, tuple[int, int, int]] = {
    "Cyan": (255, 0, 0),
    "Magenta": (0, 255, 0),
    "Yellow": (0, 0, 255),
    "Black": (255, 255, 255),
}


def _spot_absorption_rgb(name: str) -> tuple[int, int, int]:
    lowered = name.strip().lower()
    exact: dict[str, tuple[int, int, int]] = {
        "black": (255, 255, 255),
        "k": (255, 255, 255),
        "cyan": (255, 0, 0),
        "c": (255, 0, 0),
        "magenta": (0, 255, 0),
        "m": (0, 255, 0),
        "yellow": (0, 0, 255),
        "y": (0, 0, 255),
        "white": (0, 0, 0),
    }
    if lowered in exact:
        return exact[lowered]

    patterns: list[tuple[str, tuple[int, int, int]]] = [
        ("cut", (0, 200, 200)),
        ("dieline", (0, 200, 200)),
        ("crease", (0, 200, 200)),
        ("perf", (0, 200, 200)),
        ("fold", (0, 200, 200)),
        ("foil", (128, 128, 128)),
        ("silver", (128, 128, 128)),
        ("gold", (40, 80, 200)),
        ("copper", (40, 80, 150)),
        ("varnish", (200, 200, 200)),
        ("matte", (200, 200, 200)),
        ("beige", (30, 80, 140)),
        ("tan", (30, 80, 140)),
        ("buff", (30, 60, 120)),
        ("cream", (10, 30, 80)),
        ("ivory", (10, 30, 80)),
        ("red", (0, 200, 200)),
        ("orange", (0, 150, 230)),
        ("blue", (220, 140, 0)),
        ("navy", (220, 140, 0)),
        ("green", (220, 40, 210)),
        ("teal", (220, 80, 120)),
        ("mint", (220, 80, 120)),
        ("purple", (120, 220, 80)),
        ("violet", (120, 220, 80)),
        ("pink", (40, 200, 100)),
        ("rose", (40, 200, 100)),
        ("brown", (80, 140, 200)),
        ("grey", (128, 128, 128)),
        ("gray", (128, 128, 128)),
        ("slate", (128, 128, 128)),
    ]
    for key, coef in patterns:
        if key in lowered:
            return coef

    h = 0
    for ch in name:
        h = ord(ch) + ((h << 5) - h)
    hue = abs(h) % 360
    s, light = 0.6, 0.45
    c = (1 - abs(2 * light - 1)) * s
    x = c * (1 - abs(((hue / 60) % 2) - 1))
    m = light - c / 2
    if hue < 60:
        r, g, b = c, x, 0
    elif hue < 120:
        r, g, b = x, c, 0
    elif hue < 180:
        r, g, b = 0, c, x
    elif hue < 240:
        r, g, b = 0, x, c
    elif hue < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    ink_r = round((r + m) * 255)
    ink_g = round((g + m) * 255)
    ink_b = round((b + m) * 255)
    return (255 - ink_r, 255 - ink_g, 255 - ink_b)


def render_composite_via_separations(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 150,
    *,
    tenant_id: str | None = None,
    job_id: str | None = None,
    storage: StorageBackend | None = None,
    rgba: bool = False,
) -> bytes | None:
    """Software-composite the page from per-channel separations (codex-backed).

    Mirrors the legacy subtractive-ink model exactly: every 1 % of
    tint applied to a plate removes ``absorption_coef * 0.01`` from
    the paper's reflected light per RGB channel.
    """
    import numpy as np

    cache_ok = bool(tenant_id and job_id and storage)

    try:
        spot_names = [s["name"] for s in list_separations(pdf_bytes) if s.get("type") == "spot"]
    except Exception:
        spot_names = []

    plates: list[tuple[str, np.ndarray]] = []
    if rgba:
        cache_ok = False
    if cache_ok and tenant_id and job_id and storage:
        cmyk_ok = True
        for ch in PROCESS_CHANNEL_ORDER:
            key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch)
            try:
                raw = storage.download_raw(key)
            except Exception:
                raw = None
            if raw is None:
                cmyk_ok = False
                break
            plates.append((ch, _pct_array_from_png_bytes(raw)))
        if cmyk_ok and spot_names:
            for spot in spot_names:
                key = channel_cache_key(tenant_id, job_id, page_num, dpi, spot)
                try:
                    raw = storage.download_raw(key)
                except Exception:
                    raw = None
                if raw is None:
                    plates = []
                    break
                plates.append((spot, _pct_array_from_png_bytes(raw)))
        elif not cmyk_ok:
            plates = []

    if not plates:
        try:
            seps = _codex_render_separations(pdf_bytes, page_num, dpi=dpi)
        except Exception:
            logger.exception("render_composite_via_separations: codex render failed")
            return None
        for ch in seps.get("channels", []):
            png = ch.get("png")
            if not png:
                continue
            plates.append((ch["name"], _pct_array_from_png_bytes(png)))

        if cache_ok and tenant_id and job_id and storage:
            for ch_name, arr in plates:
                key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch_name)
                try:
                    storage.upload_raw(key, _pct_array_to_png_bytes(arr), content_type="image/png")
                except Exception:
                    logger.warning("render_composite_via_separations: failed to cache %s", ch_name)

    if not plates:
        return None

    height, width = plates[0][1].shape
    rgb = np.full((height, width, 3), 255.0, dtype=np.float32)

    for name, plate in plates:
        absorption = (
            _INK_ABSORPTION_RGB.get(name)
            if name in PROCESS_CHANNEL_ORDER
            else _spot_absorption_rgb(name)
        )
        if absorption is None:
            continue
        tint = np.clip(plate, 0.0, 100.0) / 100.0
        for channel_idx, coef in enumerate(absorption):
            rgb[:, :, channel_idx] *= 1.0 - (tint * (coef / 255.0))

    rgb_uint8 = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
    buf = io.BytesIO()
    if rgba:
        max_ink = np.zeros((rgb.shape[0], rgb.shape[1]), dtype=np.float32)
        for _name, plate in plates:
            np.maximum(max_ink, np.clip(plate, 0.0, 100.0), out=max_ink)
        alpha = (max_ink * 2.55).astype(np.uint8)
        rgba_uint8 = np.dstack([rgb_uint8, alpha])
        Image.fromarray(rgba_uint8, mode="RGBA").save(buf, format="PNG")
    else:
        Image.fromarray(rgb_uint8, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()
