"""Pixie Dust integration - webhook payload formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lintpdf.api.middleware import UsageInfo
    from lintpdf.profiles.orchestrator import PreflightResult


def format_pixie_dust_payload(
    result: PreflightResult,
    usage: UsageInfo | None = None,
    report_urls: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Format a PreflightResult as a Pixie Dust-compatible webhook payload.

    Pixie Dust expects a specific JSON structure for displaying
    preflight results in its UI.

    Args:
        result: Preflight result to format.
        usage: Optional current usage info to include.

    Returns:
        Dict formatted for Pixie Dust webhook consumption.
    """
    # Group findings by severity for summary
    findings_by_severity: dict[str, list[dict[str, Any]]] = {
        "error": [],
        "warning": [],
        "advisory": [],
    }

    for f in result.findings:
        severity_key = (
            f.severity.value.replace("-", "_")
            if hasattr(f.severity, "value")
            else str(f.severity).replace("-", "_")
        )
        if severity_key in findings_by_severity:
            findings_by_severity[severity_key].append(
                {
                    "check_id": f.inspection_id,
                    "message": f.message,
                    "page": f.page_num,
                    "object": f.object_id,
                }
            )

    payload: dict[str, Any] = {
        "event": "preflight.complete",
        "job_id": result.job_id,
        "profile_id": result.profile_id,
        "passed": result.summary.passed,
        "badge": "pass" if result.summary.passed else "fail",
        "summary": {
            "total": result.summary.total_findings,
            "error": result.summary.error_count,
            "warning": result.summary.warning_count,
            "advisory": result.summary.advisory_count,
            "pages": result.summary.page_count,
            "file_size_bytes": result.summary.file_size_bytes,
        },
        "document": {
            "pdf_version": result.metadata.get("pdf_version", ""),
            "encrypted": result.metadata.get("is_encrypted", False),
            "conformance": result.metadata.get("conformance"),
        },
        "findings": findings_by_severity,
        "duration_ms": result.duration_ms,
    }

    if usage is not None:
        payload["usage"] = format_usage_section(usage)

    if report_urls is not None:
        payload["report"] = report_urls

    return payload


def format_usage_event(
    event_type: str,
    tenant_id: str,
    usage: UsageInfo,
) -> dict[str, Any]:
    """Format a usage event payload (warning, overage, cap_reached, blocked).

    Args:
        event_type: One of "usage.warning", "usage.overage", "usage.cap_reached", "usage.blocked".
        tenant_id: Tenant ID.
        usage: Current usage info.

    Returns:
        Dict for webhook dispatch.
    """
    return {
        "event": event_type,
        "tenant_id": tenant_id,
        **format_usage_section(usage),
    }


def format_usage_section(usage: UsageInfo) -> dict[str, Any]:
    """Format a UsageInfo into a Pixie Dust usage section.

    Args:
        usage: Current usage info.

    Returns:
        Dict with usage metrics for the dashboard.
    """
    return {
        "used": usage.used,
        "limit": usage.limit,
        "remaining_included": usage.remaining_included,
        "percentage": usage.percentage,
        "in_overage": usage.in_overage,
        "overage_count": usage.overage_count,
        "overage_rate_cents": usage.overage_rate_cents,
        "overage_cost_cents": usage.overage_cost_cents,
        "overage_enabled": usage.overage_enabled,
        "overage_cap_cents": usage.overage_cap_cents,
        "cap_remaining_cents": usage.cap_remaining_cents,
        "blocked": usage.blocked,
        "warning": usage.warning,
    }


def format_pixie_dust_error(
    job_id: str,
    error: str,
    usage: UsageInfo | None = None,
) -> dict[str, Any]:
    """Format a job failure as a Pixie Dust-compatible error payload.

    Args:
        job_id: The failed job's ID.
        error: Error message.
        usage: Optional current usage info to include.

    Returns:
        Dict formatted for Pixie Dust error webhook.
    """
    payload: dict[str, Any] = {
        "event": "preflight.failed",
        "job_id": job_id,
        "passed": False,
        "badge": "error",
        "error": error,
    }

    if usage is not None:
        payload["usage"] = format_usage_section(usage)

    return payload
