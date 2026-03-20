"""Tests for HTML report generation."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grounded.profiles.orchestrator import PreflightResult

from grounded.reports.html_report import generate_html_report


class TestHtmlReport:
    def test_generates_html(self, sample_result: PreflightResult) -> None:
        report_bytes = generate_html_report(sample_result)
        html = report_bytes.decode("utf-8")
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_includes_pass_fail_badge(self, sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "FAIL" in html

    def test_pass_badge_for_clean_result(self, empty_result: PreflightResult) -> None:
        html = generate_html_report(empty_result).decode("utf-8")
        assert "PASS" in html

    def test_includes_finding_counts(self, sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        # Summary cards should contain the counts
        assert "GRD_FONT_001" in html
        assert "GRD_IMG_001" in html

    def test_includes_document_info(self, sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "1.7" in html  # PDF version

    def test_includes_profile_id(self, sample_result: PreflightResult) -> None:
        html = generate_html_report(sample_result).decode("utf-8")
        assert "grounded-default" in html

    def test_empty_result_shows_no_findings(self, empty_result: PreflightResult) -> None:
        html = generate_html_report(empty_result).decode("utf-8")
        assert "No findings detected" in html

    def test_output_is_utf8(self, sample_result: PreflightResult) -> None:
        report_bytes = generate_html_report(sample_result)
        assert isinstance(report_bytes, bytes)
        report_bytes.decode("utf-8")
