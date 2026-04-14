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
    # horizontal gap to the previous run is less than one character
    # width (~6pt). Produces one bbox per visually-contiguous text run.
    merged: list[list[float]] = []
    line_tol = 2.0
    gap_tol = 6.0
    for x0, y0, x1, y1 in words:
        if merged:
            prev = merged[-1]
            same_line = abs(y0 - prev[1]) <= line_tol and abs(y1 - prev[3]) <= line_tol * 2
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
) -> bytes:
    """Generate a TAC (Total Area Coverage) heatmap PNG overlay.

    Renders CMYK channels via Ghostscript, computes per-pixel TAC, and
    produces a color-mapped overlay:
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

        # Text-run outlines: find text bboxes, compute each run's mean TAC
        # from the heatmap we just built, and draw a red stroke around
        # runs that exceed the limit. Wrapped so a pdftotext failure or a
        # PDF with no text never breaks the heatmap itself.
        try:
            text_bboxes = _extract_text_bboxes(pdf_bytes, page_num)
        except Exception:
            logger.warning("TAC heatmap: text-bbox extraction failed", exc_info=True)
            text_bboxes = []

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

                # Mean TAC inside the bbox — cheap and good enough. Only
                # outline runs where the mean exceeds the limit; runs with
                # a single heavy glyph on a light background read as
                # borderline and don't warrant an alarm outline.
                patch = tac[px_y0:px_y1, px_x0:px_x1]
                if patch.size == 0:
                    continue
                if float(patch.mean()) < tac_limit:
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
        return buf.getvalue()


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
) -> dict[str, object]:
    """Sample per-channel ink coverage + TAC at a PDF point.

    Runs Ghostscript ``tiffsep`` once to split the requested page into
    CMYK (and any spot) channels at ``dpi`` resolution, then averages a
    3x3 pixel patch around the converted pixel coordinate on each channel
    grayscale. Returns one entry per channel plus the summed TAC.

    Args:
        pdf_bytes: Raw PDF bytes.
        page_num: 1-indexed page number.
        x, y: PDF-space coordinates in points (origin lower-left,
            matching the sample_color endpoint).
        page_w, page_h: MediaBox width / height in points.
        dpi: Rendering resolution.
        tac_limit: TAC limit in percent (for ``limit_exceeded`` flag).

    Returns:
        ``{"x", "y", "dpi", "channels": [{"name", "percent"}, ...],
        "tac", "tac_limit", "limit_exceeded"}``.

    Raises:
        RuntimeError: If Ghostscript fails or no CMYK channels are produced
            (e.g. an RGB-only PDF with no separable inks). The caller
            surfaces this as a 422 for the UI to render a friendly
            "no separations available" message.
    """
    import numpy as np
    from PIL import Image

    with tempfile.TemporaryDirectory(prefix="lintpdf_dens_") as tmpdir:
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
            raise RuntimeError(f"Ghostscript separation failed: {stderr[:500]}")

        # Collect channel TIFFs: CMYK always, plus whatever spots ghostscript
        # discovered on this page.
        channel_files: list[tuple[str, str]] = []
        for ch_name in PROCESS_CHANNEL_ORDER:
            ch_tif = _find_channel_tif(tmpdir, ch_name, output_base)
            if ch_tif is not None:
                channel_files.append((ch_name, ch_tif))
        # Spot channels appear as filenames outside the process set. Walk
        # the tmpdir looking for ``(...).tif`` entries that aren't the
        # composite or one of the CMYK process names we already have.
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

        # Load the first channel to get image dimensions for the coord map.
        first_img = Image.open(channel_files[0][1]).convert("L")
        img_w, img_h = first_img.size
        scale_x = img_w / page_w if page_w else 1.0
        scale_y = img_h / page_h if page_h else 1.0
        px_x = round(x * scale_x)
        # PDF origin is lower-left; image origin is upper-left. Flip Y.
        px_y = round(img_h - y * scale_y)
        px_x = max(0, min(px_x, img_w - 1))
        px_y = max(0, min(px_y, img_h - 1))

        def _sample(path: str) -> float:
            img = Image.open(path).convert("L")
            arr = np.array(img, dtype=np.float32)
            # tiffsep encodes 0 = full ink, 255 = no ink. Invert to get
            # ink density, then normalise to 0-100.
            x0 = max(0, px_x - 1)
            x1 = min(img_w, px_x + 2)
            y0 = max(0, px_y - 1)
            y1 = min(img_h, px_y + 2)
            patch = arr[y0:y1, x0:x1]
            mean_ink = (255.0 - float(patch.mean())) * (100.0 / 255.0)
            # Clamp to [0, 100] to guard against rounding noise.
            return max(0.0, min(100.0, mean_ink))

        channels = [
            {"name": name, "percent": round(_sample(path), 2)} for name, path in channel_files
        ]
        tac = round(sum(ch["percent"] for ch in channels), 2)

        return {
            "x": x,
            "y": y,
            "dpi": dpi,
            "channels": channels,
            "tac": tac,
            "tac_limit": tac_limit,
            "limit_exceeded": tac > tac_limit,
        }
