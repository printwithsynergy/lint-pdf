"""veraPDF-backed conformance findings for PDF/X, PDF/A, PDF/UA.

One entry point (``run_verapdf_checks``) that the orchestrator calls
once per preflight run. It decides which veraPDF flavours to invoke
based on the active profile's ``conformance`` string and any enabled
PDF/UA checks, runs veraPDF per flavour (cached), and emits up to
three stable findings:

- ``LPDF_PDFX_CONF`` (T1-CMP01) — PDF/X-1a..X-6 conformance
- ``LPDF_PDFA_CONF`` (T4-A02) — PDF/A-1b..4 conformance
- ``LPDF_UA_CONF``   (T4-A01) — PDF/UA-1 Matterhorn

Each finding carries the failure list in ``details`` so tenants see
the exact veraPDF clauses + messages without a second round-trip.
"""

from __future__ import annotations

import logging
from typing import Any

from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.conformance.verapdf_client import is_verapdf_configured, validate_with_verapdf

logger = logging.getLogger(__name__)

__all__ = ["run_verapdf_checks"]


# Conformance-string → veraPDF profile mapping. Keep in sync with
# PreflightProfile.conformance enum and veraPDF's supported profiles.
_CONF_TO_VERAPDF_PDFX: dict[str, str] = {
    "pdfx1a": "PDFX_1A",
    "pdfx1a2003": "PDFX_1A",
    "pdfx3": "PDFX_3",
    "pdfx32003": "PDFX_3",
    "pdfx4": "PDFX_4",
    "pdfx4p": "PDFX_4P",
    "pdfx5": "PDFX_5",
    "pdfx6": "PDFX_4",  # X-6 builds on X-4 per ISO 15930-9; use X-4 as best-effort
}

_CONF_TO_VERAPDF_PDFA: dict[str, str] = {
    "pdfa1b": "PDFA_1_B",
    "pdfa2b": "PDFA_2_B",
    "pdfa3b": "PDFA_3_B",
    "pdfa2u": "PDFA_2_U",
    "pdfa3u": "PDFA_3_U",
    "pdfa4": "PDFA_4",
}


def _summarise_failures(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip the raw veraPDF per-rule findings down to a stable summary list.

    Returns ``[{clause, test_number, description, failed_checks}, ...]``.
    Dedups by (clause, test_number) and caps at 25 entries so one
    finding stays human-readable in the rules editor / report.
    """
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for entry in raw:
        details = entry.get("details", {}) or {}
        clause = str(details.get("clause", ""))
        test_number = str(details.get("test_number", ""))
        key = (clause, test_number)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "clause": clause,
                "test_number": test_number,
                "description": entry.get("message", "")[:160],
                "failed_checks": details.get("failed_checks", 0),
            }
        )
        if len(out) >= 25:
            break
    return out


def _run_flavour(
    pdf_bytes: bytes,
    *,
    verapdf_profile: str,
) -> tuple[bool, list[dict[str, Any]]]:
    """Call veraPDF for one profile. Returns (compliant, failure_list).

    ``compliant`` is ``True`` when no findings come back (either the
    PDF really is conformant, or veraPDF was unreachable — callers
    treat "no failures returned" as "don't emit this finding").
    ``compliant`` is ``False`` when at least one failed rule was
    returned.
    """
    try:
        raw = validate_with_verapdf(pdf_bytes, profile=verapdf_profile)
    except Exception:
        logger.exception("veraPDF %s invocation failed", verapdf_profile)
        return True, []
    if not raw:
        return True, []
    summary = _summarise_failures(raw)
    return False, summary


def run_verapdf_checks(
    pdf_bytes: bytes,
    *,
    conformance: str | None,
    enabled_ua: bool,
) -> list[Finding]:
    """Run any applicable veraPDF flavours and emit stable findings.

    Args:
        pdf_bytes: Raw PDF bytes.
        conformance: ``PreflightProfile.conformance`` string (e.g.
            ``"pdfx4"``, ``"pdfa1b"``). ``None`` means "no conformance
            target" → no PDF/X or PDF/A finding.
        enabled_ua: True when the profile's checks include any
            ``LPDF_UA_*`` pattern (i.e., accessibility validation is
            on for this job).

    Returns:
        Up to three findings (LPDF_PDFX_CONF / LPDF_PDFA_CONF /
        LPDF_UA_CONF), one per flavour that ran and found failures.
        Empty list when veraPDF isn't configured, isn't reachable, or
        the PDF passes every configured flavour.
    """
    if not is_verapdf_configured():
        return []
    if not pdf_bytes:
        return []

    findings: list[Finding] = []

    # PDF/X → LPDF_PDFX_CONF (T1-CMP01)
    if conformance and conformance.lower() in _CONF_TO_VERAPDF_PDFX:
        vera_profile = _CONF_TO_VERAPDF_PDFX[conformance.lower()]
        compliant, failures = _run_flavour(pdf_bytes, verapdf_profile=vera_profile)
        if not compliant:
            findings.append(
                Finding(
                    inspection_id="LPDF_PDFX_CONF",
                    severity=Severity.ERROR,
                    message=(
                        f"PDF is not {conformance.upper()} conformant "
                        f"(veraPDF: {len(failures)} rule(s) failed)"
                    ),
                    details={
                        "conformance": conformance,
                        "verapdf_profile": vera_profile,
                        "failure_count": len(failures),
                        "failures": failures,
                        "validator": "veraPDF",
                    },
                    iso_clause="ISO 15930-* (PDF/X family)",
                )
            )

    # PDF/A → LPDF_PDFA_CONF (T4-A02)
    if conformance and conformance.lower() in _CONF_TO_VERAPDF_PDFA:
        vera_profile = _CONF_TO_VERAPDF_PDFA[conformance.lower()]
        compliant, failures = _run_flavour(pdf_bytes, verapdf_profile=vera_profile)
        if not compliant:
            findings.append(
                Finding(
                    inspection_id="LPDF_PDFA_CONF",
                    severity=Severity.ERROR,
                    message=(
                        f"PDF is not {conformance.upper()} conformant "
                        f"(veraPDF: {len(failures)} rule(s) failed)"
                    ),
                    details={
                        "conformance": conformance,
                        "verapdf_profile": vera_profile,
                        "failure_count": len(failures),
                        "failures": failures,
                        "validator": "veraPDF",
                    },
                    iso_clause="ISO 19005-* (PDF/A family)",
                )
            )

    # PDF/UA-1 → LPDF_UA_CONF (T4-A01). Only run when the profile opts in.
    if enabled_ua:
        compliant, failures = _run_flavour(pdf_bytes, verapdf_profile="PDFUA_1")
        if not compliant:
            findings.append(
                Finding(
                    inspection_id="LPDF_UA_CONF",
                    severity=Severity.WARNING,
                    message=(
                        "PDF is not PDF/UA-1 compliant "
                        f"(veraPDF Matterhorn: {len(failures)} checkpoint(s) failed)"
                    ),
                    details={
                        "verapdf_profile": "PDFUA_1",
                        "failure_count": len(failures),
                        "failures": failures,
                        "validator": "veraPDF",
                    },
                    iso_clause="ISO 14289-1 (PDF/UA) / Matterhorn Protocol",
                )
            )

    return findings
