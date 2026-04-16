"""Bake-to-PDF reviewer markup export.

Stamps the user-drawn viewer annotations (rectangles, circles, arrows,
freehand strokes, sticky-note pins) and their threaded comments onto
the original PDF using pikepdf content-stream overlays, then appends an
appendix page that resolves numbered note pins to their bodies + full
comment threads.

Distinct from ``annotated_pdf_report`` (which stamps preflight
*findings*). This renderer backs the ``annotated_pdf_markup`` report
format so reviewers can print or forward a marked-up PDF after the
collaboration phase.
"""

from __future__ import annotations

import io
import logging
from typing import Any

logger = logging.getLogger(__name__)


# Default stroke width for drawn shapes, in PDF points. 1.5pt reads
# cleanly at both print scale and screen zoom without drowning small
# rectangles.
_STROKE_WIDTH = 1.5

# Sticky-note pin geometry (PDF points).
_PIN_RADIUS = 8
_PIN_FONT_SIZE = 9

# Appendix page layout.
_APPENDIX_PAGE_W = 612.0  # US Letter
_APPENDIX_PAGE_H = 792.0
_APPENDIX_MARGIN = 54.0
_APPENDIX_LINE_HEIGHT = 12.0
_APPENDIX_FONT_SIZE = 9
_APPENDIX_HEADER_FONT_SIZE = 14


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """``#rrggbb`` → ``(r, g, b)`` floats in 0-1.

    Accepts 3- or 6-character hex codes. Falls back to a red tone on
    parse failures so the overlay stays visible rather than disappearing
    into a black stroke.
    """
    try:
        raw = hex_color.strip()
        if raw.startswith("#"):
            raw = raw[1:]
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        if len(raw) != 6:
            return (0.86, 0.15, 0.15)
        r = int(raw[0:2], 16) / 255.0
        g = int(raw[2:4], 16) / 255.0
        b = int(raw[4:6], 16) / 255.0
        return (r, g, b)
    except Exception:
        return (0.86, 0.15, 0.15)


def _pdf_string(s: str) -> str:
    """Escape a Python string for use inside a PDF ``(...)`` literal.

    Also replaces any character that isn't representable in latin-1
    with ``"?"`` so the final ``.encode("latin-1", errors="replace")`` in the content
    stream can't blow up on a surrogate emoji or a CJK glyph that
    slipped into a comment body. A custom font subset would be the
    "right" fix for multilingual markup; until that lands, a sanitised
    ASCII rendering is better than a 500.
    """
    escaped = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\r", " ")
    return escaped.encode("latin-1", errors="replace").decode("latin-1")


def _build_bezier_circle(cx: float, cy: float, r: float) -> list[str]:
    """Return the PDF operators that draw a circle of radius ``r`` at ``(cx, cy)``.

    Uses the standard four-cubic-Bezier approximation (magic constant
    ``k`` below). Caller is expected to emit the ``f`` / ``S`` / ``B``
    operator afterwards depending on whether they want fill, stroke, or
    both.
    """
    k = 0.5523
    return [
        f"{cx + r:.2f} {cy:.2f} m",
        f"{cx + r:.2f} {cy + r * k:.2f} {cx + r * k:.2f} {cy + r:.2f} {cx:.2f} {cy + r:.2f} c",
        f"{cx - r * k:.2f} {cy + r:.2f} {cx - r:.2f} {cy + r * k:.2f} {cx - r:.2f} {cy:.2f} c",
        f"{cx - r:.2f} {cy - r * k:.2f} {cx - r * k:.2f} {cy - r:.2f} {cx:.2f} {cy - r:.2f} c",
        f"{cx + r * k:.2f} {cy - r:.2f} {cx + r:.2f} {cy - r * k:.2f} {cx + r:.2f} {cy:.2f} c",
    ]


def _draw_shape(
    ann: dict[str, Any],
    note_index_by_id: dict[str, int],
) -> list[str]:
    """Return the PDF operators that stamp a single annotation.

    ``ann`` is the serialised :class:`ViewerAnnotation` dict. Geometry
    coordinates are already in PDF points with lower-left origin, so
    they can be emitted directly into the page content stream.
    """
    kind = ann.get("kind")
    color = _hex_to_rgb(str(ann.get("color", "#dc2626")))
    g = ann.get("geometry") or {}
    lines: list[str] = ["q"]
    # Stroke colour + width. Fill matches stroke for notes (pin) and is
    # left transparent for open shapes so underlying content shows.
    lines.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG")
    lines.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
    lines.append(f"{_STROKE_WIDTH} w")

    if kind == "rect":
        try:
            x0 = float(g["x0"])
            y0 = float(g["y0"])
            x1 = float(g["x1"])
            y1 = float(g["y1"])
        except (KeyError, TypeError, ValueError):
            lines.append("Q")
            return lines
        w = x1 - x0
        h = y1 - y0
        lines.append(f"{x0:.2f} {y0:.2f} {w:.2f} {h:.2f} re S")

    elif kind == "circle":
        try:
            cx = float(g["cx"])
            cy = float(g["cy"])
            rx = float(g["rx"])
            ry = float(g["ry"])
        except (KeyError, TypeError, ValueError):
            lines.append("Q")
            return lines
        # Draw as a Bezier ellipse. With rx == ry, this is the same path
        # as the sticky-note circle; we reuse the helper for rx and
        # stretch vertically via a scaled CTM. A dedicated ellipse
        # approximation keeps the output self-contained.
        k = 0.5523
        lines.append(f"{cx + rx:.2f} {cy:.2f} m")
        lines.append(
            f"{cx + rx:.2f} {cy + ry * k:.2f} {cx + rx * k:.2f} {cy + ry:.2f} {cx:.2f} {cy + ry:.2f} c"
        )
        lines.append(
            f"{cx - rx * k:.2f} {cy + ry:.2f} {cx - rx:.2f} {cy + ry * k:.2f} {cx - rx:.2f} {cy:.2f} c"
        )
        lines.append(
            f"{cx - rx:.2f} {cy - ry * k:.2f} {cx - rx * k:.2f} {cy - ry:.2f} {cx:.2f} {cy - ry:.2f} c"
        )
        lines.append(
            f"{cx + rx * k:.2f} {cy - ry:.2f} {cx + rx:.2f} {cy - ry * k:.2f} {cx + rx:.2f} {cy:.2f} c"
        )
        lines.append("S")

    elif kind == "arrow":
        try:
            x0 = float(g["x0"])
            y0 = float(g["y0"])
            x1 = float(g["x1"])
            y1 = float(g["y1"])
        except (KeyError, TypeError, ValueError):
            lines.append("Q")
            return lines
        lines.append(f"{x0:.2f} {y0:.2f} m {x1:.2f} {y1:.2f} l S")
        # Filled arrow head. Direction vector.
        dx = x1 - x0
        dy = y1 - y0
        import math

        length = math.hypot(dx, dy) or 1.0
        ux = dx / length
        uy = dy / length
        size = 10.0
        # Two shoulder points perpendicular to the direction.
        left_x = x1 - size * ux + size * 0.5 * -uy
        left_y = y1 - size * uy + size * 0.5 * ux
        right_x = x1 - size * ux - size * 0.5 * -uy
        right_y = y1 - size * uy - size * 0.5 * ux
        lines.append(f"{x1:.2f} {y1:.2f} m")
        lines.append(f"{left_x:.2f} {left_y:.2f} l")
        lines.append(f"{right_x:.2f} {right_y:.2f} l")
        lines.append("h f")

    elif kind == "freehand":
        pts = g.get("points") or []
        if not pts:
            lines.append("Q")
            return lines
        for i, p in enumerate(pts):
            try:
                px = float(p["x"])
                py = float(p["y"])
            except (KeyError, TypeError, ValueError):
                continue
            op = "m" if i == 0 else "l"
            lines.append(f"{px:.2f} {py:.2f} {op}")
        lines.append("S")

    elif kind == "note":
        try:
            nx = float(g["x"])
            ny = float(g["y"])
        except (KeyError, TypeError, ValueError):
            lines.append("Q")
            return lines
        # Filled circle + white numeric badge.
        lines.extend(_build_bezier_circle(nx, ny, _PIN_RADIUS))
        lines.append("f")
        idx = note_index_by_id.get(str(ann.get("id", "")))
        if idx is not None:
            badge_text = str(idx)
            # Approximate centring — Helvetica-Bold width ~0.55 per em.
            text_x = nx - len(badge_text) * _PIN_FONT_SIZE * 0.3
            text_y = ny - _PIN_FONT_SIZE * 0.35
            lines.append(f"BT /LPDFMarkup {_PIN_FONT_SIZE} Tf 1 1 1 rg")
            lines.append(f"{text_x:.2f} {text_y:.2f} Td ({badge_text}) Tj ET")

    lines.append("Q")
    return lines


def _build_overlay_stream(
    page_annotations: list[dict[str, Any]],
    note_index_by_id: dict[str, int],
) -> str:
    """Assemble the overlay content stream for all annotations on a page."""
    out: list[str] = []
    for ann in page_annotations:
        out.extend(_draw_shape(ann, note_index_by_id))
    return "\n".join(out)


def _wrap_text(text: str, max_chars: int) -> list[str]:
    """Naive word-wrap for the appendix. Good enough for Helvetica at 9pt."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        if not current:
            current = w
        elif len(current) + 1 + len(w) <= max_chars:
            current = f"{current} {w}"
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines or [""]


def generate_markup_pdf(
    pdf_bytes: bytes,
    annotations: list[dict[str, Any]],
    comments_by_annotation: dict[str, list[dict[str, Any]]],
    *,
    branding_name: str = "LintPDF",
) -> bytes:
    """Stamp reviewer markup + comment threads onto the original PDF.

    Args:
        pdf_bytes: Original PDF file bytes.
        annotations: Serialised :class:`ViewerAnnotation` rows
            (``{id, page_num, kind, geometry, color, text, author_email,
            created_at}``). ``geometry`` is in PDF-point space with the
            lower-left origin, matching the engine database.
        comments_by_annotation: Annotation id → list of serialised
            :class:`ViewerAnnotationComment` rows (``{author_email, body,
            created_at}`` at minimum).
        branding_name: Label used in the appendix header.

    Returns:
        The annotated PDF as bytes.
    """
    import pikepdf

    annotations_by_page: dict[int, list[dict[str, Any]]] = {}
    for a in annotations:
        page = int(a.get("page_num", 0) or 0)
        if page < 1:
            continue
        annotations_by_page.setdefault(page, []).append(a)

    # Number notes globally so the appendix and the in-page pins line up.
    note_index_by_id: dict[str, int] = {}
    next_idx = 1
    for page in sorted(annotations_by_page):
        for a in annotations_by_page[page]:
            if a.get("kind") == "note":
                note_index_by_id[str(a.get("id", ""))] = next_idx
                next_idx += 1

    pdf = pikepdf.open(io.BytesIO(pdf_bytes))

    # Fonts: Helvetica-Bold for the numeric pin badges, Helvetica for
    # the appendix body.
    helvetica_bold = pikepdf.Dictionary(
        {
            "/Type": pikepdf.Name("/Font"),
            "/Subtype": pikepdf.Name("/Type1"),
            "/BaseFont": pikepdf.Name("/Helvetica-Bold"),
        }
    )
    helvetica = pikepdf.Dictionary(
        {
            "/Type": pikepdf.Name("/Font"),
            "/Subtype": pikepdf.Name("/Type1"),
            "/BaseFont": pikepdf.Name("/Helvetica"),
        }
    )

    for page_idx, page in enumerate(pdf.pages):
        page_num = page_idx + 1
        page_annotations = annotations_by_page.get(page_num, [])
        if not page_annotations:
            continue

        media_box = page.get("/MediaBox")
        if media_box is None:
            continue

        if "/Resources" not in page:
            page["/Resources"] = pikepdf.Dictionary({})
        resources = page["/Resources"]
        if "/XObject" not in resources:
            resources["/XObject"] = pikepdf.Dictionary({})
        if "/Font" not in resources:
            resources["/Font"] = pikepdf.Dictionary({})
        resources["/Font"]["/LPDFMarkup"] = helvetica_bold

        overlay_stream = _build_overlay_stream(page_annotations, note_index_by_id)
        if not overlay_stream:
            continue

        overlay_dict = pikepdf.Dictionary(
            {
                "/Type": pikepdf.Name("/XObject"),
                "/Subtype": pikepdf.Name("/Form"),
                "/BBox": media_box,
                "/Resources": pikepdf.Dictionary(
                    {"/Font": pikepdf.Dictionary({"/LPDFMarkup": helvetica_bold})}
                ),
            }
        )
        overlay_obj = pdf.make_stream(overlay_stream.encode("latin-1", errors="replace"), overlay_dict)

        xobjects = resources.get("/XObject", pikepdf.Dictionary({}))
        if not isinstance(xobjects, pikepdf.Dictionary):
            xobjects = pikepdf.Dictionary({})
        xobjects["/LintPDFMarkup"] = overlay_obj
        resources["/XObject"] = xobjects

        existing_contents = page.get("/Contents")
        overlay_ref = b"\nq /LintPDFMarkup Do Q\n"
        overlay_ref_stream = pdf.make_stream(overlay_ref)
        if existing_contents is None:
            page["/Contents"] = overlay_ref_stream
        elif isinstance(existing_contents, pikepdf.Array):
            existing_contents.append(overlay_ref_stream)
        else:
            page["/Contents"] = pikepdf.Array([existing_contents, overlay_ref_stream])

    # Appendix pages listing notes + threads.
    _append_markup_appendix(
        pdf,
        annotations_by_page=annotations_by_page,
        note_index_by_id=note_index_by_id,
        comments_by_annotation=comments_by_annotation,
        branding_name=branding_name,
        helvetica=helvetica,
    )

    output = io.BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue()


def _append_markup_appendix(
    pdf: Any,
    *,
    annotations_by_page: dict[int, list[dict[str, Any]]],
    note_index_by_id: dict[str, int],
    comments_by_annotation: dict[str, list[dict[str, Any]]],
    branding_name: str,
    helvetica: Any,
) -> None:
    """Append one or more appendix pages that resolve note pins to bodies + threads."""
    import pikepdf

    # If there are no numbered notes, nothing to resolve.
    if not note_index_by_id:
        return

    pages_needed: list[list[str]] = []
    current: list[str] = []
    y = _APPENDIX_PAGE_H - _APPENDIX_MARGIN
    margin = _APPENDIX_MARGIN
    wrap_chars = 90  # Helvetica 9pt at ~0.5em/char fits comfortably in margin.

    def _flush_page() -> None:
        nonlocal current, y
        if current:
            pages_needed.append(current)
        current = []
        y = _APPENDIX_PAGE_H - _APPENDIX_MARGIN

    def _emit(lines: list[str], advance: float) -> None:
        nonlocal y
        if y - advance < margin:
            _flush_page()
        current.extend(lines)
        y -= advance

    # Header on the first page.
    current.append(
        f"BT /F1 {_APPENDIX_HEADER_FONT_SIZE} Tf {margin} {y} Td "
        # ASCII-only header so the latin-1 content-stream encoding is
        # safe regardless of branding_name contents. An em-dash would
        # need a custom font encoding table to render predictably.
        f"({_pdf_string(branding_name)} -- Markup Notes) Tj ET"
    )
    y -= _APPENDIX_HEADER_FONT_SIZE + 8
    current.append(
        f"BT /F1 {_APPENDIX_FONT_SIZE} Tf {margin} {y} Td "
        "(Each numbered pin below corresponds to a sticky-note on the matching page.) Tj ET"
    )
    y -= _APPENDIX_LINE_HEIGHT + 6

    for page_num in sorted(annotations_by_page):
        page_notes = [a for a in annotations_by_page[page_num] if a.get("kind") == "note"]
        if not page_notes:
            continue

        hdr = f"BT /F1 {_APPENDIX_FONT_SIZE + 1} Tf {margin} {y} Td (Page {page_num}) Tj ET"
        _emit([hdr], _APPENDIX_LINE_HEIGHT + 2)

        for note in page_notes:
            idx = note_index_by_id.get(str(note.get("id", "")))
            if idx is None:
                continue
            author = str(note.get("author_email", ""))
            text = str(note.get("text") or "(empty note)")

            # Header line for this note.
            head = (
                f"BT /F1 {_APPENDIX_FONT_SIZE} Tf {margin} {y} Td "
                f"({idx}. {_pdf_string(author)}) Tj ET"
            )
            _emit([head], _APPENDIX_LINE_HEIGHT)

            # Wrapped body.
            for wline in _wrap_text(text, wrap_chars):
                body = (
                    f"BT /F1 {_APPENDIX_FONT_SIZE} Tf {margin + 14} {y} Td "
                    f"({_pdf_string(wline)}) Tj ET"
                )
                _emit([body], _APPENDIX_LINE_HEIGHT)

            # Comment thread.
            thread = comments_by_annotation.get(str(note.get("id", "")), [])
            for c in thread:
                c_author = str(c.get("author_email", ""))
                c_body = str(c.get("body", ""))
                # Use ASCII arrow "-> " instead of U+21B3 so the
                # content stream round-trips through latin-1 (required
                # by pikepdf's make_stream) without relying on a custom
                # font encoding.
                head = (
                    f"BT /F1 {_APPENDIX_FONT_SIZE} Tf {margin + 14} {y} Td "
                    f"(-> {_pdf_string(c_author)}) Tj ET"
                )
                _emit([head], _APPENDIX_LINE_HEIGHT)
                for wline in _wrap_text(c_body, wrap_chars - 4):
                    body = (
                        f"BT /F1 {_APPENDIX_FONT_SIZE} Tf {margin + 28} {y} Td "
                        f"({_pdf_string(wline)}) Tj ET"
                    )
                    _emit([body], _APPENDIX_LINE_HEIGHT)

            _emit([], 6)  # gap between notes

        _emit([], 6)  # gap between page groups

    _flush_page()

    for page_lines in pages_needed:
        page_obj = pikepdf.Dictionary(
            {
                "/Type": pikepdf.Name("/Page"),
                "/MediaBox": pikepdf.Array([0, 0, _APPENDIX_PAGE_W, _APPENDIX_PAGE_H]),
                "/Resources": pikepdf.Dictionary({"/Font": pikepdf.Dictionary({"/F1": helvetica})}),
            }
        )
        content_stream = pdf.make_stream("\n".join(page_lines).encode("latin-1", errors="replace"))
        page_obj["/Contents"] = content_stream
        pdf.pages.append(pikepdf.Page(page_obj))
