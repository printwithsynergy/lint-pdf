"""Shared fixtures for report tests."""

from __future__ import annotations

import pytest

from grounded.analyzers.finding import Finding, Severity
from grounded.profiles.orchestrator import PreflightResult, PreflightSummary


@pytest.fixture
def sample_result() -> PreflightResult:
    """Create a sample PreflightResult for testing."""
    findings = [
        Finding(
            inspection_id="GRD_FONT_001",
            severity=Severity.ERROR,
            message="Font 'Arial' is not embedded",
            page_num=1,
            object_id="F1",
            object_type="font",
        ),
        Finding(
            inspection_id="GRD_IMG_001",
            severity=Severity.WARNING,
            message="Image resolution below minimum (72 DPI < 150 DPI)",
            page_num=1,
            object_id="Im1",
            object_type="image",
        ),
        Finding(
            inspection_id="GRD_COLOR_003",
            severity=Severity.ADVISORY,
            message="RGB color space detected",
            page_num=2,
            object_type="color",
        ),
    ]

    summary = PreflightSummary(
        total_findings=3,
        error_count=1,
        warning_count=1,
        advisory_count=1,
        passed=False,
        page_count=2,
        file_size_bytes=1048576,
    )

    return PreflightResult(
        job_id="test-job-001",
        profile_id="lintpdf-default",
        findings=findings,
        summary=summary,
        metadata={
            "pdf_version": "1.7",
            "page_count": 2,
            "is_encrypted": False,
            "conformance": None,
            "workflow": "CMYK",
        },
        duration_ms=42,
    )


@pytest.fixture
def empty_result() -> PreflightResult:
    """Create a PreflightResult with no findings."""
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
        metadata={
            "pdf_version": "1.4",
            "page_count": 1,
            "is_encrypted": False,
            "conformance": None,
            "workflow": "CMYK",
        },
        duration_ms=10,
    )
