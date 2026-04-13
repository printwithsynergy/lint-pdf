"""JSON report generation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lintpdf.profiles.orchestrator import PreflightResult


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
            "error_count": result.summary.error_count,
            "warning_count": result.summary.warning_count,
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


def generate_json_from_dict(result_json: dict[str, Any]) -> bytes:
    """Generate a structured JSON report from a result_json dict.

    This is the entry point used by the report mint service, which
    operates on the persisted ``Job.result_json`` payload (already a dict)
    plus the per-finding rows joined in from the ``job_findings`` table.
    The shape is intentionally compatible with the LintPDF v1 import
    schema so the same JSON can be re-imported via
    ``preflight_source=external``, ``external_format=lintpdf_json``.

    Args:
        result_json: Job result dict with at minimum ``job_id``, ``profile_id``,
            ``summary``, ``metadata``, and ``findings`` keys.

    Returns:
        UTF-8 encoded JSON bytes (pretty-printed, indent=2).
    """
    summary = result_json.get("summary", {}) or {}
    metadata = result_json.get("metadata", {}) or {}
    findings_raw = result_json.get("findings", []) or []

    findings: list[dict[str, Any]] = []
    for f in findings_raw:
        if not isinstance(f, dict):
            continue
        findings.append(
            {
                "inspection_id": f.get("inspection_id"),
                "severity": f.get("severity"),
                "message": f.get("message"),
                "page_num": f.get("page_num"),
                "object_id": f.get("object_id"),
                "object_type": f.get("object_type"),
                "iso_clause": f.get("iso_clause"),
                "category": f.get("category"),
                "source": f.get("source") or "engine",
                "bbox": f.get("bbox"),
                "details": f.get("details"),
            }
        )

    report: dict[str, Any] = {
        "schema_version": "1",
        "job_id": result_json.get("job_id"),
        "profile_id": result_json.get("profile_id"),
        "preflight_source": result_json.get("preflight_source", "engine"),
        "external_format": result_json.get("external_format"),
        "summary": {
            "passed": summary.get("passed"),
            "total_findings": summary.get("total_findings", len(findings)),
            "error_count": summary.get("error_count", 0),
            "warning_count": summary.get("warning_count", 0),
            "advisory_count": summary.get("advisory_count", 0),
            "page_count": summary.get("page_count", metadata.get("page_count", 0)),
            "file_size_bytes": summary.get("file_size_bytes", 0),
        },
        "document": {
            "pdf_version": metadata.get("pdf_version", ""),
            "page_count": metadata.get("page_count", 0),
            "is_encrypted": metadata.get("is_encrypted", False),
            "conformance": metadata.get("conformance"),
        },
        "findings": findings,
        "metadata": metadata,
        "duration_ms": result_json.get("duration_ms"),
    }

    return json.dumps(report, indent=2, default=str).encode("utf-8")
