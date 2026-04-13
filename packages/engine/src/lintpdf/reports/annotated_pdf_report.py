"""Annotated PDF report generator.

Renders the original PDF with color-coded finding overlays drawn directly
onto each page using pikepdf content streams.  Each finding gets:
  - A severity-colored semi-transparent rectangle over its bounding box
  - A numbered callout circle at the top-right corner of the bbox
  - A legend sidebar/page listing what each number means

Requires: pikepdf (already a dependency)
"""

from __future__ import annotations

import io
import logging
from typing import Any

logger = logging.getLogger(__name__)


# Severity colors (RGB 0-1 range for PDF operators)
_SEVERITY_COLORS = {
    "error": (0.937, 0.267, 0.267),  # #ef4444
    "warning": (0.961, 0.620, 0.043),  # #f59e0b
    "advisory": (0.231, 0.510, 0.965),  # #3b82f6
}

_SEVERITY_STROKE = {
    "error": (0.863, 0.149, 0.149),  # #dc2626
    "warning": (0.851, 0.467, 0.024),  # #d97706
    "advisory": (0.145, 0.388, 0.922),  # #2563eb
}

_SEVERITY_LABELS = {
    "error": "Error",
    "warning": "Warning",
    "advisory": "Info",
}

# Default DPI for page rendering
DEFAULT_ANNOTATION_DPI = 150

# Badge sizing (PDF points)
BADGE_RADIUS = 8
BADGE_FONT_SIZE = 9
LEGEND_FONT_SIZE = 7
LEGEND_LINE_HEIGHT = 12
LEGEND_MAX_ENTRIES = 40


def generate_annotated_pdf(
    pdf_bytes: bytes,
    findings: list[dict[str, Any]],
    *,
    annotation_dpi: int = DEFAULT_ANNOTATION_DPI,
    branding_name: str = "LintPDF",
) -> bytes:
    """Generate an annotated PDF with finding overlays.

    Approach: Use pikepdf to read the original PDF, then draw overlay
    rectangles, numbered callout badges, and a color legend directly
    onto each page using PDF content streams.

    Args:
        pdf_bytes: Original PDF file bytes.
        findings: List of finding dicts with bbox, severity, page_num, message.
        annotation_dpi: DPI for annotation rendering (unused in direct overlay mode).
        branding_name: Brand name for the annotation legend.

    Returns:
        Annotated PDF as bytes.
    """
    import pikepdf

    # Group findings by page
    findings_by_page: dict[int, list[dict[str, Any]]] = {}
    for f in findings:
        page_num = f.get("page_num", 0)
        if page_num < 1:
            continue
        if page_num not in findings_by_page:
            findings_by_page[page_num] = []
        findings_by_page[page_num].append(f)

    if not findings_by_page:
        # No page-level findings — return original with a summary page
        return _add_summary_page(pdf_bytes, findings, branding_name)

    # Open the PDF and add overlays
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))

    # Register Helvetica font for callout numbers
    helvetica = pikepdf.Dictionary(
        {
            "/Type": pikepdf.Name("/Font"),
            "/Subtype": pikepdf.Name("/Type1"),
            "/BaseFont": pikepdf.Name("/Helvetica-Bold"),
        }
    )

    for page_idx, page in enumerate(pdf.pages):
        page_num = page_idx + 1
        page_findings = findings_by_page.get(page_num, [])
        if not page_findings:
            continue

        # Get page MediaBox for coordinate reference
        media_box = page.get("/MediaBox")
        if media_box is None:
            continue

        mb = [float(v) for v in media_box]

        # Ensure resources exist
        if "/Resources" not in page:
            page["/Resources"] = pikepdf.Dictionary({})
        resources = page["/Resources"]
        if "/XObject" not in resources:
            resources["/XObject"] = pikepdf.Dictionary({})
        if "/Font" not in resources:
            resources["/Font"] = pikepdf.Dictionary({})

        # Add our font
        resources["/Font"]["/LPDFBadge"] = pdf.copy_foreign(helvetica) if False else helvetica

        # Build overlay content stream
        overlay_stream = _build_overlay_stream(page_findings, mb)
        if overlay_stream:
            overlay_dict = pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/XObject"),
                    "/Subtype": pikepdf.Name("/Form"),
                    "/BBox": media_box,
                    "/Resources": pikepdf.Dictionary(
                        {"/Font": pikepdf.Dictionary({"/LPDFBadge": helvetica})}
                    ),
                }
            )
            overlay_obj = pdf.make_stream(overlay_stream.encode("latin-1"), overlay_dict)

            xobjects = resources.get("/XObject", pikepdf.Dictionary({}))
            if not isinstance(xobjects, pikepdf.Dictionary):
                xobjects = pikepdf.Dictionary({})
            xobjects["/LintPDFOverlay"] = overlay_obj
            resources["/XObject"] = xobjects

            # Append overlay reference to content stream
            existing_contents = page.get("/Contents")
            if existing_contents is not None:
                overlay_ref = b"\nq /LintPDFOverlay Do Q\n"
                overlay_ref_stream = pdf.make_stream(overlay_ref)

                if isinstance(existing_contents, pikepdf.Array):
                    existing_contents.append(overlay_ref_stream)
                else:
                    page["/Contents"] = pikepdf.Array([existing_contents, overlay_ref_stream])

    # Add a findings legend page at the end
    _add_legend_page(pdf, findings_by_page, branding_name)

    # Write output
    output = io.BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue()


def _build_overlay_stream(
    findings: list[dict[str, Any]],
    media_box: list[float],
) -> str:
    """Build a PDF content stream with annotation rectangles and numbered badges."""
    lines: list[str] = []
    callout_num = 0

    for f in findings:
        bbox = f.get("bbox")
        has_bbox = bbox is not None and len(bbox) == 4 and bbox[0] is not None
        callout_num += 1

        if not has_bbox:
            continue

        severity = f.get("severity", "advisory")
        stroke = _SEVERITY_STROKE.get(severity, _SEVERITY_STROKE["advisory"])
        fill = _SEVERITY_COLORS.get(severity, _SEVERITY_COLORS["advisory"])

        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0

        if width <= 0 or height <= 0:
            continue

        # --- Draw rectangle ---
        lines.append("q")  # Save graphics state

        # Stroke color
        lines.append(f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG")
        # Fill color (lighter)
        lines.append(f"{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg")
        # Line width
        lines.append("2 w")
        # Dashed line for visual distinction
        lines.append("[4 2] 0 d")
        # Draw rectangle (fill and stroke)
        lines.append(f"{x0:.2f} {y0:.2f} {width:.2f} {height:.2f} re B")

        lines.append("Q")  # Restore graphics state

        # --- Draw numbered badge at top-right of bbox ---
        badge_x = x1 + 2
        badge_y = y1 - BADGE_RADIUS

        # Clamp badge to page bounds
        page_w = media_box[2] - media_box[0]
        page_h = media_box[3] - media_box[1]
        if badge_x + BADGE_RADIUS > media_box[0] + page_w:
            badge_x = x1 - BADGE_RADIUS - 2
        if badge_y + BADGE_RADIUS > media_box[1] + page_h:
            badge_y = media_box[1] + page_h - BADGE_RADIUS - 2
        if badge_y - BADGE_RADIUS < media_box[1]:
            badge_y = media_box[1] + BADGE_RADIUS + 2

        lines.append("q")
        # Badge circle (filled)
        lines.append(f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} rg")
        lines.append("1 1 1 RG")  # White outline
        lines.append("1 w")
        # Approximate circle with 4 Bezier curves
        r = BADGE_RADIUS
        k = 0.5523  # magic number for circle approximation
        cx, cy = badge_x, badge_y
        lines.append(f"{cx + r:.2f} {cy:.2f} m")
        lines.append(
            f"{cx + r:.2f} {cy + r * k:.2f} {cx + r * k:.2f} {cy + r:.2f} {cx:.2f} {cy + r:.2f} c"
        )
        lines.append(
            f"{cx - r * k:.2f} {cy + r:.2f} {cx - r:.2f} {cy + r * k:.2f} {cx - r:.2f} {cy:.2f} c"
        )
        lines.append(
            f"{cx - r:.2f} {cy - r * k:.2f} {cx - r * k:.2f} {cy - r:.2f} {cx:.2f} {cy - r:.2f} c"
        )
        lines.append(
            f"{cx + r * k:.2f} {cy - r:.2f} {cx + r:.2f} {cy - r * k:.2f} {cx + r:.2f} {cy:.2f} c"
        )
        lines.append("B")  # Fill and stroke

        # Badge number (white text)
        text = str(callout_num)
        # Approximate centering
        text_x = cx - len(text) * BADGE_FONT_SIZE * 0.3
        text_y = cy - BADGE_FONT_SIZE * 0.35
        lines.append(f"BT /LPDFBadge {BADGE_FONT_SIZE} Tf")
        lines.append("1 1 1 rg")  # White text
        lines.append(f"{text_x:.2f} {text_y:.2f} Td")
        lines.append(f"({text}) Tj ET")

        lines.append("Q")

    return "\n".join(lines)


def _add_legend_page(
    pdf: Any,
    findings_by_page: dict[int, list[dict[str, Any]]],
    branding_name: str,
) -> None:
    """Add a findings legend page at the end of the PDF."""
    import pikepdf

    page_width = 612  # US Letter
    page_height = 792
    margin = 54  # 0.75 inches
    y = page_height - margin

    lines: list[str] = []

    # Title
    lines.append(
        f"BT /F1 16 Tf {margin} {y} Td ({branding_name} Preflight Report \u2014 Findings Legend) Tj ET"
    )
    y -= 28

    # Color legend
    for sev, label in _SEVERITY_LABELS.items():
        color = _SEVERITY_STROKE.get(sev, (0, 0, 0))
        lines.append("q")
        lines.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
        lines.append(f"{margin} {y - 2} 10 10 re f")
        lines.append("Q")
        lines.append(f"BT /F1 10 Tf {margin + 16} {y} Td ({label}) Tj ET")
        y -= 16

    y -= 12

    # Findings by page
    entry_count = 0
    for page_num in sorted(findings_by_page.keys()):
        if entry_count >= LEGEND_MAX_ENTRIES:
            lines.append(
                f"BT /F1 9 Tf {margin} {y} Td (... and more findings \\(see full report\\)) Tj ET"
            )
            break

        page_findings = findings_by_page[page_num]
        lines.append(f"BT /F1 11 Tf {margin} {y} Td (Page {page_num}) Tj ET")
        y -= 16

        for callout_num, f in enumerate(page_findings, start=1):
            entry_count += 1
            if entry_count > LEGEND_MAX_ENTRIES:
                break

            severity = f.get("severity", "advisory")
            color = _SEVERITY_STROKE.get(severity, (0, 0, 0))
            check_id = f.get("inspection_id", "")
            # Escape parentheses in message for PDF string
            message = f.get("message", "")[:80].replace("(", "\\(").replace(")", "\\)")

            lines.append("q")
            # Badge circle
            lines.append(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg")
            cx = margin + 8
            cy_badge = y + 3
            r = 5
            k = 0.5523
            lines.append(f"{cx + r:.2f} {cy_badge:.2f} m")
            lines.append(
                f"{cx + r:.2f} {cy_badge + r * k:.2f} {cx + r * k:.2f} {cy_badge + r:.2f} {cx:.2f} {cy_badge + r:.2f} c"
            )
            lines.append(
                f"{cx - r * k:.2f} {cy_badge + r:.2f} {cx - r:.2f} {cy_badge + r * k:.2f} {cx - r:.2f} {cy_badge:.2f} c"
            )
            lines.append(
                f"{cx - r:.2f} {cy_badge - r * k:.2f} {cx - r * k:.2f} {cy_badge - r:.2f} {cx:.2f} {cy_badge - r:.2f} c"
            )
            lines.append(
                f"{cx + r * k:.2f} {cy_badge - r:.2f} {cx + r:.2f} {cy_badge - r * k:.2f} {cx + r:.2f} {cy_badge:.2f} c"
            )
            lines.append("f")

            # Number in badge
            lines.append(
                f"BT /F1 {LEGEND_FONT_SIZE} Tf 1 1 1 rg {cx - 2:.2f} {cy_badge - 3:.2f} Td ({callout_num}) Tj ET"
            )
            lines.append("Q")

            # Check ID + message
            lines.append(f"BT /F1 8 Tf 0 0 0 rg {margin + 20} {y} Td ({check_id}: {message}) Tj ET")
            y -= LEGEND_LINE_HEIGHT

            # Page break if we run out of space
            if y < margin + 20 and entry_count < LEGEND_MAX_ENTRIES:
                break  # Just stop on this page — not worth adding another page for legend

        y -= 8  # gap between page groups

    # Create the summary page
    summary_page = pikepdf.Dictionary(
        {
            "/Type": pikepdf.Name("/Page"),
            "/MediaBox": pikepdf.Array([0, 0, page_width, page_height]),
            "/Resources": pikepdf.Dictionary(
                {
                    "/Font": pikepdf.Dictionary(
                        {
                            "/F1": pikepdf.Dictionary(
                                {
                                    "/Type": pikepdf.Name("/Font"),
                                    "/Subtype": pikepdf.Name("/Type1"),
                                    "/BaseFont": pikepdf.Name("/Helvetica"),
                                }
                            )
                        }
                    )
                }
            ),
        }
    )

    content = "\n".join(lines)
    content_stream = pdf.make_stream(content.encode("latin-1"))
    summary_page["/Contents"] = content_stream

    pdf.pages.append(pikepdf.Page(summary_page))


def _add_summary_page(
    pdf_bytes: bytes,
    findings: list[dict[str, Any]],
    branding_name: str,
) -> bytes:
    """Add a summary page at the end of the PDF listing all findings.

    Used when no findings have bounding boxes.
    """
    import pikepdf

    pdf = pikepdf.open(io.BytesIO(pdf_bytes))

    # Count findings by severity
    error_count = sum(1 for f in findings if f.get("severity") == "error")
    warning_count = sum(1 for f in findings if f.get("severity") == "warning")
    advisory_count = sum(1 for f in findings if f.get("severity") == "advisory")
    total = len(findings)

    margin = 54
    y = 740

    lines: list[str] = []
    lines.append(f"BT /F1 16 Tf {margin} {y} Td ({branding_name} Preflight Report) Tj ET")
    y -= 28
    lines.append(f"BT /F1 11 Tf {margin} {y} Td (Total findings: {total}) Tj ET")
    y -= 16
    lines.append(
        f"BT /F1 11 Tf {margin} {y} Td (Errors: {error_count}  |  Warnings: {warning_count}  |  Info: {advisory_count}) Tj ET"
    )
    y -= 24

    # List individual findings
    for f in findings[:LEGEND_MAX_ENTRIES]:
        severity = f.get("severity", "advisory")
        sev_label = _SEVERITY_LABELS.get(severity, severity)
        check_id = f.get("inspection_id", "")
        page = f.get("page_num", 0)
        message = f.get("message", "")[:70].replace("(", "\\(").replace(")", "\\)")
        page_text = f"p.{page}" if page > 0 else "doc"

        lines.append(
            f"BT /F1 8 Tf {margin} {y} Td ([{sev_label}] {check_id} \\({page_text}\\): {message}) Tj ET"
        )
        y -= LEGEND_LINE_HEIGHT

        if y < 60:
            lines.append(
                f"BT /F1 8 Tf {margin} {y} Td (... and {total - findings.index(f) - 1} more findings) Tj ET"
            )
            break

    # Create the summary page
    summary_page = pikepdf.Dictionary(
        {
            "/Type": pikepdf.Name("/Page"),
            "/MediaBox": pikepdf.Array([0, 0, 612, 792]),  # US Letter
            "/Resources": pikepdf.Dictionary(
                {
                    "/Font": pikepdf.Dictionary(
                        {
                            "/F1": pikepdf.Dictionary(
                                {
                                    "/Type": pikepdf.Name("/Font"),
                                    "/Subtype": pikepdf.Name("/Type1"),
                                    "/BaseFont": pikepdf.Name("/Helvetica"),
                                }
                            )
                        }
                    )
                }
            ),
        }
    )

    content = "\n".join(lines)
    content_stream = pdf.make_stream(content.encode("latin-1"))
    summary_page["/Contents"] = content_stream

    pdf.pages.append(pikepdf.Page(summary_page))

    output = io.BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue()
