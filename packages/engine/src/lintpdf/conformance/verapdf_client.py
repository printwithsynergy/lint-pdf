"""Optional veraPDF REST API client for enhanced PDF/A validation.

When ``LINTPDF_VERAPDF_URL`` is configured, the orchestrator calls
``validate_with_verapdf()`` after running the built-in conformance
checks. Results are merged into the findings list.

If veraPDF is unreachable (sleeping, restarting, or not deployed),
the call is skipped with a warning — it never blocks preflight.
"""

from __future__ import annotations

import io
import logging
from typing import Any

logger = logging.getLogger(__name__)

# veraPDF REST endpoints:
#   GET  /api/info       — service info (used as healthcheck)
#   POST /api/validate   — validate a PDF (multipart/form-data)

_TIMEOUT = 30  # seconds — enough for veraPDF to wake from Railway sleep


def is_verapdf_configured() -> bool:
    """Return True if veraPDF URL is configured."""
    try:
        from lintpdf.api.config import get_settings

        url = get_settings().verapdf_url
        return bool(url and url != "http://localhost:8080")
    except Exception:
        return False


def validate_with_verapdf(
    pdf_bytes: bytes,
    *,
    profile: str = "PDFA_1_B",
) -> list[dict[str, Any]]:
    """Send a PDF to veraPDF for validation and return findings.

    Args:
        pdf_bytes: Raw PDF bytes.
        profile: veraPDF validation profile. Common values:
            PDFA_1_B, PDFA_2_B, PDFA_3_B, PDFUA_1

    Returns:
        List of finding dicts compatible with the engine's Finding format.
        Empty list if veraPDF is unreachable or returns no issues.
    """
    try:
        from lintpdf.api.config import get_settings

        base_url = get_settings().verapdf_url.rstrip("/")
        if not base_url:
            return []
    except Exception:
        return []

    import httpx

    try:
        # Wake check — hit /api/info first (Railway healthcheck endpoint)
        with httpx.Client(timeout=_TIMEOUT) as client:
            info_resp = client.get(f"{base_url}/api/info")
            if info_resp.status_code != 200:
                logger.warning(
                    "veraPDF /api/info returned %d — skipping validation",
                    info_resp.status_code,
                )
                return []

            # Submit PDF for validation
            files = {"file": ("input.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            data = {"profile": profile}
            resp = client.post(f"{base_url}/api/validate", files=files, data=data)

            if resp.status_code != 200:
                logger.warning(
                    "veraPDF validation returned %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []

            return _parse_verapdf_response(resp.json())

    except httpx.TimeoutException:
        logger.info("veraPDF timed out (may be waking from sleep) — skipping")
        return []
    except httpx.ConnectError:
        logger.info("veraPDF unreachable — skipping validation")
        return []
    except Exception:
        logger.exception("veraPDF validation failed unexpectedly")
        return []


def _parse_verapdf_response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert veraPDF REST response to engine-compatible findings.

    veraPDF returns a nested structure with test assertions grouped by
    rule. We flatten these into individual findings.
    """
    findings: list[dict[str, Any]] = []

    # veraPDF response structure varies by version. Common shapes:
    # - { "report": { "jobs": [{ "validationResult": { ... } }] } }
    # - { "validationResult": { ... } }

    result = data
    if "report" in data:
        jobs = data["report"].get("jobs", [])
        if jobs:
            result = jobs[0]

    validation = result.get("validationResult", {})
    if not validation:
        return findings

    is_compliant = validation.get("compliant", True)
    profile_name = validation.get("profileName", "PDF/A")

    # Each failed rule becomes a finding
    rules = validation.get("details", {}).get("failedRules", [])
    if not rules:
        rules = validation.get("ruleSummaries", [])

    for rule in rules:
        clause = rule.get("clause", "")
        test_number = rule.get("testNumber", "")
        description = rule.get("description", "")
        failed_checks = rule.get("failedChecks", rule.get("checks", 0))

        if isinstance(failed_checks, list):
            check_count = len(failed_checks)
        else:
            check_count = int(failed_checks) if failed_checks else 0

        if check_count == 0:
            continue

        # Build a finding
        finding_id = f"VERA_{clause.replace('.', '_')}_{test_number}"
        findings.append({
            "inspection_id": finding_id,
            "severity": "error",
            "message": description or f"{profile_name} rule {clause}-{test_number} failed ({check_count} occurrence(s))",
            "page_num": 0,  # veraPDF doesn't always give page-level detail
            "source": "verapdf",
            "category": "conformance",
            "details": {
                "clause": clause,
                "test_number": test_number,
                "profile": profile_name,
                "failed_checks": check_count,
                "validator": "veraPDF",
            },
        })

    # Add a summary finding if non-compliant
    if not is_compliant and not findings:
        findings.append({
            "inspection_id": "VERA_NONCOMPLIANT",
            "severity": "error",
            "message": f"Document is not {profile_name} compliant (veraPDF)",
            "page_num": 0,
            "source": "verapdf",
            "category": "conformance",
            "details": {"profile": profile_name, "validator": "veraPDF"},
        })

    return findings
