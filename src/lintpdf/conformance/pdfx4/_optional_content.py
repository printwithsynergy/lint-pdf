"""PDF/X-4 optional content checks (PDFX4-066-070).

Validates optional content (OCG/layers) requirements per ISO 15930-7:2010 section 6.5.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_optional_content(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run optional content conformance checks."""
    findings: list[Finding] = []
    catalog = document.catalog

    oc_properties = catalog.get("/OCProperties")
    if not isinstance(oc_properties, dict):
        return findings

    # PDFX4-066: OCCD (default config) present
    default_config = oc_properties.get("/D")
    if not isinstance(default_config, dict):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-066",
                severity=Severity.WARNING,
                message="OCProperties /D (default configuration) missing",
                iso_clause="ISO 15930-7:2010 6.5",
            )
        )
        return findings

    # PDFX4-067: Default viewing = ON
    base_state = default_config.get("/BaseState") or default_config.get("BaseState") or "ON"
    if base_state not in ("ON", "Unchanged"):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-067",
                severity=Severity.WARNING,
                message=f"OCProperties default /BaseState is '{base_state}' (should be 'ON' for PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.5",
            )
        )

    # PDFX4-068: Printing configuration
    # /PrintState should map content as visible for print
    off_list = default_config.get("/OFF") or default_config.get("OFF")
    if isinstance(off_list, list) and off_list:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-068",
                severity=Severity.ADVISORY,
                message=f"OCProperties default config has {len(off_list)} layer(s) set to OFF",
                iso_clause="ISO 15930-7:2010 6.5",
                details={"off_count": len(off_list)},
            )
        )

    # PDFX4-069: OCGs defined in /OCGs array
    ocgs = oc_properties.get("/OCGs")
    if not isinstance(ocgs, list) or not ocgs:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-069",
                severity=Severity.WARNING,
                message="OCProperties present but /OCGs array is empty or missing",
                iso_clause="ISO 32000-2:2020 8.11.4.2",
            )
        )

    # PDFX4-070: No AS (auto-state) triggers
    as_triggers = default_config.get("/AS") or default_config.get("AS")
    if isinstance(as_triggers, list) and as_triggers:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-070",
                severity=Severity.WARNING,
                message="OCProperties has /AS (auto-state) triggers (not recommended for PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.5",
                details={"trigger_count": len(as_triggers)},
            )
        )

    return findings
