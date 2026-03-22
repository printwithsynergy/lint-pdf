"""PDF/X-1a metadata checks (PDFX1A-016-022).

Validates metadata requirements per ISO 15930-4:2003 section 6.7.
PDF/X-1a uses the Info dictionary (not XMP) for conformance metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX1A"

# Valid PDF/X-1a version strings
_VALID_PDFX_VERSIONS = {
    "PDF/X-1a:2003",
    "PDF/X-1:2001",
    "PDF/X-1a:2001",
}


def validate_metadata(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run metadata conformance checks."""
    findings: list[Finding] = []

    # PDFX1A-016: PDF version > 1.4 (must be 1.3 or 1.4 for X-1a:2003)
    version = document.version
    if version:
        try:
            ver_num = float(version)
        except (ValueError, TypeError):
            ver_num = 0.0
        if ver_num > 1.4:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-016",
                    severity=Severity.AGROUND,
                    message=(
                        f"PDF version {version} exceeds maximum allowed for PDF/X-1a "
                        f"(must be 1.3 or 1.4)"
                    ),
                    iso_clause="ISO 15930-4:2003 6.1",
                    details={"version": version},
                )
            )

    info_dict = document.info_dict

    # PDFX1A-017: Missing /GTS_PDFXVersion in Info dict
    pdfx_version = info_dict.get("/GTS_PDFXVersion") or info_dict.get("GTS_PDFXVersion")
    if not pdfx_version:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-017",
                severity=Severity.AGROUND,
                message="/GTS_PDFXVersion missing from Info dictionary (required for PDF/X-1a)",
                iso_clause="ISO 15930-4:2003 6.7.3",
            )
        )
    else:
        # PDFX1A-018: /GTS_PDFXVersion value incorrect
        if pdfx_version not in _VALID_PDFX_VERSIONS:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-018",
                    severity=Severity.AGROUND,
                    message=(
                        f"/GTS_PDFXVersion is '{pdfx_version}' "
                        f"(expected 'PDF/X-1a:2003' or 'PDF/X-1:2001')"
                    ),
                    iso_clause="ISO 15930-4:2003 6.7.3",
                    details={"pdfx_version": pdfx_version},
                )
            )

    # PDFX1A-019: /Trapped key missing
    trapped = info_dict.get("/Trapped") or info_dict.get("Trapped")
    if trapped is None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-019",
                severity=Severity.SQUALL,
                message="/Trapped key missing from Info dictionary",
                iso_clause="ISO 15930-4:2003 6.7.5",
            )
        )

    # PDFX1A-020: /CreationDate missing
    creation_date = info_dict.get("/CreationDate") or info_dict.get("CreationDate")
    if not creation_date:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-020",
                severity=Severity.SQUALL,
                message="/CreationDate missing from Info dictionary",
                iso_clause="ISO 15930-4:2003 6.7.5",
            )
        )

    # PDFX1A-021: /ModDate missing
    mod_date = info_dict.get("/ModDate") or info_dict.get("ModDate")
    if not mod_date:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-021",
                severity=Severity.SQUALL,
                message="/ModDate missing from Info dictionary",
                iso_clause="ISO 15930-4:2003 6.7.5",
            )
        )

    # PDFX1A-022: /Title missing
    title = info_dict.get("/Title") or info_dict.get("Title")
    if not title:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-022",
                severity=Severity.SQUALL,
                message="/Title missing from Info dictionary",
                iso_clause="ISO 15930-4:2003 6.7.5",
            )
        )

    return findings
