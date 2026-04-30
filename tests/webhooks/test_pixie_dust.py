"""Tests for Pixie Dust webhook payload formatting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from lintpdf.webhooks.pixie_dust import (
    format_pixie_dust_error,
    format_pixie_dust_payload,
    format_usage_section,
)


class _Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    ADVISORY = "advisory"


@dataclass
class _Finding:
    inspection_id: str = "LPDF_TEST_001"
    severity: _Severity = _Severity.ADVISORY
    message: str = "Test finding"
    page_num: int = 1
    object_id: str = ""
    object_type: str = ""


@dataclass
class _Summary:
    total_findings: int = 0
    error_count: int = 0
    warning_count: int = 0
    advisory_count: int = 0
    passed: bool = True
    page_count: int = 1
    file_size_bytes: int = 1024


@dataclass
class _PreflightResult:
    job_id: str = "job-123"
    profile_id: str = "lintpdf-default"
    findings: list[Any] = field(default_factory=list)
    summary: _Summary = field(default_factory=_Summary)
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 500


@dataclass
class _UsageInfo:
    used: int = 50
    limit: int = 100
    percentage: int = 50
    in_overage: bool = False
    overage_count: int = 0
    overage_rate_cents: int = 10
    overage_cost_cents: int = 0
    overage_enabled: bool = True
    overage_cap_cents: int | None = None
    blocked: bool = False

    @property
    def remaining_included(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def cap_remaining_cents(self) -> int | None:
        if self.overage_cap_cents is None:
            return None
        return max(0, self.overage_cap_cents - self.overage_cost_cents)

    @property
    def warning(self) -> bool:
        return self.percentage >= 80 and not self.blocked


class TestFormatPixieDustPayload:
    """Tests for format_pixie_dust_payload."""

    @staticmethod
    def test_basic_structure() -> None:
        result = _PreflightResult()
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        assert payload["event"] == "preflight.complete"
        assert payload["job_id"] == "job-123"
        assert payload["profile_id"] == "lintpdf-default"
        assert payload["passed"] is True
        assert payload["badge"] == "pass"
        assert payload["duration_ms"] == 500

    @staticmethod
    def test_pass_badge() -> None:
        result = _PreflightResult(summary=_Summary(passed=True))
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]
        assert payload["badge"] == "pass"

    @staticmethod
    def test_fail_badge() -> None:
        result = _PreflightResult(summary=_Summary(passed=False))
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]
        assert payload["badge"] == "fail"
        assert payload["passed"] is False

    @staticmethod
    def test_summary_section() -> None:
        result = _PreflightResult(
            summary=_Summary(
                total_findings=10,
                error_count=2,
                warning_count=3,
                advisory_count=5,
                page_count=4,
                file_size_bytes=2048,
            )
        )
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        assert payload["summary"]["total"] == 10
        assert payload["summary"]["error"] == 2
        assert payload["summary"]["warning"] == 3
        assert payload["summary"]["advisory"] == 5
        assert payload["summary"]["pages"] == 4
        assert payload["summary"]["file_size_bytes"] == 2048

    @staticmethod
    def test_document_section() -> None:
        result = _PreflightResult(
            metadata={
                "pdf_version": "1.7",
                "is_encrypted": False,
                "conformance": "PDF/X-4",
            }
        )
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        assert payload["document"]["pdf_version"] == "1.7"
        assert payload["document"]["encrypted"] is False
        assert payload["document"]["conformance"] == "PDF/X-4"

    @staticmethod
    def test_document_section_missing_metadata() -> None:
        result = _PreflightResult(metadata={})
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        assert payload["document"]["pdf_version"] == ""
        assert payload["document"]["encrypted"] is False
        assert payload["document"]["conformance"] is None

    @staticmethod
    def test_findings_grouped_by_severity() -> None:
        findings = [
            _Finding(
                inspection_id="LPDF_FONT_001",
                severity=_Severity.ERROR,
                message="Font not embedded",
                page_num=1,
            ),
            _Finding(
                inspection_id="LPDF_IMG_001",
                severity=_Severity.WARNING,
                message="Low resolution",
                page_num=2,
            ),
            _Finding(
                inspection_id="LPDF_COLOR_001",
                severity=_Severity.ADVISORY,
                message="RGB detected",
                page_num=1,
            ),
        ]
        result = _PreflightResult(findings=findings)
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        assert len(payload["findings"]["error"]) == 1
        assert len(payload["findings"]["warning"]) == 1
        assert len(payload["findings"]["advisory"]) == 1

    @staticmethod
    def test_finding_structure() -> None:
        findings = [
            _Finding(
                inspection_id="LPDF_FONT_001",
                severity=_Severity.ERROR,
                message="Font not embedded",
                page_num=3,
                object_id="F1",
            ),
        ]
        result = _PreflightResult(findings=findings)
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        finding = payload["findings"]["error"][0]
        assert finding["check_id"] == "LPDF_FONT_001"
        assert finding["message"] == "Font not embedded"
        assert finding["page"] == 3
        assert finding["object"] == "F1"

    @staticmethod
    def test_empty_findings() -> None:
        result = _PreflightResult(findings=[])
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        assert payload["findings"]["error"] == []
        assert payload["findings"]["warning"] == []
        assert payload["findings"]["advisory"] == []

    @staticmethod
    def test_multiple_findings_same_severity() -> None:
        findings = [
            _Finding(severity=_Severity.ADVISORY, inspection_id="LPDF_A"),
            _Finding(severity=_Severity.ADVISORY, inspection_id="LPDF_B"),
            _Finding(severity=_Severity.ADVISORY, inspection_id="LPDF_C"),
        ]
        result = _PreflightResult(findings=findings)
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]

        assert len(payload["findings"]["advisory"]) == 3

    @staticmethod
    def test_no_usage_by_default() -> None:
        result = _PreflightResult()
        payload = format_pixie_dust_payload(result)  # type: ignore[arg-type]
        assert "usage" not in payload

    @staticmethod
    def test_usage_included_when_provided() -> None:
        result = _PreflightResult()
        usage = _UsageInfo(used=50, limit=100)
        payload = format_pixie_dust_payload(result, usage=usage)  # type: ignore[arg-type]

        assert "usage" in payload
        assert payload["usage"]["used"] == 50
        assert payload["usage"]["limit"] == 100
        assert payload["usage"]["remaining_included"] == 50
        assert payload["usage"]["percentage"] == 50
        assert payload["usage"]["in_overage"] is False
        assert payload["usage"]["overage_count"] == 0
        assert payload["usage"]["overage_cost_cents"] == 0

    @staticmethod
    def test_usage_in_overage() -> None:
        result = _PreflightResult()
        usage = _UsageInfo(
            used=105,
            limit=100,
            percentage=105,
            in_overage=True,
            overage_count=5,
            overage_cost_cents=50,
        )
        payload = format_pixie_dust_payload(result, usage=usage)  # type: ignore[arg-type]

        assert payload["usage"]["in_overage"] is True
        assert payload["usage"]["remaining_included"] == 0
        assert payload["usage"]["overage_count"] == 5
        assert payload["usage"]["overage_cost_cents"] == 50

    @staticmethod
    def test_usage_with_cap() -> None:
        result = _PreflightResult()
        usage = _UsageInfo(
            used=105,
            limit=100,
            percentage=105,
            in_overage=True,
            overage_count=5,
            overage_cost_cents=50,
            overage_cap_cents=200,
        )
        payload = format_pixie_dust_payload(result, usage=usage)  # type: ignore[arg-type]
        assert payload["usage"]["overage_cap_cents"] == 200
        assert payload["usage"]["cap_remaining_cents"] == 150


class TestFormatPixieDustError:
    """Tests for format_pixie_dust_error."""

    @staticmethod
    def test_basic_structure() -> None:
        payload = format_pixie_dust_error("job-456", "File corrupt")

        assert payload["event"] == "preflight.failed"
        assert payload["job_id"] == "job-456"
        assert payload["passed"] is False
        assert payload["badge"] == "error"
        assert payload["error"] == "File corrupt"

    @staticmethod
    def test_error_message_preserved() -> None:
        msg = "PDF parsing failed: unexpected EOF at byte 12345"
        payload = format_pixie_dust_error("j1", msg)
        assert payload["error"] == msg

    @staticmethod
    def test_empty_error_message() -> None:
        payload = format_pixie_dust_error("j1", "")
        assert payload["error"] == ""

    @staticmethod
    def test_no_usage_by_default() -> None:
        payload = format_pixie_dust_error("j1", "err")
        assert "usage" not in payload

    @staticmethod
    def test_usage_included_when_provided() -> None:
        usage = _UsageInfo(used=95, limit=100, percentage=95)
        payload = format_pixie_dust_error("j1", "err", usage=usage)  # type: ignore[arg-type]
        assert "usage" in payload
        assert payload["usage"]["used"] == 95
        assert payload["usage"]["warning"] is True


class TestFormatUsageSection:
    """Tests for format_usage_section."""

    @staticmethod
    def test_basic() -> None:
        usage = _UsageInfo()
        section = format_usage_section(usage)  # type: ignore[arg-type]
        assert section["used"] == 50
        assert section["limit"] == 100
        assert section["remaining_included"] == 50
        assert section["percentage"] == 50
        assert section["in_overage"] is False
        assert section["blocked"] is False
        assert section["warning"] is False
        assert section["overage_count"] == 0
        assert section["overage_rate_cents"] == 10
        assert section["overage_cost_cents"] == 0

    @staticmethod
    def test_warning_state() -> None:
        usage = _UsageInfo(used=85, percentage=85)
        section = format_usage_section(usage)  # type: ignore[arg-type]
        assert section["warning"] is True

    @staticmethod
    def test_overage_fields() -> None:
        usage = _UsageInfo(
            used=110,
            limit=100,
            percentage=110,
            in_overage=True,
            overage_count=10,
            overage_cost_cents=100,
            overage_cap_cents=500,
        )
        section = format_usage_section(usage)  # type: ignore[arg-type]
        assert section["overage_count"] == 10
        assert section["overage_cost_cents"] == 100
        assert section["overage_cap_cents"] == 500
        assert section["cap_remaining_cents"] == 400
