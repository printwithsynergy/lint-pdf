"""Report generation engine for preflight results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from siftpdf.profiles.orchestrator import PreflightResult
    from siftpdf.reports.service import BrandingContext


class ReportEngine:
    """Generates reports in multiple formats from preflight results."""

    def generate(
        self,
        result: PreflightResult,
        fmt: str,
        *,
        branding: BrandingContext | None = None,
        pdf_bytes: bytes | None = None,
        detail_level: str = "standard",
    ) -> bytes:
        """Generate a report in the requested format.

        Args:
            result: Preflight result to generate report for.
            fmt: Output format ("json", "html", "pdf", "xml").
            branding: Optional white-label branding context.
            pdf_bytes: Original PDF bytes (enables page screenshots in html/pdf).
            detail_level: Report detail ("executive", "standard", "comprehensive").

        Returns:
            Report content as bytes.

        Raises:
            ValueError: If format is not supported.
        """
        if fmt == "json":
            return self.to_json(result)
        if fmt == "html":
            return self.to_html(
                result, branding=branding, pdf_bytes=pdf_bytes, detail_level=detail_level
            )
        if fmt == "pdf":
            return self.to_pdf(
                result, branding=branding, pdf_bytes=pdf_bytes, detail_level=detail_level
            )
        if fmt == "xml":
            return self.to_xml(result)
        msg = f"Unsupported report format: {fmt}"
        raise ValueError(msg)

    @staticmethod
    def to_json(result: PreflightResult) -> bytes:
        """Generate JSON report."""
        from siftpdf.reports.json_report import generate_json_report

        return generate_json_report(result)

    @staticmethod
    def to_html(
        result: PreflightResult,
        *,
        branding: BrandingContext | None = None,
        pdf_bytes: bytes | None = None,
        detail_level: str = "standard",
    ) -> bytes:
        """Generate HTML report with optional page screenshots."""
        from siftpdf.reports.html_report import generate_html_report

        return generate_html_report(
            result,
            branding=branding,
            pdf_bytes=pdf_bytes,
            detail_level=detail_level,
        )

    @staticmethod
    def to_pdf(
        result: PreflightResult,
        *,
        branding: BrandingContext | None = None,
        pdf_bytes: bytes | None = None,
        detail_level: str = "standard",
    ) -> bytes:
        """Generate PDF report with optional page screenshots."""
        from siftpdf.reports.pdf_report import generate_pdf_report

        return generate_pdf_report(
            result,
            branding=branding,
            pdf_bytes=pdf_bytes,
            detail_level=detail_level,
        )

    @staticmethod
    def to_xml(result: PreflightResult) -> bytes:
        """Generate XML report."""
        from siftpdf.reports.xml_report import generate_xml_report

        return generate_xml_report(result)

    @staticmethod
    def supported_formats() -> list[str]:
        """Return list of supported output formats."""
        return ["json", "html", "pdf", "xml"]
