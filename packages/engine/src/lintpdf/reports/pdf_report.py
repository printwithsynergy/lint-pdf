"""PDF report generation using WeasyPrint."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.profiles.orchestrator import PreflightResult
    from lintpdf.reports.service import BrandingContext


def generate_pdf_report(
    result: PreflightResult,
    *,
    branding: BrandingContext | None = None,
    pdf_bytes: bytes | None = None,
    annotation_dpi: int = 150,
    detail_level: str = "standard",
) -> bytes:
    """Generate a PDF report from preflight results.

    Uses WeasyPrint to convert the HTML report to PDF.  When *pdf_bytes*
    is provided, annotated page screenshots are embedded in the report.

    Args:
        result: Preflight result to render.
        branding: Optional white-label branding context.
        pdf_bytes: Original PDF bytes for page screenshot rendering.
        annotation_dpi: DPI for page screenshot rendering.
        detail_level: Report detail ("executive", "standard", "comprehensive").

    Returns:
        PDF bytes.
    """
    from weasyprint import HTML

    from lintpdf.reports.html_report import generate_html_report

    html_bytes = generate_html_report(
        result,
        branding=branding,
        pdf_bytes=pdf_bytes,
        annotation_dpi=annotation_dpi,
        detail_level=detail_level,
    )
    html_string = html_bytes.decode("utf-8")

    pdf_bytes_out: bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes_out
