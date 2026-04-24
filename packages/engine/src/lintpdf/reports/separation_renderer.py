"""Separation channel rendering — decompose PDF into ink channels and TAC heatmaps."""

from __future__ import annotations

import io
import logging
import os
import re
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any, TypedDict

import pikepdf
from PIL import Image

if TYPE_CHECKING:
    import numpy as np

    from lintpdf.api.storage import StorageBackend

logger = logging.getLogger(__name__)

# Process ink channel colors for tinting
PROCESS_CHANNEL_COLORS = {
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Yellow": (255, 255, 0),
    "Black": (0, 0, 0),
}

PROCESS_CHANNEL_ORDER = ["Cyan", "Magenta", "Yellow", "Black"]


class TacRun(TypedDict):
    """PDF-point bbox of a text run with its mean TAC%."""

    # Coordinates in PDF points, origin **top-left** of the page (matching
    # pdftotext's output). Callers that want conventional lower-left must
    # flip Y themselves.
    x0: float
    y0: float
    x1: float
    y1: float
    mean_tac: float  # 0-400, percent
    limit: float  # the tac_limit in force when sampled
    exceeds: bool


class TacHeatmap(TypedDict):
    """Result of :func:`render_tac_heatmap` — image + per-run metadata."""

    png: bytes
    runs: list[TacRun]


def _safe_channel_slug(name: str) -> str:
    """File-safe slug for a channel name (matches the viewer cache keys)."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def channel_cache_key(tenant_id: str, job_id: str, page_num: int, dpi: int, channel: str) -> str:
    """S3 key for a cached separation channel PNG.

    Shared with the viewer routes so the densitometer, TAC heatmap, and
    the ``/channel/{name}`` tile endpoint all read / write the same
    bytes.
    """
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}_ch_{_safe_channel_slug(channel)}.png"


def tac_runs_cache_key(tenant_id: str, job_id: str, page_num: int, dpi: int, tac_limit: int) -> str:
    """S3 key for the per-run TAC metadata JSON sidecar."""
    return f"{tenant_id}/{job_id}/tiles/p{page_num}_d{dpi}_tac_l{tac_limit}_runs.json"


def _run_tiffsep(pdf_bytes: bytes, page_num: int, dpi: int, tmpdir: str) -> str:
    """Run Ghostscript ``tiffsep`` into ``tmpdir`` and return the output-base path.

    Centralised so the three consumers (channel tile, TAC heatmap,
    densitometer) can't drift on args.
    """
    pdf_path = os.path.join(tmpdir, "input.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    output_base = os.path.join(tmpdir, "sep")
    cmd = [
        "gs",
        "-q",
        "-sDEVICE=tiffsep",
        "-dNOPAUSE",
        "-dBATCH",
        f"-r{dpi}",
        f"-dFirstPage={page_num}",
        f"-dLastPage={page_num}",
        f"-sOutputFile={output_base}%d.tif",
        pdf_path,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        logger.error("Ghostscript tiffsep failed: %s", stderr)
        raise RuntimeError(f"Ghostscript separation failed: {stderr[:500]}")
    return output_base


def _pct_array_from_tiff(tif_path: str) -> np.ndarray:
    """Load a tiffsep channel TIFF as a 0-100 percent ink array."""
    import numpy as np

    img = Image.open(tif_path).convert("L")
    # tiffsep: 0 = full ink, 255 = no ink → invert to get ink density.
    arr = 255 - np.array(img, dtype=np.float32)
    return arr * (100.0 / 255.0)


def _pct_array_from_png_bytes(png_bytes: bytes) -> np.ndarray:
    """Load a cached channel PNG back into the 0-100 percent array.

    The cache stores the same grayscale that tiffsep produced (0 = full
    ink), so the decode path inverts the same way as :func:`_pct_array_from_tiff`.
    """
    import numpy as np

    img = Image.open(io.BytesIO(png_bytes)).convert("L")
    arr = 255 - np.array(img, dtype=np.float32)
    return arr * (100.0 / 255.0)


def _pct_array_to_png_bytes(arr: np.ndarray) -> bytes:
    """Encode a 0-100% ink array as the tiffsep-native PNG (0 = full ink)."""
    import numpy as np

    inked = np.clip(arr, 0.0, 100.0) * (255.0 / 100.0)
    gray = (255.0 - inked).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(gray, mode="L").save(buf, format="PNG")
    return buf.getvalue()


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

    Checks the S3 channel-PNG cache first when ``tenant_id``, ``job_id``
    and ``storage`` are all supplied; on a full CMYK hit, skips
    Ghostscript entirely. On a miss (or when called without a tenant
    scope, e.g. from a batch worker), runs ``tiffsep`` once and writes
    each CMYK channel back to S3 so the next call is cheap.

    Spot channels are **not** included here — callers that need them
    (densitometer) should run their own tiffsep discovery because spot
    channel composition varies by page and doesn't round-trip through
    the fixed CMYK cache keys.
    """
    # Fast path: all four CMYK PNGs already in S3.
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
            logger.debug(
                "get_cmyk_channels: S3 cache hit (tenant=%s job=%s p%d dpi=%d)",
                tenant_id,
                job_id,
                page_num,
                dpi,
            )
            return cached_arrays, list(PROCESS_CHANNEL_ORDER)

    # Miss (or no tenant context): render.
    with tempfile.TemporaryDirectory(prefix="lintpdf_cmyk_") as tmpdir:
        output_base = _run_tiffsep(pdf_bytes, page_num, dpi, tmpdir)
        arrays: list[np.ndarray] = []
        for ch in PROCESS_CHANNEL_ORDER:
            tif = _find_channel_tif(tmpdir, ch, output_base)
            if tif is None:
                raise RuntimeError(f"CMYK channel '{ch}' not found in GS output")
            arrays.append(_pct_array_from_tiff(tif))

    if cache_ok and tenant_id and job_id and storage:
        for ch, arr in zip(PROCESS_CHANNEL_ORDER, arrays, strict=True):
            key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch)
            try:
                storage.upload_raw(key, _pct_array_to_png_bytes(arr), content_type="image/png")
            except Exception:
                logger.warning("get_cmyk_channels: failed to cache channel %s key=%s", ch, key)

    return arrays, list(PROCESS_CHANNEL_ORDER)


def list_separations(pdf_bytes: bytes) -> list[dict]:
    """Return the ink channels actually present in the PDF.

    Scans every page's ``/ColorSpace`` resource dict (plus nested
    XObject forms, Shading, and Pattern dicts) and derives the set of
    channels that have real content:

    - ``DeviceCMYK`` / ``ICCBased`` with 4-component CMYK profile →
      emits Cyan / Magenta / Yellow / Black as ``type="process"``.
    - ``DeviceRGB`` / ``CalRGB`` / ``ICCBased`` with 3-component RGB
      profile → emits Red / Green / Blue as ``type="rgb"``. The viewer
      cannot render these as grayscale separations today (ghostscript
      ``tiffsep`` only decomposes CMYK), so they're surfaced as
      inventory only — the renderer returns 422 for non-CMYK channels.
    - ``DeviceGray`` / ``CalGray`` / ``ICCBased``-1-comp → ``Gray``.
    - ``/Separation`` and ``/DeviceN`` → each non-process component
      emitted as ``type="spot"`` (``All``/``None`` skipped).

    Previously this function unconditionally returned the four CMYK
    process channels regardless of whether the PDF used CMYK, so a
    pure-RGB or pure-spot file falsely reported CMYK separations and
    hid the actual inventory.

    Returns:
        List of dicts: ``[{"name": "Cyan", "type": "process"}, ...]``.
        Preserves first-seen order so process channels (when present)
        come before spots.
    """
    channels: list[dict] = []
    seen_names: set[str] = set()
    families: set[str] = set()  # "cmyk" | "rgb" | "gray"

    # Scan all pages for ink-bearing color spaces.
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            _scan_page_colorspaces(page, seen_names, channels, families)

    # Emit process channels based on what the PDF actually uses. Order:
    # CMYK → RGB → Gray → spots (spots were appended during the scan).
    prefix: list[dict] = []
    if "cmyk" in families:
        for name in PROCESS_CHANNEL_ORDER:
            prefix.append({"name": name, "type": "process"})
    if "rgb" in families:
        for name in ("Red", "Green", "Blue"):
            prefix.append({"name": name, "type": "rgb"})
    if "gray" in families and "cmyk" not in families and "rgb" not in families:
        # Only emit Gray when the file is actually grayscale-only —
        # otherwise the gray channel is implied by the CMYK K plate or
        # RGB composite and duplicating it in the viewer is noise.
        prefix.append({"name": "Gray", "type": "gray"})

    return prefix + channels


# Maximum recursion depth for nested Form XObjects. Illustrator-exported
# packaging PDFs have been observed at 4–6 levels deep for sticker /
# label artwork; 12 gives plenty of headroom without risking a runaway
# walk on a maliciously self-referencing file.
_MAX_XOBJECT_DEPTH = 12


def _scan_page_colorspaces(
    page: pikepdf.Page,
    seen_names: set[str],
    channels: list[dict],
    families: set[str],
) -> None:
    """Recursively scan a page's resources for color-space declarations.

    Tracks both spot-color declarations AND which device/ICCBased
    families are used on the page. ``families`` accumulates the
    strings ``"cmyk"`` / ``"rgb"`` / ``"gray"`` for the caller.
    """
    resources = page.get("/Resources")
    if resources is None:
        return
    _scan_resources_dict(
        resources,
        seen_names,
        channels,
        families,
        visited=set(),
        depth=0,
    )


def _scan_resources_dict(
    resources: object,
    seen_names: set[str],
    channels: list[dict],
    families: set[str],
    visited: set[int],
    depth: int,
) -> None:
    """Walk a ``/Resources`` dict + every Form XObject it references.

    Packaging PDFs from Illustrator / Esko nest Form XObjects many
    levels deep — each Form brings its own ``/Resources/ColorSpace``
    where spot colors are actually declared. The previous scanner
    only looked one level deep, so a nine-spot wine label (Amalgam
    Catalyst) surfaced zero channels in the viewer even though the
    analyzers saw all nine. This helper recurses up to
    :data:`_MAX_XOBJECT_DEPTH` levels and dedups via ``visited`` so
    cyclic references can't loop forever.

    Also scans ``/Pattern`` and ``/Shading`` resource entries since
    they can declare their own colorspaces (tinting patterns carry
    the stencil's colorspace, shadings may reference DeviceN).
    """
    if depth > _MAX_XOBJECT_DEPTH or resources is None:
        return

    # ColorSpace dict — the canonical spot-color declaration spot.
    # pikepdf Dictionary objects are already dict-like (dict(obj) works),
    # so we iterate directly. An earlier version called
    # ``pikepdf.Object.parse`` here, which silently raised a TypeError
    # on every saved-and-reopened PDF (``parse()`` takes bytes, not an
    # Object) — the outer ``except Exception: pass`` hid the failure and
    # left the channel list empty, which is exactly what the Amalgam
    # viewer surfaced.
    cs_dict = _safe_get(resources, "/ColorSpace")
    if cs_dict is not None and hasattr(cs_dict, "keys"):
        try:
            for _key, cs_value in dict(cs_dict).items():
                _extract_spot_from_cs(cs_value, seen_names, channels, families)
        except Exception:
            pass

    # Pattern resources — colored patterns inline a paint colorspace.
    pattern_dict = _safe_get(resources, "/Pattern")
    if pattern_dict is not None:
        try:
            for _key, pat in dict(pattern_dict).items():
                if hasattr(pat, "get"):
                    pat_cs = pat.get("/Resources")
                    if pat_cs is not None:
                        _scan_resources_dict(
                            pat_cs, seen_names, channels, families, visited, depth + 1,
                        )
        except Exception:
            pass

    # Shading resources — function-based shadings can declare a
    # DeviceN / Separation colorspace directly.
    shading_dict = _safe_get(resources, "/Shading")
    if shading_dict is not None:
        try:
            for _key, sh in dict(shading_dict).items():
                if hasattr(sh, "get"):
                    sh_cs = sh.get("/ColorSpace")
                    if sh_cs is not None:
                        _extract_spot_from_cs(sh_cs, seen_names, channels, families)
        except Exception:
            pass

    # XObjects — Images carry their own ColorSpace; Forms carry a
    # full Resources dict that we recurse into.
    xobjects = _safe_get(resources, "/XObject")
    if xobjects is None:
        return
    try:
        for _key, xobj in dict(xobjects).items():
            if not hasattr(xobj, "get"):
                continue
            obj_id = id(xobj)
            if obj_id in visited:
                continue
            visited.add(obj_id)

            subtype = xobj.get("/Subtype")
            subtype_str = str(subtype) if subtype is not None else ""

            if subtype_str == "/Image":
                img_cs = xobj.get("/ColorSpace")
                if img_cs is not None:
                    _extract_spot_from_cs(img_cs, seen_names, channels, families)
                continue

            # Form XObject — recurse into nested resources. Without
            # this, anything inside a Form (which is how Illustrator
            # exports the bulk of vector artwork) was invisible to
            # the separations scanner.
            sub_resources = xobj.get("/Resources")
            if sub_resources is not None:
                _scan_resources_dict(
                    sub_resources,
                    seen_names,
                    channels,
                    families,
                    visited,
                    depth + 1,
                )
    except Exception:
        pass


def _safe_get(obj: object, key: str) -> object | None:
    """``obj.get(key)`` but tolerant of non-dict-like inputs."""
    if obj is None or not hasattr(obj, "get"):
        return None
    try:
        return obj.get(key)
    except Exception:
        return None


def _extract_spot_from_cs(
    cs_value: object,
    seen_names: set[str],
    channels: list[dict],
    families: set[str],
) -> None:
    """Extract color family + spot name from a colorspace declaration.

    Accepts either a bare name (``/DeviceCMYK``) or an array
    (``[/ICCBased <stream>]``, ``[/Separation /PANTONE ...]``,
    ``[/DeviceN [/Cyan /Magenta ...] ...]``). Mutates ``families`` +
    ``channels`` + ``seen_names`` as side effects.
    """
    try:
        # Bare-name colorspaces used directly in content streams.
        if not hasattr(cs_value, "__iter__") or isinstance(cs_value, (str, bytes)):
            cs_type = str(cs_value)
            if cs_type == "/DeviceCMYK":
                families.add("cmyk")
            elif cs_type == "/DeviceRGB":
                families.add("rgb")
            elif cs_type == "/DeviceGray":
                families.add("gray")
            return

        cs_array = list(cs_value)
        if not cs_array:
            return

        cs_type = str(cs_array[0])

        if cs_type == "/DeviceCMYK":
            families.add("cmyk")
        elif cs_type == "/DeviceRGB" or cs_type == "/CalRGB":
            families.add("rgb")
        elif cs_type == "/DeviceGray" or cs_type == "/CalGray":
            families.add("gray")
        elif cs_type == "/ICCBased":
            # [/ICCBased <stream>] — stream's /N = component count:
            # 1 = gray, 3 = RGB/Lab, 4 = CMYK. The /Alternate entry
            # tells us which for 3-comp (Lab still emits RGB channel
            # set visually — we don't split Lab here).
            if len(cs_array) >= 2:
                stream = cs_array[1]
                n = None
                try:
                    n = int(stream.get("/N", 0)) if hasattr(stream, "get") else 0
                except Exception:
                    n = 0
                if n == 4:
                    families.add("cmyk")
                elif n == 3:
                    families.add("rgb")
                elif n == 1:
                    families.add("gray")
        elif cs_type == "/Lab":
            # Lab viewer behaviour is out of scope; treat as RGB family
            # so we at least emit SOMETHING rather than dropping the
            # page silently.
            families.add("rgb")
        elif cs_type == "/Indexed":
            # [/Indexed <base> <hival> <lookup>] — recurse on base.
            if len(cs_array) >= 2:
                _extract_spot_from_cs(cs_array[1], seen_names, channels, families)
        elif cs_type == "/Pattern":
            # [/Pattern <base>] — recurse if a base is specified
            # (uncoloured tiling pattern carries through the base cs).
            if len(cs_array) >= 2:
                _extract_spot_from_cs(cs_array[1], seen_names, channels, families)
        elif cs_type == "/Separation":
            if len(cs_array) >= 2:
                name = str(cs_array[1]).lstrip("/")
                if name not in seen_names and name not in ("All", "None"):
                    seen_names.add(name)
                    channels.append({"name": name, "type": "spot"})
        elif cs_type == "/DeviceN" and len(cs_array) >= 2:
            names_array = cs_array[1]
            for n_obj in names_array:
                name = str(n_obj).lstrip("/")
                if name in ("All", "None"):
                    continue
                if name in PROCESS_CHANNEL_COLORS:
                    # DeviceN declaring CMYK components as process.
                    families.add("cmyk")
                    continue
                if name not in seen_names:
                    seen_names.add(name)
                    channels.append({"name": name, "type": "spot"})
    except Exception:
        pass


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
    """Render a single separation channel as a grayscale PNG.

    Uses Ghostscript ``tiffsep`` device to decompose the page into
    individual channel TIFFs, then extracts the requested channel. When
    the caching context is supplied, a requested CMYK channel is served
    from S3 if possible, and any CMYK siblings rendered during a miss
    are warmed into the cache as a side effect.

    Args:
        pdf_bytes: Raw PDF bytes.
        page_num: 1-indexed page number.
        channel: Channel name (e.g. ``"Cyan"``, ``"PANTONE 485 C"``).
        dpi: Rendering resolution.
        tenant_id, job_id, storage: Optional S3 caching context.

    Returns:
        PNG image bytes (grayscale, tiffsep-native polarity: 0 = full
        ink, 255 = no ink).
    """
    cache_ok = bool(tenant_id and job_id and storage)

    # Direct hit for this exact channel.
    if cache_ok and tenant_id and job_id and storage:
        key = channel_cache_key(tenant_id, job_id, page_num, dpi, channel)
        try:
            raw = storage.download_raw(key)
        except Exception:
            raw = None
        if raw is not None:
            return raw

    # Fast path for a CMYK channel: piggy-back on the CMYK cache so we
    # warm all four at once.
    if channel in PROCESS_CHANNEL_ORDER:
        arrays, names = get_cmyk_channels(
            pdf_bytes, page_num, dpi, tenant_id=tenant_id, job_id=job_id, storage=storage
        )
        idx = names.index(channel)
        return _pct_array_to_png_bytes(arrays[idx])

    # Spot channel — we have to shell out and inspect the tmpdir for a
    # ``(name).tif`` match. Warm CMYK siblings while we're here.
    with tempfile.TemporaryDirectory(prefix="lintpdf_sep_") as tmpdir:
        output_base = _run_tiffsep(pdf_bytes, page_num, dpi, tmpdir)
        channel_tif = _find_channel_tif(tmpdir, channel, output_base)
        if channel_tif is None:
            raise RuntimeError(
                f"Channel '{channel}' not found in Ghostscript output. "
                f"Available files: {os.listdir(tmpdir)}"
            )

        if cache_ok and tenant_id and job_id and storage:
            for ch in PROCESS_CHANNEL_ORDER:
                tif = _find_channel_tif(tmpdir, ch, output_base)
                if tif is None:
                    continue
                key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch)
                try:
                    arr = _pct_array_from_tiff(tif)
                    storage.upload_raw(key, _pct_array_to_png_bytes(arr), content_type="image/png")
                except Exception:
                    logger.warning("render_separation_channel: failed to warm %s", ch)

        img = Image.open(channel_tif).convert("L")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def _find_channel_tif(tmpdir: str, channel: str, output_base: str) -> str | None:
    """Find the TIFF file for a specific channel in the GS output directory."""
    files = sorted(os.listdir(tmpdir))

    # Ghostscript tiffsep naming: {base}1.tif is composite CMYK
    # Channel-specific files are named like:
    #   {base}1(Cyan).tif, {base}1(Magenta).tif, {base}1(Yellow).tif, {base}1(Black).tif
    #   {base}1(PANTONE 485 C).tif, etc.
    # Or in older GS: {base}1.Cyan.tif

    channel.replace("(", r"\(").replace(")", r"\)")

    for f in files:
        fpath = os.path.join(tmpdir, f)
        if not f.endswith(".tif"):
            continue

        # Match pattern: sep1(Cyan).tif or sep1.Cyan.tif
        # Case-insensitive match on channel name
        fname_lower = f.lower()
        channel_lower = channel.lower()

        if f"({channel_lower})" in fname_lower:
            return fpath
        if f".{channel_lower}.tif" in fname_lower:
            return fpath
        # Also try with dots replaced by spaces for spot colors
        if channel_lower.replace(" ", "_") in fname_lower:
            return fpath

    # Fallback: for process channels, try index-based matching
    # tiffsep generates numbered files for CMYK: index 0=Cyan,1=Magenta,2=Yellow,3=Black
    if channel in PROCESS_CHANNEL_ORDER:
        PROCESS_CHANNEL_ORDER.index(channel)
        # The composite is file 1, then channels start at file with channel name
        # Try numbered fallback: look for sep1(Cyan).tif pattern with different naming
        for f in files:
            if not f.endswith(".tif"):
                continue
            fpath = os.path.join(tmpdir, f)
            # Check if file contains channel name in any form
            if channel.lower() in f.lower():
                return fpath

    return None


def _extract_text_bboxes(
    pdf_bytes: bytes, page_num: int
) -> list[tuple[float, float, float, float]]:
    """Return merged text-run bboxes for a page in PDF points.

    Uses poppler's ``pdftotext -bbox`` to get per-word positions, then
    merges adjacent words on the same line into single run bboxes so we
    emit one outline per headline / caption / paragraph rather than one
    per word (which would cover the whole page).

    Bboxes are returned in PDF-point space with origin at the **top-left**
    of the page — matching pdftotext's output — so callers that want the
    conventional PDF lower-left origin must flip Y themselves.

    Returns an empty list if poppler-utils is not installed or the PDF
    has no extractable text (e.g. scanned images only). Never raises.
    """
    # nosemgrep: use-defused-xml — output of our own pdftotext, not external input
    from xml.etree.ElementTree import fromstring

    with tempfile.TemporaryDirectory(prefix="lintpdf_txt_") as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        html_path = os.path.join(tmpdir, "out.xhtml")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        cmd = [
            "pdftotext",
            "-bbox",
            "-f",
            str(page_num),
            "-l",
            str(page_num),
            pdf_path,
            html_path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        if proc.returncode != 0 or not os.path.exists(html_path):
            return []

        try:
            with open(html_path, encoding="utf-8", errors="replace") as f:
                xml_body: str = f.read()
        except OSError:
            return []

    # pdftotext emits an XHTML doc that contains exactly one <page> for the
    # slice we requested (-f == -l). Strip the doctype so xml.etree can
    # parse it, then walk the word nodes.
    body_idx = xml_body.find("<html")
    if body_idx == -1:
        return []
    cleaned = xml_body[body_idx:]
    try:
        root = fromstring(cleaned)
    except Exception:
        return []

    # pdftotext emits nodes in the XHTML namespace, so the real tag is
    # e.g. ``{http://www.w3.org/1999/xhtml}word``. Match on localname.
    words: list[tuple[float, float, float, float]] = []
    for el in root.iter():
        tag = el.tag if isinstance(el.tag, str) else ""
        if tag.split("}")[-1] != "word":
            continue
        try:
            x0 = float(el.get("xMin") or 0)
            y0 = float(el.get("yMin") or 0)
            x1 = float(el.get("xMax") or 0)
            y1 = float(el.get("yMax") or 0)
        except (TypeError, ValueError):
            continue
        if x1 <= x0 or y1 <= y0:
            continue
        words.append((x0, y0, x1, y1))

    if not words:
        return []

    # Sort top-to-bottom, then left-to-right.
    words.sort(key=lambda b: (round(b[1], 1), b[0]))

    # Merge words on the "same line" (yMin within 2pt tolerance) whose
    # horizontal gap to the previous run is less than one em of the
    # current word's height. Scaling the gap with font size matters:
    # a 9pt caption has tight 2-3pt spaces, while a 48pt headline can
    # carry 14pt tracking and still be a single run. A static 6pt gap
    # splits big type into word-soup and doesn't tighten captions.
    merged: list[list[float]] = []
    line_tol = 2.0
    for x0, y0, x1, y1 in words:
        height = max(1.0, y1 - y0)
        gap_tol = max(6.0, height * 0.75)
        if merged:
            prev = merged[-1]
            prev_height = max(1.0, prev[3] - prev[1])
            same_line = (
                abs(y0 - prev[1]) <= line_tol
                and abs(y1 - prev[3]) <= line_tol * 2
                # Runs of wildly different heights (caption word next to
                # a super/subscript glyph) should not glue together.
                and abs(height - prev_height) <= max(2.0, prev_height * 0.3)
            )
            gap_ok = x0 - prev[2] <= gap_tol
            if same_line and gap_ok:
                prev[2] = max(prev[2], x1)
                prev[3] = max(prev[3], y1)
                prev[1] = min(prev[1], y0)
                continue
        merged.append([x0, y0, x1, y1])

    # Cap noise on dense pages so the overlay stays readable.
    if len(merged) > 400:
        merged = merged[:400]

    return [(b[0], b[1], b[2], b[3]) for b in merged]


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
    """Generate a TAC (Total Area Coverage) heatmap PNG overlay plus per-run metadata.

    Renders CMYK channels via Ghostscript (or the S3 channel cache if
    ``tenant_id`` / ``job_id`` / ``storage`` are supplied), computes
    per-pixel TAC, and produces a color-mapped overlay:
    - Green: TAC < 250%
    - Yellow: 250% <= TAC < ``tac_limit``
    - Red: TAC >= ``tac_limit``

    Also draws **red outline rectangles** around each text run whose
    interior mean TAC exceeds ``tac_limit``, so reviewers can see at a
    glance which specific pieces of text are over budget without
    squinting at a pixel gradient. Text-run detection uses
    ``pdftotext -bbox``; if poppler is unavailable or the page has no
    extractable text, the heatmap still renders without outlines.

    Args:
        pdf_bytes: Raw PDF bytes.
        page_num: 1-indexed page number.
        dpi: Rendering resolution.
        tac_limit: TAC threshold for red highlighting (default 300%).
        tenant_id, job_id, storage: Optional S3 caching context. When all
            three are supplied, the CMYK channel raster cache is consulted
            before running tiffsep.

    Returns:
        A ``TacHeatmap`` dict: ``{"png": <rgba bytes>, "runs": [TacRun, ...]}``.
        The PNG carries the final overlay (including outlines), while the
        ``runs`` list exposes per-text-run mean TAC in PDF-point space for
        an interactive tooltip layer.
    """
    import numpy as np

    cmyk_arrays, _ = get_cmyk_channels(
        pdf_bytes, page_num, dpi, tenant_id=tenant_id, job_id=job_id, storage=storage
    )

    # Compute TAC: sum of CMYK percentages per pixel (0–400%)
    tac = cmyk_arrays[0] + cmyk_arrays[1] + cmyk_arrays[2] + cmyk_arrays[3]

    height, width = tac.shape

    # Build RGBA heatmap
    heatmap = np.zeros((height, width, 4), dtype=np.uint8)

    # Every element with ink gets a color. Only true paper-white
    # (TAC essentially zero) stays transparent so the PDF page remains visible.

    # Green zone: TAC < 250% (includes text and light coverage areas)
    green_mask = (tac >= 1) & (tac < 250)
    heatmap[green_mask] = [0, 180, 0, 100]

    # Yellow zone: 250% <= TAC < tac_limit
    yellow_mask = (tac >= 250) & (tac < tac_limit)
    heatmap[yellow_mask] = [255, 200, 0, 150]

    # Red zone: TAC >= tac_limit
    red_mask = tac >= tac_limit
    heatmap[red_mask] = [255, 0, 0, 190]

    # True paper-white (TAC < 1%) stays transparent so page content shows through
    paper_mask = tac < 1
    heatmap[paper_mask] = [0, 0, 0, 0]

    heatmap_img = Image.fromarray(heatmap, mode="RGBA")

    # Text-run outlines: find text bboxes, compute each run's mean TAC
    # from the heatmap we just built, and draw a red stroke around
    # runs that exceed the limit. Wrapped so a pdftotext failure or a
    # PDF with no text never breaks the heatmap itself.
    try:
        text_bboxes = _extract_text_bboxes(pdf_bytes, page_num)
    except Exception:
        logger.warning("TAC heatmap: text-bbox extraction failed", exc_info=True)
        text_bboxes = []

    runs: list[TacRun] = []

    if text_bboxes:
        # pdftotext uses top-left origin in PDF points. We need pixel
        # coordinates in the heatmap raster. Read the page MediaBox to
        # compute the pt -> pixel scale.
        try:
            with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
                mb = pdf.pages[page_num - 1].get("/MediaBox")
                mb_vals = [float(v) for v in mb] if mb is not None else [0, 0, 612, 792]
        except Exception:
            mb_vals = [0.0, 0.0, float(width), float(height)]

        page_w_pt = mb_vals[2] - mb_vals[0] or 1.0
        page_h_pt = mb_vals[3] - mb_vals[1] or 1.0
        sx = width / page_w_pt
        sy = height / page_h_pt

        from PIL import ImageDraw

        draw = ImageDraw.Draw(heatmap_img)
        stroke = (220, 0, 0, 230)
        stroke_w = max(2, round(dpi / 72))

        for x0, y0, x1, y1 in text_bboxes:
            px_x0 = max(0, round(x0 * sx))
            px_y0 = max(0, round(y0 * sy))
            px_x1 = min(width, round(x1 * sx))
            px_y1 = min(height, round(y1 * sy))
            if px_x1 - px_x0 < 2 or px_y1 - px_y0 < 2:
                continue

            # Mean TAC inside the bbox — cheap and good enough.
            patch = tac[px_y0:px_y1, px_x0:px_x1]
            if patch.size == 0:
                continue
            mean_tac = float(patch.mean())
            exceeds = mean_tac >= tac_limit

            # Always record the run so the tooltip layer can show every
            # text region's TAC, not just the hot ones.
            runs.append(
                TacRun(
                    x0=float(x0),
                    y0=float(y0),
                    x1=float(x1),
                    y1=float(y1),
                    mean_tac=round(mean_tac, 2),
                    limit=float(tac_limit),
                    exceeds=exceeds,
                )
            )

            # Only draw the outline for runs that exceed the limit; runs
            # with a single heavy glyph on a light background read as
            # borderline and don't warrant an alarm outline.
            if not exceeds:
                continue

            # Draw the outline with a 1px inset so the stroke sits just
            # inside the bbox and doesn't clip at the page edge.
            draw.rectangle(
                (px_x0, px_y0, px_x1 - 1, px_y1 - 1),
                outline=stroke,
                width=stroke_w,
            )

    buf = io.BytesIO()
    heatmap_img.save(buf, format="PNG")
    return TacHeatmap(png=buf.getvalue(), runs=runs)


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
    """Sample per-channel ink coverage + TAC at a PDF point.

    On the CMYK fast path — when ``tenant_id`` / ``job_id`` / ``storage``
    are all supplied and the S3 channel cache is populated — no
    Ghostscript subprocess is run; the cached per-channel rasters are
    sampled directly. On cache miss the page is rendered via
    ``tiffsep`` (which both populates the CMYK cache **and** gives us
    any spot channels that weren't cacheable anyway).

    Args:
        pdf_bytes: Raw PDF bytes.
        page_num: 1-indexed page number.
        x, y: PDF-space coordinates in points (origin lower-left,
            matching the sample_color endpoint).
        page_w, page_h: MediaBox width / height in points.
        dpi: Rendering resolution.
        tac_limit: TAC limit in percent (for ``limit_exceeded`` flag).
        tenant_id, job_id, storage: Optional S3 caching context.

    Returns:
        ``{"x", "y", "dpi", "channels": [{"name", "percent"}, ...],
        "tac", "tac_limit", "limit_exceeded"}``.

    Raises:
        RuntimeError: If Ghostscript fails or no CMYK channels are produced
            (e.g. an RGB-only PDF with no separable inks). The caller
            surfaces this as a 422 for the UI to render a friendly
            "no separations available" message.
    """
    # Try the cache-only path first: if all four CMYK channels are
    # already in S3 we can avoid shelling out to Ghostscript entirely.
    # When the PDF has spot inks we also try to pull each spot from
    # the cache so the response stays complete; if any spot misses
    # we fall back to tiffsep so the densitometer never hides inks
    # the page actually uses.
    cache_ok = bool(tenant_id and job_id and storage)
    cmyk_from_cache: list[np.ndarray] | None = None
    spots_from_cache: list[tuple[str, np.ndarray]] = []
    spot_names: list[str] = []
    if cache_ok and tenant_id and job_id and storage:
        try:
            spot_names = [
                s["name"]
                for s in list_separations(pdf_bytes)
                if s.get("type") == "spot"
            ]
        except Exception:
            spot_names = []

        candidate: list[np.ndarray] = []
        for ch in PROCESS_CHANNEL_ORDER:
            key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch)
            try:
                raw = storage.download_raw(key)
            except Exception:
                raw = None
            if raw is None:
                candidate = []
                break
            candidate.append(_pct_array_from_png_bytes(raw))
        if len(candidate) == 4:
            cmyk_from_cache = candidate
            # Also try the spot cache. Any miss → fall back to tiffsep
            # below so no ink is silently dropped.
            spot_pulls: list[tuple[str, np.ndarray]] = []
            for spot in spot_names:
                key = channel_cache_key(tenant_id, job_id, page_num, dpi, spot)
                try:
                    raw = storage.download_raw(key)
                except Exception:
                    raw = None
                if raw is None:
                    spot_pulls = []
                    cmyk_from_cache = None
                    break
                spot_pulls.append((spot, _pct_array_from_png_bytes(raw)))
            spots_from_cache = spot_pulls

    def _sample_patch(arr: np.ndarray, px_x: int, px_y: int) -> float:
        img_h, img_w = arr.shape
        x0 = max(0, px_x - 1)
        x1 = min(img_w, px_x + 2)
        y0 = max(0, px_y - 1)
        y1 = min(img_h, px_y + 2)
        patch = arr[y0:y1, x0:x1]
        if patch.size == 0:
            return 0.0
        return max(0.0, min(100.0, float(patch.mean())))

    def _pct_to_px(arr: np.ndarray) -> tuple[int, int]:
        img_h, img_w = arr.shape
        scale_x = img_w / page_w if page_w else 1.0
        scale_y = img_h / page_h if page_h else 1.0
        px_x = round(x * scale_x)
        # PDF origin is lower-left; image origin is upper-left. Flip Y.
        px_y = round(img_h - y * scale_y)
        px_x = max(0, min(px_x, img_w - 1))
        px_y = max(0, min(px_y, img_h - 1))
        return px_x, px_y

    channel_entries: list[dict[str, Any]] = []

    if cmyk_from_cache is not None:
        px_x, px_y = _pct_to_px(cmyk_from_cache[0])
        for ch_name, arr in zip(PROCESS_CHANNEL_ORDER, cmyk_from_cache, strict=True):
            channel_entries.append(
                {"name": ch_name, "percent": round(_sample_patch(arr, px_x, px_y), 2)}
            )
        for spot_name, spot_arr in spots_from_cache:
            channel_entries.append(
                {"name": spot_name, "percent": round(_sample_patch(spot_arr, px_x, px_y), 2)}
            )
        logger.debug(
            "sample_densitometer: cache hit (no tiffsep) — cmyk=4 spots=%d",
            len(spots_from_cache),
        )
    else:
        # Cache miss or no scope — run tiffsep, capture CMYK + any spots,
        # write CMYK back to the cache for next time.
        with tempfile.TemporaryDirectory(prefix="lintpdf_dens_") as tmpdir:
            output_base = _run_tiffsep(pdf_bytes, page_num, dpi, tmpdir)

            channel_files: list[tuple[str, str]] = []
            for ch_name in PROCESS_CHANNEL_ORDER:
                ch_tif = _find_channel_tif(tmpdir, ch_name, output_base)
                if ch_tif is not None:
                    channel_files.append((ch_name, ch_tif))

            process_lower = {n.lower() for n in PROCESS_CHANNEL_ORDER}
            already = {ch[0].lower() for ch in channel_files}
            for name in sorted(os.listdir(tmpdir)):
                if not name.endswith(".tif"):
                    continue
                if "(" not in name or ")" not in name:
                    continue  # composite, no parens
                spot = name[name.index("(") + 1 : name.rindex(")")]
                if not spot or spot.lower() in process_lower or spot.lower() in already:
                    continue
                channel_files.append((spot, os.path.join(tmpdir, name)))
                already.add(spot.lower())

            if not channel_files:
                raise RuntimeError("No separation channels produced for this page")

            # Load all arrays, derive pixel coord from the first, sample
            # each, and opportunistically warm the CMYK cache.
            first_arr = _pct_array_from_tiff(channel_files[0][1])
            px_x, px_y = _pct_to_px(first_arr)

            for ch_name, tif_path in channel_files:
                arr = (
                    first_arr if tif_path == channel_files[0][1] else _pct_array_from_tiff(tif_path)
                )
                channel_entries.append(
                    {"name": ch_name, "percent": round(_sample_patch(arr, px_x, px_y), 2)}
                )
                # Cache CMYK + spots alike. The cache-hit path above
                # pulls both so caching every channel keeps the fast
                # path complete for spot-heavy files.
                if cache_ok and tenant_id and job_id and storage:
                    key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch_name)
                    try:
                        storage.upload_raw(
                            key, _pct_array_to_png_bytes(arr), content_type="image/png"
                        )
                    except Exception:
                        logger.warning("sample_densitometer: failed to cache channel %s", ch_name)

    tac = round(sum(float(ch["percent"]) for ch in channel_entries), 2)

    return {
        "x": x,
        "y": y,
        "dpi": dpi,
        "channels": channel_entries,
        "tac": tac,
        "tac_limit": tac_limit,
        "limit_exceeded": tac > tac_limit,
    }


# WS-17A software-composite tile renderer.
#
# Ghostscript's ``png16m`` + ``-dSimulateOverprint=true`` path is
# supposed to produce an on-screen preview that faithfully simulates
# how the page will print — including spot-ink overprinting. In
# practice, on files with no /OutputIntent declared (which every
# file in the 2026-04-23 Test3 / Amalgam_Catalyst / Pink-Slush
# corpus is), Ghostscript collapses every Separation alternate onto
# a single CMYK intermediate and the composite comes out a single
# tint (flat blue for Test3).
#
# Per ISO 32000-2:2020 §8.6.6.4 ("Separation colour spaces"), "For
# an additive device such as a computer display, a Separation
# colour space never applies a process colourant directly; it
# always reverts to the alternate colour space". The alternate +
# tint-transform approach ONLY works when the alternates are
# well-defined + the output intent supplies a reference CMYK
# profile. Neither is reliable for real-world packaging PDFs.
#
# This function bypasses the tint transform entirely by rendering
# each ink as its own plate via tiffsep (already battle-tested for
# the densitometer + TAC + per-channel viewer), then compositing
# the plates into RGB using a fixed-per-ink absorption model.
# Mirrors the pixel math the browser's SeparationCanvas does when
# the user enters separation mode, so "normal" composite preview
# and "separation" preview converge.

# Subtractive ink → RGB absorption coefficients. Each value is the
# amount of R, G, B (0-255) absorbed at 100% tint. White paper
# reflects (255, 255, 255); every 1 % of tint applied removes
# ``coef × 2.55`` units of reflected light per channel.
_INK_ABSORPTION_RGB: dict[str, tuple[int, int, int]] = {
    # CMYK process inks — absorption is the complement of the
    # ink's visible RGB ("cyan absorbs red light", etc.).
    "Cyan":    (255,   0,   0),
    "Magenta": (  0, 255,   0),
    "Yellow":  (  0,   0, 255),
    "Black":   (255, 255, 255),
}


def _spot_absorption_rgb(name: str) -> tuple[int, int, int]:
    """Best-effort absorption triple for a spot ink named ``name``.

    Mirrors the rules in ``SeparationPanel.spotSwatchColor``:
    semantic colour words ("black", "cyan", "foil", "beige", ...)
    map to curated absorption tuples; everything else falls back
    to a stable hash-driven HSL → RGB. The goal is a reasonable
    preview, not printing fidelity — a press-accurate composite
    needs the real alternate CMYK tint transform, which the
    ``-dSimulateOverprint=true`` path already handles when the
    file carries a valid OutputIntent.
    """
    lowered = name.strip().lower()
    exact: dict[str, tuple[int, int, int]] = {
        "black":   (255, 255, 255),
        "k":       (255, 255, 255),
        "cyan":    (255,   0,   0),
        "c":       (255,   0,   0),
        "magenta": (  0, 255,   0),
        "m":       (  0, 255,   0),
        "yellow":  (  0,   0, 255),
        "y":       (  0,   0, 255),
        "white":   (  0,   0,   0),  # paper — absorbs nothing.
    }
    if lowered in exact:
        return exact[lowered]

    patterns: list[tuple[str, tuple[int, int, int]]] = [
        ("cut", (0, 200, 200)),        # dieline / cut — red ink preview
        ("dieline", (0, 200, 200)),
        ("crease", (0, 200, 200)),
        ("perf", (0, 200, 200)),
        ("fold", (0, 200, 200)),
        ("foil", (128, 128, 128)),     # metallic → neutral grey
        ("silver", (128, 128, 128)),
        ("gold", (40, 80, 200)),
        ("copper", (40, 80, 150)),
        ("varnish", (200, 200, 200)),  # gloss / UV — nearly invisible
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

    # Hash → HSL(hue, 60%, 45%) → RGB absorption coefficient.
    h = 0
    for ch in name:
        h = ord(ch) + ((h << 5) - h)
    hue = abs(h) % 360
    s, light = 0.6, 0.45
    c = (1 - abs(2 * light - 1)) * s
    x = c * (1 - abs(((hue / 60) % 2) - 1))
    m = light - c / 2
    if hue < 60:     r, g, b = c, x, 0
    elif hue < 120:  r, g, b = x, c, 0
    elif hue < 180:  r, g, b = 0, c, x
    elif hue < 240:  r, g, b = 0, x, c
    elif hue < 300:  r, g, b = x, 0, c
    else:            r, g, b = c, 0, x
    ink_r = int(round((r + m) * 255))
    ink_g = int(round((g + m) * 255))
    ink_b = int(round((b + m) * 255))
    # Absorption = 255 - ink colour.
    return (255 - ink_r, 255 - ink_g, 255 - ink_b)


def render_composite_via_separations(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 150,
    *,
    tenant_id: str | None = None,
    job_id: str | None = None,
    storage: StorageBackend | None = None,
) -> bytes | None:
    """Software-composite the page from per-channel separations.

    Returns the PNG bytes of a white-paper RGB composite built from
    the tiffsep output, or ``None`` when there are no separations
    to composite (the caller should then fall back to the regular
    Ghostscript path).

    The composite honours the subtractive ink model: every 1 % of
    tint applied to a plate removes ``absorption_coef × 0.01`` from
    the paper's reflected light in each RGB channel. This approximates
    "what the page will look like on a press, viewed under D50"
    without needing a proper OutputIntent — which most packaging
    PDFs sadly lack (confirmed by LPDF_COLOR_006 on every file in
    the 2026-04-23 corpus).

    Uses the CMYK + spot cache populated by :func:`sample_densitometer`
    when available; falls back to a fresh tiffsep run on miss.
    """
    import numpy as np

    # Try cache first (CMYK + all declared spots).
    cache_ok = bool(tenant_id and job_id and storage)

    try:
        spot_names = [
            s["name"] for s in list_separations(pdf_bytes) if s.get("type") == "spot"
        ]
    except Exception:
        spot_names = []

    plates: list[tuple[str, np.ndarray]] = []
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
                    # Spot missing — drop the cache path and run tiffsep
                    # so every plate comes from the same render.
                    plates = []
                    break
                plates.append((spot, _pct_array_from_png_bytes(raw)))
        elif not cmyk_ok:
            plates = []

    if not plates:
        with tempfile.TemporaryDirectory(prefix="lintpdf_comp_") as tmpdir:
            try:
                output_base = _run_tiffsep(pdf_bytes, page_num, dpi, tmpdir)
            except Exception:
                logger.exception(
                    "render_composite_via_separations: tiffsep failed"
                )
                return None

            for ch in PROCESS_CHANNEL_ORDER:
                tif = _find_channel_tif(tmpdir, ch, output_base)
                if tif is not None:
                    plates.append((ch, _pct_array_from_tiff(tif)))

            process_lower = {n.lower() for n in PROCESS_CHANNEL_ORDER}
            already = {name.lower() for name, _ in plates}
            for name in sorted(os.listdir(tmpdir)):
                if not name.endswith(".tif"):
                    continue
                if "(" not in name or ")" not in name:
                    continue
                spot = name[name.index("(") + 1 : name.rindex(")")]
                if not spot or spot.lower() in process_lower or spot.lower() in already:
                    continue
                plates.append((spot, _pct_array_from_tiff(os.path.join(tmpdir, name))))
                already.add(spot.lower())

            # Warm the cache for subsequent densitometer / TAC hits.
            if cache_ok and tenant_id and job_id and storage:
                for ch_name, arr in plates:
                    key = channel_cache_key(tenant_id, job_id, page_num, dpi, ch_name)
                    try:
                        storage.upload_raw(
                            key,
                            _pct_array_to_png_bytes(arr),
                            content_type="image/png",
                        )
                    except Exception:
                        logger.warning(
                            "render_composite_via_separations: failed to cache %s",
                            ch_name,
                        )

    if not plates:
        return None

    # Start from white paper and subtract each ink's absorption.
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
        # ``plate`` is 0..100 (% tint). Scale to 0..1.
        tint = np.clip(plate, 0.0, 100.0) / 100.0
        for channel_idx, coef in enumerate(absorption):
            # Every 1% of tint absorbs coef/100 of the channel's
            # current value — a multiplicative "stack more ink" model
            # that stays sane when plates overlap (e.g. registration
            # tick marks that paint every separation at 100%).
            rgb[:, :, channel_idx] *= 1.0 - (tint * (coef / 255.0))

    rgb_uint8 = np.clip(rgb, 0.0, 255.0).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb_uint8, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()
