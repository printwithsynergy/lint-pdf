"""PDF/X-3 output intent checks (PDFX3-021-026).

Validates OutputIntent requirements per ISO 15930-6:2003.
Unlike X-1a, RGB ICC profiles ARE allowed in output intents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX3"

_REGISTERED_CONDITIONS = {
    "CGATS TR 001",
    "CGATS TR 003",
    "CGATS TR 006",
    "FOGRA39",
    "FOGRA47",
    "FOGRA51",
    "FOGRA52",
    "FOGRA53",
    "FOGRA54",
    "FOGRA55",
    "FOGRA56",
    "FOGRA57",
    "FOGRA58",
    "FOGRA59",
    "GRACoL2006_Coated1v2",
    "GRACoL2013_CRPC6",
    "IFRA26",
    "Japan Color 2001 Coated",
    "Japan Color 2002 Newspaper",
    "Japan Color 2003 Web Coated",
    "Japan Color 2011 Coated",
    "SNAP 2007",
    "SWOP2006_Coated3v2",
    "SWOP2006_Coated5v2",
    "SWOP2013_CRPC5",
}


def validate_output_intent(document: SemanticDocument) -> list[Finding]:
    """Run output intent conformance checks for PDF/X-3."""
    findings: list[Finding] = []
    intents = document.output_intents

    if not intents:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-021",
                severity=Severity.ERROR,
                message="No OutputIntent present (required for PDF/X-3)",
                iso_clause="ISO 15930-6:2003 6.2.3",
            )
        )
        return findings

    gts_pdfx_count = 0
    for i, intent in enumerate(intents):
        subtype = intent.get("/S") or intent.get("S") or ""
        if subtype in ("/GTS_PDFX", "GTS_PDFX"):
            gts_pdfx_count += 1
        else:
            continue

        oci = intent.get("/OutputConditionIdentifier") or intent.get("OutputConditionIdentifier")
        if not oci:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-023",
                    severity=Severity.ERROR,
                    message=f"OutputIntent {i + 1}: /OutputConditionIdentifier missing",
                    iso_clause="ISO 15930-6:2003 6.2.3",
                )
            )

        dest_profile = intent.get("/DestOutputProfile") or intent.get("DestOutputProfile")
        is_registered = oci in _REGISTERED_CONDITIONS if oci else False
        if dest_profile is None and not is_registered:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-024",
                    severity=Severity.ERROR,
                    message=(
                        f"OutputIntent {i + 1}: ICC profile not embedded "
                        f"and condition '{oci}' is not registered"
                    ),
                    iso_clause="ISO 15930-6:2003 6.2.3",
                    details={"output_condition": oci},
                )
            )

        if isinstance(dest_profile, dict):
            icc_cs = dest_profile.get("/ColorSpace") or dest_profile.get("ColorSpace") or ""
            if icc_cs and icc_cs not in ("CMYK", "RGB", "Gray", "Lab"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-026",
                        severity=Severity.WARNING,
                        message=f"OutputIntent {i + 1}: ICC color space '{icc_cs}' not recognized",
                        iso_clause="ISO 15930-6:2003 6.2.3",
                    )
                )

    if gts_pdfx_count == 0:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-022",
                severity=Severity.ERROR,
                message="No OutputIntent with /S = /GTS_PDFX found (required for PDF/X-3)",
                iso_clause="ISO 15930-6:2003 6.2.3",
            )
        )

    if gts_pdfx_count > 1:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-025",
                severity=Severity.WARNING,
                message=f"Multiple GTS_PDFX OutputIntents found ({gts_pdfx_count})",
                iso_clause="ISO 15930-6:2003 6.2.3",
            )
        )

    return findings
