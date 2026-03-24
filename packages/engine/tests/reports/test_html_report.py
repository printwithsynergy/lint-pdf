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
        assert "GRD_FONT_001" in html
        assert "GRD_IMG_001" in html

    @staticmethod
    def test_includes_document_info(sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "1.7" in html  # PDF version

    @staticmethod
    def test_includes_profile_id(sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "lintpdf-default" in html

    @staticmethod
    def test_empty_result_shows_no_findings(empty_result: PreflightResult) -> None:
        html = generate_html_report(empty_result).decode("utf-8")
        assert "No findings detected" in html

    @staticmethod
    def test_output_is_utf8(sample_result: PreflightResult) -> None:
        report_bytes = generate_html_report(sample_result)
        assert isinstance(report_bytes, bytes)
        report_bytes.decode("utf-8")
