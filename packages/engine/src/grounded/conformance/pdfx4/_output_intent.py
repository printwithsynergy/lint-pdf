"""PDF/X-4 output intent checks (PDFX4-016-025).

Validates OutputIntent requirements per ISO 15930-7:2010 section 6.2.3.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX4"

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

    # PDFX4-016: At least one output intent
    if not intents:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-016",
                severity=Severity.ERROR,
                message="No OutputIntent present (required for PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.2.3",
            )
        )
        return findings

    gts_pdfx_count = 0

    for i, intent in enumerate(intents):
        subtype = intent.get("/S") or intent.get("S") or ""

        # PDFX4-017: /S must be /GTS_PDFX
        if subtype in ("/GTS_PDFX", "GTS_PDFX"):
            gts_pdfx_count += 1
        else:
            # Non-GTS_PDFX intents are allowed but we only validate GTS_PDFX
            continue

        # PDFX4-018: /OutputConditionIdentifier present
        oci = intent.get("/OutputConditionIdentifier") or intent.get("OutputConditionIdentifier")
        if not oci:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-018",
                    severity=Severity.ERROR,
                    message=f"OutputIntent {i + 1}: /OutputConditionIdentifier missing",
                    iso_clause="ISO 15930-7:2010 6.2.3",
                )
            )

        # PDFX4-019: ICC profile embedded or registered condition
        dest_profile = intent.get("/DestOutputProfile") or intent.get("DestOutputProfile")
        is_registered = oci in _REGISTERED_CONDITIONS if oci else False

        if dest_profile is None and not is_registered:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-019",
                    severity=Severity.ERROR,
                    message=(
                        f"OutputIntent {i + 1}: ICC profile not embedded "
                        f"and condition '{oci}' is not a registered name"
                    ),
                    iso_clause="ISO 15930-7:2010 6.2.3",
                    details={"output_condition": oci},
                )
            )

        # PDFX4-020: ICC profile version >= 2.0
        if isinstance(dest_profile, dict):
            icc_version = dest_profile.get("/ICCVersion") or dest_profile.get("ICCVersion")
            if icc_version is not None:
                try:
                    ver = float(icc_version)
                except (ValueError, TypeError):
                    ver = 0.0
                if ver < 2.0:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-020",
                            severity=Severity.WARNING,
                            message=f"OutputIntent {i + 1}: ICC profile version {icc_version} < 2.0",
                            iso_clause="ISO 15930-7:2010 6.2.4",
                        )
                    )

            # PDFX4-021: ICC profile class is output or display
            profile_class = (
                dest_profile.get("/ProfileClass") or dest_profile.get("ProfileClass") or ""
            )
            if profile_class and profile_class not in ("prtr", "mntr", "output", "display"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-021",
                        severity=Severity.WARNING,
                        message=(
                            f"OutputIntent {i + 1}: ICC profile class '{profile_class}' "
                            f"is not output (prtr) or display (mntr)"
                        ),
                        iso_clause="ISO 15930-7:2010 6.2.4",
                    )
                )

            # PDFX4-022: ICC color space matches usage
            icc_cs = dest_profile.get("/ColorSpace") or dest_profile.get("ColorSpace") or ""
            if icc_cs and icc_cs not in ("CMYK", "RGB", "Gray", "Lab"):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-022",
                        severity=Severity.WARNING,
                        message=f"OutputIntent {i + 1}: ICC color space '{icc_cs}' not recognized",
                        iso_clause="ISO 15930-7:2010 6.2.4",
                    )
                )

        # PDFX4-024: /RegistryName if registered condition
        if is_registered:
            registry = intent.get("/RegistryName") or intent.get("RegistryName")
            if not registry:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-024",
                        severity=Severity.ADVISORY,
                        message=(
                            f"OutputIntent {i + 1}: /RegistryName missing "
                            f"for registered condition '{oci}'"
                        ),
                        iso_clause="ISO 15930-7:2010 6.2.3",
                    )
                )

        # PDFX4-025: /Info string present
        info_str = intent.get("/Info") or intent.get("Info")
        if not info_str:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-025",
                    severity=Severity.ADVISORY,
                    message=f"OutputIntent {i + 1}: /Info string missing",
                    iso_clause="ISO 15930-7:2010 6.2.3",
                )
            )

    # PDFX4-017: At least one GTS_PDFX output intent required
    if gts_pdfx_count == 0:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-017",
                severity=Severity.ERROR,
                message="No OutputIntent with /S = /GTS_PDFX found (required for PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.2.3",
            )
        )

    # PDFX4-023: Only one GTS_PDFX output intent
    if gts_pdfx_count > 1:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-023",
                severity=Severity.WARNING,
                message=f"Multiple GTS_PDFX OutputIntents found ({gts_pdfx_count})",
                iso_clause="ISO 15930-7:2010 6.2.3",
                details={"gts_pdfx_count": gts_pdfx_count},
            )
        )

    return findings
