"""PDF/X-3 metadata checks (PDFX3-014 through PDFX3-020).

Validates metadata requirements per ISO 15930-6:2003 section 6.7.
PDF version must be <= 1.4, GTS_PDFXVersion must be "PDF/X-3:2003".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity
from grounded.conformance.xmp import XmpMetadata

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX3"


def validate_metadata(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run metadata conformance checks for PDF/X-3."""
    findings: list[Finding] = []

    # PDFX3-014: PDF version must be <= 1.4
    version = document.version
    if version:
        try:
            ver_num = float(version)
        except (ValueError, TypeError):
            ver_num = 0.0
        if ver_num > 1.4:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-014",
                    severity=Severity.ERROR,
                    message=(
                        f"PDF version {version} exceeds 1.4 "
                        f"(PDF/X-3 requires PDF 1.4 or earlier)"
                    ),
                    iso_clause="ISO 15930-6:2003 6.1",
                    details={"pdf_version": version},
                )
            )

    # Remaining checks require XMP metadata
    if document.metadata_stream is None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-015",
                severity=Severity.ERROR,
                message="XMP metadata stream missing (required for PDF/X-3)",
                iso_clause="ISO 15930-6:2003 6.7",
            )
        )
        return findings

    xmp = XmpMetadata.from_bytes(document.metadata_stream)

    # PDFX3-015: GTS_PDFXVersion must be present
    if not xmp.pdfx_version:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-015",
                severity=Severity.ERROR,
                message="GTS_PDFXVersion not declared in XMP (required for PDF/X-3)",
                iso_clause="ISO 15930-6:2003 6.7.3",
            )
        )
    else:
        # PDFX3-016: GTS_PDFXVersion value must be "PDF/X-3:2003"
        if "PDF/X-3" not in xmp.pdfx_version:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-016",
                    severity=Severity.ERROR,
                    message=(
                        f"GTS_PDFXVersion is '{xmp.pdfx_version}' "
                        f"(expected 'PDF/X-3:2003')"
                    ),
                    iso_clause="ISO 15930-6:2003 6.7.3",
                    details={"pdfx_version": xmp.pdfx_version},
                )
            )

    # PDFX3-017: /Trapped key must be present
    info_trapped = document.info_dict.get("/Trapped") or document.info_dict.get("Trapped")
    valid_trapped = {"True", "False", "Unknown"}
    if not info_trapped:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-017",
                severity=Severity.WARNING,
                message="/Trapped key missing from Info dictionary",
                iso_clause="ISO 15930-6:2003 6.7.5",
            )
        )
    elif str(info_trapped) not in valid_trapped:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-017",
                severity=Severity.WARNING,
                message=f"/Trapped value '{info_trapped}' is not valid (expected True/False/Unknown)",
                iso_clause="ISO 15930-6:2003 6.7.5",
                details={"trapped": str(info_trapped)},
            )
        )

    # PDFX3-018: /CreationDate must be present
    info_create = document.info_dict.get("/CreationDate") or document.info_dict.get("CreationDate")
    if not info_create:
        if not xmp.create_date:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-018",
                    severity=Severity.WARNING,
                    message="CreationDate missing from both Info dict and XMP metadata",
                    iso_clause="ISO 15930-6:2003 6.7.5",
                )
            )

    # PDFX3-019: /ModDate must be present
    info_mod = document.info_dict.get("/ModDate") or document.info_dict.get("ModDate")
    if not info_mod:
        if not xmp.modify_date:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-019",
                    severity=Severity.WARNING,
                    message="ModDate missing from both Info dict and XMP metadata",
                    iso_clause="ISO 15930-6:2003 6.7.5",
                )
            )

    # PDFX3-020: /Title must be present
    info_title = document.info_dict.get("/Title") or document.info_dict.get("Title")
    if not info_title:
        if not xmp.title:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-020",
                    severity=Severity.WARNING,
                    message="Title missing from both Info dict and XMP metadata",
                    iso_clause="ISO 15930-6:2003 6.7.5",
                )
            )

    return findings
