"""Separation channel rendering — decompose PDF into ink channels and TAC heatmaps."""

from __future__ import annotations

import io
import logging
import os
import subprocess
import tempfile

import pikepdf
from PIL import Image

logger = logging.getLogger(__name__)

# Process ink channel colors for tinting
PROCESS_CHANNEL_COLORS = {
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Yellow": (255, 255, 0),
    "Black": (0, 0, 0),
}

PROCESS_CHANNEL_ORDER = ["Cyan", "Magenta", "Yellow", "Black"]


def list_separations(pdf_bytes: bytes) -> list[dict]:
    """Return all ink channels present in a PDF.

    Enumerates color spaces across all pages using pikepdf to find both
    process (CMYK) and spot color channels.

    Returns:
        List of dicts: ``[{"name": "Cyan", "type": "process"}, ...]``
    """
    channels: list[dict] = []
    seen_names: set[str] = set()

    # Always include CMYK process channels
    for name in PROCESS_CHANNEL_ORDER:
        channels.append({"name": name, "type": "process"})
        seen_names.add(name)

    # Scan all pages for Separation and DeviceN color spaces
    with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            _scan_page_colorspaces(page, seen_names, channels)

    return channels


def _scan_page_colorspaces(
    page: pikepdf.Page,
    seen_names: set[str],
    channels: list[dict],
) -> None:
    """Recursively scan a page's resources for spot color declarations."""
    resources = page.get("/Resources")
    if resources is None:
        return

    # Check ColorSpace resource dictionary
    cs_dict = resources.get("/ColorSpace")
    if cs_dict is not None:
        try:
            cs_obj = pikepdf.Object.parse(cs_dict) if not isinstance(cs_dict, dict) else cs_dict
            for _key, cs_value in dict(cs_obj).items():
                _extract_spot_from_cs(cs_value, seen_names, channels)
        except Exception:
            pass

    # Also scan XObject forms recursively
    xobjects = resources.get("/XObject")
    if xobjects is not None:
        try:
            for _key, xobj in dict(xobjects).items():
                xobj_resolved = xobj
                if hasattr(xobj_resolved, "get"):
                    sub_resources = xobj_resolved.get("/Resources")
                    if sub_resources is not None:
                        sub_cs = sub_resources.get("/ColorSpace")
                        if sub_cs is not None:
                            try:
                                for _k2, cs_val in dict(sub_cs).items():
                                    _extract_spot_from_cs(cs_val, seen_names, channels)
                            except Exception:
                                pass
        except Exception:
            pass


def _extract_spot_from_cs(
    cs_value: object,
    seen_names: set[str],
    channels: list[dict],
) -> None:
    """Extract spot color name from a Separation or DeviceN color space array."""
    try:
        cs_array = list(cs_value) if hasattr(cs_value, "__iter__") else []
        if len(cs_array) < 2:
            return

        cs_type = str(cs_array[0])

        if cs_type == "/Separation":
            name = str(cs_array[1]).lstrip("/")
            if name not in seen_names and name != "All" and name != "None":
                seen_names.add(name)
                channels.append({"name": name, "type": "spot"})

        elif cs_type == "/DeviceN":
            names_array = cs_array[1]
            for n in names_array:
                name = str(n).lstrip("/")
                if name not in seen_names and name != "All" and name != "None":
                    # Check if it's a known process channel
                    if name in PROCESS_CHANNEL_COLORS:
                        continue  # already included
                    seen_names.add(name)
                    channels.append({"name": name, "type": "spot"})
    except Exception:
        pass


def render_separation_channel(
    pdf_bytes: bytes,
    page_num: int,
    channel: str,
    dpi: int = 150,
) -> bytes:
    """Render a single separation channel as a grayscale PNG.

    Uses Ghostscript ``tiffsep`` device to decompose the page into
    individual channel TIFFs, then extracts the requested channel.

    Args:
        pdf_bytes: Raw PDF bytes.
        page_num: 1-indexed page number.
        channel: Channel name (e.g. ``"Cyan"``, ``"PANTONE 485 C"``).
        dpi: Rendering resolution.

    Returns:
        PNG image bytes (grayscale).
    """
    with tempfile.TemporaryDirectory(prefix="lintpdf_sep_") as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        output_base = os.path.join(tmpdir, "sep")

        # Run Ghostscript tiffsep
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

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            logger.error("Ghostscript tiffsep failed: %s", stderr)
            raise RuntimeError(f"Ghostscript separation failed: {stderr[:500]}")

        # Determine channel mapping from the generated files
        # tiffsep outputs: sep1.tif (composite), then per-channel TIFs named
        # with the channel name: sep1.tif.Cyan.tif, sep1.tif.Magenta.tif, etc.
        # Or numbered format: sep1.tif is composite, sep1(Cyan).tif, etc.
        # The actual naming depends on GS version — scan the directory.
        channel_tif = _find_channel_tif(tmpdir, channel, output_base)
        if channel_tif is None:
            raise RuntimeError(
                f"Channel '{channel}' not found in Ghostscript output. "
                f"Available files: {os.listdir(tmpdir)}"
            )

        # Convert TIFF to grayscale PNG
        img = Image.open(channel_tif).convert("L")

        # Invert: tiffsep outputs ink density (255 = full ink, 0 = no ink)
        # but we want 0 = full ink (dark) for display, so we invert
        # Actually tiffsep already outputs as ink density where 0=full ink
        # in CMYK space. We keep as-is for compositing.
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


def render_tac_heatmap(
    pdf_bytes: bytes,
    page_num: int,
    dpi: int = 150,
    tac_limit: float = 300,
) -> bytes:
    """Generate a TAC (Total Area Coverage) heatmap PNG overlay.

    Renders CMYK channels via Ghostscript, computes per-pixel TAC, and
    produces a color-mapped overlay:
    - Green: TAC < 250%
    - Yellow: 250% <= TAC < ``tac_limit``
    - Red: TAC >= ``tac_limit``

    Args:
        pdf_bytes: Raw PDF bytes.
        page_num: 1-indexed page number.
        dpi: Rendering resolution.
        tac_limit: TAC threshold for red highlighting (default 300%).

    Returns:
        RGBA PNG image bytes (heatmap overlay with transparency).
    """
    import numpy as np

    with tempfile.TemporaryDirectory(prefix="lintpdf_tac_") as tmpdir:
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        output_base = os.path.join(tmpdir, "sep")

        # Run Ghostscript tiffsep
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

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            raise RuntimeError(f"Ghostscript separation failed: {stderr[:500]}")

        # Load CMYK channel images
        cmyk_arrays = []
        for ch_name in PROCESS_CHANNEL_ORDER:
            ch_tif = _find_channel_tif(tmpdir, ch_name, output_base)
            if ch_tif is None:
                raise RuntimeError(f"CMYK channel '{ch_name}' not found in GS output")
            img = Image.open(ch_tif).convert("L")
            # tiffsep: 0 = full ink, 255 = no ink  →  invert to get ink %
            arr = 255 - np.array(img, dtype=np.float32)
            # Normalize to 0–100% range
            cmyk_arrays.append(arr * (100.0 / 255.0))

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
        buf = io.BytesIO()
        heatmap_img.save(buf, format="PNG")
        return buf.getvalue()
