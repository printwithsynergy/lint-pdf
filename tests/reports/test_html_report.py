"""Tests for HTML report generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.profiles.orchestrator import PreflightResult

from lintpdf.reports.html_report import generate_html_report


class TestHtmlReport:
    @staticmethod
    def test_generates_html(sample_result: PreflightResult) -> None:
        report_bytes = generate_html_report(sample_result)
        html = report_bytes.decode("utf-8")
        assert "<!doctype html>" in html
        assert "</html>" in html

    @staticmethod
    def test_includes_pass_fail_badge(sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "FAIL" in html

    @staticmethod
    def test_pass_badge_for_clean_result(empty_result: PreflightResult) -> None:
        html = generate_html_report(empty_result).decode("utf-8")
        assert "PASS" in html

    @staticmethod
    def test_includes_finding_counts(sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        # Summary cards should contain the counts
        assert "LPDF_FONT_001" in html
        assert "LPDF_IMG_001" in html

    @staticmethod
    def test_includes_document_info(sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "1.7" in html  # PDF version

    @staticmethod
    def test_includes_profile_id(sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "lintpdf-default" in html

    @staticmethod
    def test_renders_epm_card_for_clean_result(empty_result: PreflightResult) -> None:
        """Even a clean job gets the EPM verdict header (PASS tier)."""
        html = generate_html_report(empty_result).decode("utf-8")
        assert "EPM:" in html
        assert "epm-card" in html

    @staticmethod
    def test_renders_ai_explain_css_in_template(
        sample_result: PreflightResult,
    ) -> None:
        """Template ships AI-Explain CSS so populated findings render
        the block when the service-render path stamps `ai_explanation`."""
        html = generate_html_report(sample_result).decode("utf-8")
        # CSS classes are present in every render so populated findings
        # have somewhere to land. Service-render path covers populated
        # text via the smoke test (PR 8).
        assert ".finding-ai-explain" in html
        assert ".ai-explain-label" in html

    @staticmethod
    def test_empty_result_shows_no_findings(empty_result: PreflightResult) -> None:
        html = generate_html_report(empty_result).decode("utf-8")
        assert "No findings detected" in html

    @staticmethod
    def test_output_is_utf8(sample_result: PreflightResult) -> None:
        report_bytes = generate_html_report(sample_result)
        assert isinstance(report_bytes, bytes)
        report_bytes.decode("utf-8")
