"""Tests for the ReportEngine format dispatch."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.profiles.orchestrator import PreflightResult, PreflightSummary
from lintpdf.reports.engine import ReportEngine


@pytest.fixture
def sample_result() -> PreflightResult:
    """Create a sample PreflightResult for testing."""
    findings = [
        Finding(
            inspection_id="LPDF_FONT_001",
            severity=Severity.ERROR,
            message="Font 'Arial' is not embedded",
            page_num=1,
            object_id="F1",
            object_type="font",
        ),
    ]
    summary = PreflightSummary(
        total_findings=1,
        error_count=1,
        warning_count=0,
        advisory_count=0,
        passed=False,
        page_count=2,
        file_size_bytes=1048576,
    )
    return PreflightResult(
        job_id="test-job-001",
        profile_id="lintpdf-default",
        findings=findings,
        summary=summary,
        metadata={"pdf_version": "1.7", "page_count": 2, "is_encrypted": False},
        duration_ms=42,
    )


@pytest.fixture
def empty_result() -> PreflightResult:
    """PreflightResult with no findings (passed)."""
    return PreflightResult(
        job_id="test-job-002",
        profile_id="lintpdf-default",
        findings=[],
        summary=PreflightSummary(
            total_findings=0,
            error_count=0,
            warning_count=0,
            advisory_count=0,
            passed=True,
            page_count=1,
            file_size_bytes=512000,
        ),
        metadata={"pdf_version": "1.4", "page_count": 1, "is_encrypted": False},
        duration_ms=10,
    )


@pytest.fixture
def engine() -> ReportEngine:
    return ReportEngine()


class TestSupportedFormats:
    """Tests for ReportEngine.supported_formats."""

    @staticmethod
    def test_returns_all_formats() -> None:
        formats = ReportEngine.supported_formats()
        assert "json" in formats
        assert "html" in formats
        assert "pdf" in formats
        assert "xml" in formats

    @staticmethod
    def test_returns_list() -> None:
        assert isinstance(ReportEngine.supported_formats(), list)


class TestGenerateDispatch:
    """Tests for ReportEngine.generate format routing."""

    @staticmethod
    def test_unsupported_format_raises(engine: ReportEngine, sample_result) -> None:
        with pytest.raises(ValueError, match="Unsupported report format: csv"):
            engine.generate(sample_result, "csv")

    @staticmethod
    def test_unsupported_format_empty_string(engine: ReportEngine, sample_result) -> None:
        with pytest.raises(ValueError, match="Unsupported report format"):
            engine.generate(sample_result, "")

    @staticmethod
    def test_dispatches_to_json(engine: ReportEngine, sample_result) -> None:
        with patch.object(engine, "to_json", return_value=b"{}") as mock:
            engine.generate(sample_result, "json")
            mock.assert_called_once_with(sample_result)

    @staticmethod
    def test_dispatches_to_html(engine: ReportEngine, sample_result) -> None:
        with patch.object(engine, "to_html", return_value=b"<html>") as mock:
            engine.generate(sample_result, "html")
            mock.assert_called_once_with(sample_result)

    @staticmethod
    def test_dispatches_to_pdf(engine: ReportEngine, sample_result) -> None:
        with patch.object(engine, "to_pdf", return_value=b"%PDF") as mock:
            engine.generate(sample_result, "pdf")
            mock.assert_called_once_with(sample_result)

    @staticmethod
    def test_dispatches_to_xml(engine: ReportEngine, sample_result) -> None:
        with patch.object(engine, "to_xml", return_value=b"<xml>") as mock:
            engine.generate(sample_result, "xml")
            mock.assert_called_once_with(sample_result)


class TestToJson:
    """Tests for JSON report generation via ReportEngine."""

    @staticmethod
    def test_returns_bytes(engine: ReportEngine, sample_result) -> None:
        result = engine.to_json(sample_result)
        assert isinstance(result, bytes)

    @staticmethod
    def test_valid_json(engine: ReportEngine, sample_result) -> None:
        import json

        result = engine.to_json(sample_result)
        data = json.loads(result)
        assert data["job_id"] == "test-job-001"
        assert data["profile_id"] == "lintpdf-default"
        assert data["summary"]["passed"] is False
        assert data["summary"]["total_findings"] == 1

    @staticmethod
    def test_empty_result_passes(engine: ReportEngine, empty_result) -> None:
        import json

        result = engine.to_json(empty_result)
        data = json.loads(result)
        assert data["summary"]["passed"] is True
        assert data["findings"] == []

    @staticmethod
    def test_findings_serialized(engine: ReportEngine, sample_result) -> None:
        import json

        result = engine.to_json(sample_result)
        data = json.loads(result)
        assert len(data["findings"]) == 1
        finding = data["findings"][0]
        assert finding["inspection_id"] == "LPDF_FONT_001"
        assert finding["severity"] == "error"
        assert finding["page_num"] == 1


class TestToXml:
    """Tests for XML report generation via ReportEngine."""

    @staticmethod
    def test_returns_bytes(engine: ReportEngine, sample_result) -> None:
        result = engine.to_xml(sample_result)
        assert isinstance(result, bytes)

    @staticmethod
    def test_valid_xml(engine: ReportEngine, sample_result) -> None:
        result = engine.to_xml(sample_result)
        xml_str = result.decode("utf-8")
        assert xml_str.startswith('<?xml version="1.0"')
        assert "<PreflightReport" in xml_str


class TestToHtml:
    """Tests for HTML report generation via ReportEngine."""

    @staticmethod
    def test_delegates_to_html_report(engine: ReportEngine, sample_result) -> None:
        with patch(
            "lintpdf.reports.html_report.generate_html_report", return_value=b"<html>test</html>"
        ) as mock:
            result = engine.to_html(sample_result)
            mock.assert_called_once_with(sample_result)
            assert result == b"<html>test</html>"


class TestToPdf:
    """Tests for PDF report generation via ReportEngine (WeasyPrint mocked)."""

    @staticmethod
    def test_delegates_to_pdf_report(engine: ReportEngine, sample_result) -> None:
        with patch(
            "lintpdf.reports.pdf_report.generate_pdf_report", return_value=b"%PDF-mock"
        ) as mock:
            result = engine.to_pdf(sample_result)
            mock.assert_called_once_with(sample_result)
            assert result == b"%PDF-mock"
