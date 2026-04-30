"""PDF/X-1a output intent checks (PDFX1A-023-028).

Validates OutputIntent requirements per ISO 15930-4:2003 section 6.2.3.
PDF/X-1a is stricter than PDF/X-4: no RGB ICC profiles allowed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX1A"

# Registered output conditions that don't require an embedded ICC profile
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


def validate_output_intent(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run output intent conformance checks."""
    findings: list[Finding] = []

    intents = document.output_intents

    # PDFX1A-023: No OutputIntent present
    if not intents:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-023",
                severity=Severity.ERROR,
                message="No OutputIntent present (required for PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.3",
            )
        )
        return findings

    gts_pdfx_count = 0

    for i, intent in enumerate(intents):
        subtype = intent.get("/S") or intent.get("S") or ""

        # Count GTS_PDFX intents
        if subtype in ("/GTS_PDFX", "GTS_PDFX"):
            gts_pdfx_count += 1
        else:
            # Non-GTS_PDFX intents are allowed but we only validate GTS_PDFX
            continue

        # PDFX1A-025: OutputConditionIdentifier missing
        oci = intent.get("/OutputConditionIdentifier") or intent.get("OutputConditionIdentifier")
        if not oci:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-025",
                    severity=Severity.ERROR,
                    message=f"OutputIntent {i + 1}: /OutputConditionIdentifier missing",
                    iso_clause="ISO 15930-4:2003 6.2.3",
                )
            )

        # PDFX1A-026: ICC profile not embedded and not registered condition
        dest_profile = intent.get("/DestOutputProfile") or intent.get("DestOutputProfile")
        is_registered = oci in _REGISTERED_CONDITIONS if oci else False

        if dest_profile is None and not is_registered:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-026",
                    severity=Severity.ERROR,
                    message=(
                        f"OutputIntent {i + 1}: ICC profile not embedded "
                        f"and condition '{oci}' is not a registered name"
                    ),
                    iso_clause="ISO 15930-4:2003 6.2.3",
                    details={"output_condition": oci},
                )
            )

        # PDFX1A-027: ICC profile color space is RGB (must be CMYK or Gray for X-1a)
        if isinstance(dest_profile, dict):
            icc_cs = dest_profile.get("/ColorSpace") or dest_profile.get("ColorSpace") or ""
            if icc_cs and icc_cs.upper() in ("RGB", "SRGB"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-027",
                        severity=Severity.ERROR,
                        message=(
                            f"OutputIntent {i + 1}: ICC profile color space is '{icc_cs}' "
                            f"(must be CMYK or Gray for PDF/X-1a)"
                        ),
                        iso_clause="ISO 15930-4:2003 6.2.3",
                        details={"icc_color_space": icc_cs},
                    )
                )

    # PDFX1A-024: No GTS_PDFX output intent
    if gts_pdfx_count == 0:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-024",
                severity=Severity.ERROR,
                message="No OutputIntent with /S = /GTS_PDFX found (required for PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.2.3",
            )
        )

    # PDFX1A-028: Multiple GTS_PDFX intents
    if gts_pdfx_count > 1:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-028",
                severity=Severity.WARNING,
                message=f"Multiple GTS_PDFX OutputIntents found ({gts_pdfx_count})",
                iso_clause="ISO 15930-4:2003 6.2.3",
                details={"gts_pdfx_count": gts_pdfx_count},
            )
        )

    return findings
