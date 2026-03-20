"""JSON report generation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from grounded.profiles.orchestrator import PreflightResult


def generate_json_report(result: PreflightResult) -> bytes:
    """Generate a structured JSON report from preflight results.

    Args:
        result: Preflight result to serialize.

    Returns:
        UTF-8 encoded JSON bytes.
    """
    report: dict[str, Any] = {
        "job_id": result.job_id,
        "profile_id": result.profile_id,
        "summary": {
            "passed": result.summary.passed,
            "total_findings": result.summary.total_findings,
            "aground_count": result.summary.aground_count,
            "squall_count": result.summary.squall_count,
            "advisory_count": result.summary.advisory_count,
            "page_count": result.summary.page_count,
            "file_size_bytes": result.summary.file_size_bytes,
        },
        "document": {
            "pdf_version": result.metadata.get("pdf_version", ""),
            "page_count": result.metadata.get("page_count", 0),
            "is_encrypted": result.metadata.get("is_encrypted", False),
        },
        "findings": [
            {
                "inspection_id": f.inspection_id,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "message": f.message,
                "page_num": f.page_num,
                "object_id": f.object_id,
                "object_type": f.object_type,
                "iso_clause": f.iso_clause,
                "details": f.details,
                "source": getattr(f, "source", "engine"),
                "category": getattr(f, "category", None),
            }
            for f in result.findings
        ],
        "metadata": result.metadata,
        "duration_ms": result.duration_ms,
    }

    return json.dumps(report, indent=2, default=str).encode("utf-8")
