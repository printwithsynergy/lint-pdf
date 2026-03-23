"""Annotated PDF report generator.

Renders each PDF page as an image and overlays finding bounding boxes
with color-coded annotations. Produces a new PDF with visual indicators
showing exactly where issues were detected.

Requires: pikepdf (already a dependency), Pillow, reportlab
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass

# Severity colors (RGBA)
_SEVERITY_COLORS = {
    "error": (239, 68, 68, 128),    # Red, semi-transparent
    "warning": (245, 158, 11, 128),    # Amber, semi-transparent
    "advisory": (59, 130, 246, 128),  # Blue, semi-transparent
}

_SEVERITY_STROKE = {
    "error": (220, 38, 38),    # Darker red
    "warning": (217, 119, 6),     # Darker amber
    "advisory": (37, 99, 235),   # Darker blue
}

# Default DPI for page rendering
DEFAULT_ANNOTATION_DPI = 150


def generate_annotated_pdf(
    pdf_bytes: bytes,
    findings: list[dict[str, Any]],
    *,
    annotation_dpi: int = DEFAULT_ANNOTATION_DPI,
    branding_name: str = "LintPDF",
) -> bytes:
    """Generate an annotated PDF with finding overlays.

    Approach: Use pikepdf to read the original PDF, then draw overlay
    rectangles and labels directly onto each page using PDF content streams.
    This avoids external rendering dependencies and preserves the original
    PDF quality.

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
        if f.get("bbox") is None:
            continue
        page_num = f.get("page_num", 0)
        if page_num < 1:
            continue
        if page_num not in findings_by_page:
            findings_by_page[page_num] = []
        findings_by_page[page_num].append(f)

    if not findings_by_page:
        # No findings with bounding boxes — return original with a summary page
        return _add_summary_page(pdf_bytes, findings, branding_name)

    # Open the PDF and add overlays
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))

    for page_idx, page in enumerate(pdf.pages):
        page_num = page_idx + 1
        page_findings = findings_by_page.get(page_num, [])
        if not page_findings:
            continue

        # Get page MediaBox for coordinate reference
        media_box = page.get("/MediaBox")
        if media_box is None:
            continue

        # Build overlay content stream
        overlay_stream = _build_overlay_stream(page_findings)
        if overlay_stream:
            # Create a Form XObject for the overlay
            overlay_dict = pikepdf.Dictionary(
                {
                    "/Type": pikepdf.Name("/XObject"),
                    "/Subtype": pikepdf.Name("/Form"),
                    "/BBox": media_box,
                    "/Resources": pikepdf.Dictionary({}),
                }
            )
            overlay_obj = pdf.make_stream(
                overlay_stream.encode("latin-1"), overlay_dict
            )

            # Add overlay to page resources
            if "/XObject" not in page.get("/Resources", pikepdf.Dictionary()):
                if "/Resources" not in page:
                    page["/Resources"] = pikepdf.Dictionary({})
                page["/Resources"]["/XObject"] = pikepdf.Dictionary({})

            resources = page["/Resources"]
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
                    page["/Contents"] = pikepdf.Array(
                        [existing_contents, overlay_ref_stream]
                    )

    # Write output
    output = io.BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue()


def _build_overlay_stream(findings: list[dict[str, Any]]) -> str:
    """Build a PDF content stream with annotation rectangles.

    Uses PDF graphics operators to draw semi-transparent rectangles
    over finding bounding boxes.
    """
    lines: list[str] = []

    for f in findings:
        bbox = f.get("bbox")
        if bbox is None or len(bbox) != 4:
            continue

        severity = f.get("severity", "advisory")
        stroke_color = _SEVERITY_STROKE.get(severity, (37, 99, 235))
        fill_color = _SEVERITY_COLORS.get(severity, (59, 130, 246, 128))

        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0

        if width <= 0 or height <= 0:
            continue

        # Set graphics state for semi-transparent overlay
        lines.append("q")  # Save graphics state

        # Set stroke color (RGB, 0-1 range)
        r, g, b = stroke_color
        lines.append(f"{r / 255:.3f} {g / 255:.3f} {b / 255:.3f} RG")

        # Set fill color with alpha (using transparency via ExtGState would
        # require more setup, so we use a lighter fill instead)
        fr, fg, fb, _fa = fill_color
        lines.append(f"{fr / 255:.3f} {fg / 255:.3f} {fb / 255:.3f} rg")

        # Set line width
        lines.append("1.5 w")

        # Draw rectangle (fill and stroke)
        lines.append(f"{x0:.2f} {y0:.2f} {width:.2f} {height:.2f} re B")

        lines.append("Q")  # Restore graphics state

    return "\n".join(lines)


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

    # Create a simple text-based summary page
    summary_text = (
        f"BT /F1 14 Tf 72 750 Td "
        f"({branding_name} Annotated Report - Summary) Tj ET\n"
        f"BT /F1 10 Tf 72 720 Td "
        f"(Total findings: {total}) Tj ET\n"
        f"BT /F1 10 Tf 72 706 Td "
        f"(Error: {error_count} | Warning: {warning_count} | Advisory: {advisory_count}) Tj ET\n"
    )

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

    content_stream = pdf.make_stream(summary_text.encode("latin-1"))
    summary_page["/Contents"] = content_stream

    pdf.pages.append(pikepdf.Page(summary_page))

    output = io.BytesIO()
    pdf.save(output)
    pdf.close()
    return output.getvalue()
