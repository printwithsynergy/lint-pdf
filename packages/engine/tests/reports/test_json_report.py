"""Tests for JSON report generation."""

from __future__ import annotations

# skipcq: PYL-R0201
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grounded.profiles.orchestrator import PreflightResult

from grounded.reports.json_report import generate_json_report


class TestJsonReport:
    def test_generates_valid_json(self, sample_result: PreflightResult) -> None:
        report_bytes = generate_json_report(sample_result)
        data = json.loads(report_bytes)
        assert isinstance(data, dict)

    def test_includes_job_id(self, sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert data["job_id"] == "test-job-001"

    def test_includes_profile_id(self, sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert data["profile_id"] == "grounded-default"

    def test_includes_summary(self, sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        summary = data["summary"]
        assert summary["passed"] is False
        assert summary["total_findings"] == 3
        assert summary["aground_count"] == 1
        assert summary["squall_count"] == 1
        assert summary["advisory_count"] == 1

    def test_includes_findings(self, sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert len(data["findings"]) == 3
        first = data["findings"][0]
        assert first["inspection_id"] == "GRD_FONT_001"
        assert first["severity"] == "aground"
        assert "not embedded" in first["message"]

    def test_includes_document_info(self, sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert data["document"]["pdf_version"] == "1.7"
        assert data["document"]["page_count"] == 2

    def test_empty_result(self, empty_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(empty_result))
        assert data["summary"]["passed"] is True
        assert len(data["findings"]) == 0

    def test_output_is_utf8(self, sample_result: PreflightResult) -> None:
        report_bytes = generate_json_report(sample_result)
        assert isinstance(report_bytes, bytes)
        report_bytes.decode("utf-8")  # Should not raise
