"""Tests for report generation engine."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from grounded.profiles.orchestrator import PreflightResult

from grounded.reports.engine import ReportEngine


class TestReportEngine:
    @staticmethod
    def test_supported_formats() -> None:
        assert "json" in ReportEngine.supported_formats()
        assert "html" in ReportEngine.supported_formats()
        assert "pdf" in ReportEngine.supported_formats()

    @staticmethod
    def test_generate_json(sample_result: PreflightResult) -> None:
        engine = ReportEngine()
        report = engine.generate(sample_result, "json")
        data = json.loads(report)
        assert data["job_id"] == "test-job-001"

    @staticmethod
    def test_generate_html(sample_result: PreflightResult) -> None:
        engine = ReportEngine()
        report = engine.generate(sample_result, "html")
        assert b"<!doctype html>" in report

    @staticmethod
    def test_generate_unsupported_format(sample_result: PreflightResult) -> None:
        engine = ReportEngine()
        with pytest.raises(ValueError, match="Unsupported report format"):
            engine.generate(sample_result, "csv")

    @staticmethod
    def test_to_json_directly(sample_result: PreflightResult) -> None:
        engine = ReportEngine()
        report = engine.to_json(sample_result)
        assert isinstance(report, bytes)
        json.loads(report)

    @staticmethod
    def test_to_html_directly(sample_result: PreflightResult) -> None:
        engine = ReportEngine()
        report = engine.to_html(sample_result)
        assert isinstance(report, bytes)
        assert b"<html" in report
