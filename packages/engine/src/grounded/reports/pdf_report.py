"""PDF report generation using WeasyPrint."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grounded.profiles.orchestrator import PreflightResult


def generate_pdf_report(result: PreflightResult) -> bytes:
    """Generate a PDF report from preflight results.

    Uses WeasyPrint to convert the HTML report to PDF.

    Args:
        result: Preflight result to render.

    Returns:
        PDF bytes.
    """
    from weasyprint import HTML

    from grounded.reports.html_report import generate_html_report

    html_bytes = generate_html_report(result)
    html_string = html_bytes.decode("utf-8")

    pdf_bytes: bytes = HTML(string=html_string).write_pdf()
    return pdf_bytes
