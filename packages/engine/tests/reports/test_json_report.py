"""Tests for JSON report generation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lintpdf.profiles.orchestrator import PreflightResult

from lintpdf.reports.json_report import generate_json_from_dict, generate_json_report


class TestJsonReport:
    @staticmethod
    def test_generates_valid_json(sample_result: PreflightResult) -> None:
        report_bytes = generate_json_report(sample_result)
        data = json.loads(report_bytes)
        assert isinstance(data, dict)

    @staticmethod
    def test_includes_job_id(sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert data["job_id"] == "test-job-001"

    @staticmethod
    def test_includes_profile_id(sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert data["profile_id"] == "lintpdf-default"

    @staticmethod
    def test_includes_summary(sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        summary = data["summary"]
        assert summary["passed"] is False
        assert summary["total_findings"] == 3
        assert summary["error_count"] == 1
        assert summary["warning_count"] == 1
        assert summary["advisory_count"] == 1

    @staticmethod
    def test_includes_findings(sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert len(data["findings"]) == 3
        first = data["findings"][0]
        assert first["inspection_id"] == "LPDF_FONT_001"
        assert first["severity"] == "error"
        assert "not embedded" in first["message"]

    @staticmethod
    def test_includes_document_info(sample_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(sample_result))
        assert data["document"]["pdf_version"] == "1.7"
        assert data["document"]["page_count"] == 2

    @staticmethod
    def test_empty_result(empty_result: PreflightResult) -> None:
        data = json.loads(generate_json_report(empty_result))
        assert data["summary"]["passed"] is True
        assert len(data["findings"]) == 0

    @staticmethod
    def test_output_is_utf8(sample_result: PreflightResult) -> None:
        report_bytes = generate_json_report(sample_result)
        assert isinstance(report_bytes, bytes)
        report_bytes.decode("utf-8")  # Should not raise


class TestJsonFromDict:
    """Tests for the dict-based renderer used by the report mint service."""

    @staticmethod
    def _sample_dict() -> dict[str, object]:
        return {
            "job_id": "abc-123",
            "profile_id": "lintpdf-default",
            "duration_ms": 4321,
            "preflight_source": "engine",
            "summary": {
                "passed": False,
                "total_findings": 2,
                "error_count": 1,
                "warning_count": 1,
                "advisory_count": 0,
                "page_count": 3,
                "file_size_bytes": 9999,
            },
            "metadata": {
                "pdf_version": "1.7",
                "page_count": 3,
                "is_encrypted": False,
                "conformance": "PDF/X-4",
            },
            "findings": [
                {
                    "inspection_id": "LPDF_FONT_001",
                    "severity": "error",
                    "message": "Font not embedded",
                    "page_num": 1,
                    "object_id": "F1",
                    "object_type": "font",
                    "iso_clause": "ISO 32000-2:2020 9.6",
                    "category": "fonts",
                    "source": "engine",
                    "bbox": [10.0, 20.0, 30.0, 40.0],
                    "details": {"font_name": "Arial"},
                },
                {
                    "inspection_id": "LPDF_IMG_001",
                    "severity": "warning",
                    "message": "Image below 150 DPI",
                    "page_num": 2,
                },
            ],
        }

    def test_dict_input_roundtrips(self) -> None:
        data = json.loads(generate_json_from_dict(self._sample_dict()))
        assert data["schema_version"] == "1"
        assert data["job_id"] == "abc-123"
        assert data["profile_id"] == "lintpdf-default"
        assert data["preflight_source"] == "engine"
        assert data["summary"]["error_count"] == 1
        assert data["document"]["pdf_version"] == "1.7"
        assert data["document"]["conformance"] == "PDF/X-4"
        assert len(data["findings"]) == 2
        assert data["findings"][0]["bbox"] == [10.0, 20.0, 30.0, 40.0]
        assert data["findings"][0]["details"]["font_name"] == "Arial"

    def test_dict_input_tolerates_missing_keys(self) -> None:
        data = json.loads(generate_json_from_dict({"job_id": "x"}))
        assert data["job_id"] == "x"
        assert data["findings"] == []
        assert data["summary"]["error_count"] == 0
        assert data["document"]["pdf_version"] == ""

    def test_dict_input_skips_non_dict_findings(self) -> None:
        data = json.loads(
            generate_json_from_dict(
                {
                    "job_id": "x",
                    "findings": [{"inspection_id": "a", "severity": "error"}, "junk", None],
                }
            )
        )
        assert len(data["findings"]) == 1
        assert data["findings"][0]["inspection_id"] == "a"
