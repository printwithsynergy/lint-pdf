"""Report generation engine for preflight results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.profiles.orchestrator import PreflightResult


class ReportEngine:
    """Generates reports in multiple formats from preflight results."""

    def generate(self, result: PreflightResult, fmt: str) -> bytes:
        """Generate a report in the requested format.

        Args:
            result: Preflight result to generate report for.
            fmt: Output format ("json", "html", "pdf", "xml").

        Returns:
            Report content as bytes.

        Raises:
            ValueError: If format is not supported.
        """
        if fmt == "json":
            return self.to_json(result)
        if fmt == "html":
            return self.to_html(result)
        if fmt == "pdf":
            return self.to_pdf(result)
        if fmt == "xml":
            return self.to_xml(result)
        msg = f"Unsupported report format: {fmt}"
        raise ValueError(msg)

    @staticmethod
    def to_json(result: PreflightResult) -> bytes:
        """Generate JSON report."""
        from lintpdf.reports.json_report import generate_json_report

        return generate_json_report(result)

    @staticmethod
    def to_html(result: PreflightResult) -> bytes:
        """Generate HTML report."""
        from lintpdf.reports.html_report import generate_html_report

        return generate_html_report(result)

    @staticmethod
    def to_pdf(result: PreflightResult) -> bytes:
        """Generate PDF report."""
        from lintpdf.reports.pdf_report import generate_pdf_report

        return generate_pdf_report(result)

    @staticmethod
    def to_xml(result: PreflightResult) -> bytes:
        """Generate XML report."""
        from lintpdf.reports.xml_report import generate_xml_report

        return generate_xml_report(result)

    @staticmethod
    def supported_formats() -> list[str]:
        """Return list of supported output formats."""
        return ["json", "html", "pdf", "xml"]
