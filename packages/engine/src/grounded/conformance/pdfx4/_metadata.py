"""PDF/X-4 metadata checks (PDFX4-005-015).

Validates XMP metadata requirements per ISO 15930-7:2010 section 6.7.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity
from grounded.conformance.xmp import XmpMetadata

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_metadata(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run metadata conformance checks."""
    findings: list[Finding] = []

    # PDFX4-005: XMP metadata stream present
    if document.metadata_stream is None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-005",
                severity=Severity.AGROUND,
                message="XMP metadata stream missing (required for PDF/X-4)",
                iso_clause="ISO 15930-7:2010 6.7.2",
            )
        )
        return findings

    xmp = XmpMetadata.from_bytes(document.metadata_stream)

    # PDFX4-006: GTS_PDFXVersion declares "PDF/X-4"
    if not xmp.pdfx_version:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-006",
                severity=Severity.AGROUND,
                message="GTS_PDFXVersion not declared in XMP",
                iso_clause="ISO 15930-7:2010 6.7.3",
            )
        )
    elif "PDF/X-4" not in xmp.pdfx_version:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-006",
                severity=Severity.AGROUND,
                message=f"GTS_PDFXVersion is '{xmp.pdfx_version}' (expected 'PDF/X-4')",
                iso_clause="ISO 15930-7:2010 6.7.3",
                details={"pdfx_version": xmp.pdfx_version},
            )
        )

    # PDFX4-007: GTS_PDFXConformance present
    if not xmp.pdfx_conformance:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-007",
                severity=Severity.ADVISORY,
                message="GTS_PDFXConformance not declared in XMP",
                iso_clause="ISO 15930-7:2010 6.7.3",
            )
        )

    # PDFX4-008: pdf:PDFVersion matches header
    if xmp.pdf_version and xmp.pdf_version != document.version:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-008",
                severity=Severity.SQUALL,
                message=(
                    f"XMP pdf:PDFVersion '{xmp.pdf_version}' "
                    f"does not match header version '{document.version}'"
                ),
                iso_clause="ISO 15930-7:2010 6.7.4",
                details={
                    "xmp_version": xmp.pdf_version,
                    "header_version": document.version,
                },
            )
        )

    # PDFX4-009: xmp:CreateDate present
    if not xmp.create_date:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-009",
                severity=Severity.SQUALL,
                message="xmp:CreateDate missing from XMP metadata",
                iso_clause="ISO 15930-7:2010 6.7.5",
            )
        )

    # PDFX4-010: xmp:ModifyDate present
    if not xmp.modify_date:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-010",
                severity=Severity.SQUALL,
                message="xmp:ModifyDate missing from XMP metadata",
                iso_clause="ISO 15930-7:2010 6.7.5",
            )
        )

    # PDFX4-011: dc:title present
    if not xmp.title:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-011",
                severity=Severity.SQUALL,
                message="dc:title missing from XMP metadata",
                iso_clause="ISO 15930-7:2010 6.7.5",
            )
        )

    # PDFX4-012: pdf:Trapped = True|False|Unknown
    valid_trapped = {"True", "False", "Unknown"}
    if xmp.trapped and xmp.trapped not in valid_trapped:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-012",
                severity=Severity.SQUALL,
                message=f"pdf:Trapped value '{xmp.trapped}' is not valid (expected True/False/Unknown)",
                iso_clause="ISO 15930-7:2010 6.7.6",
                details={"trapped": xmp.trapped},
            )
        )

    # PDFX4-013: Info /Title matches XMP dc:title
    info_title = document.info_dict.get("/Title") or document.info_dict.get("Title") or ""
    if xmp.title and info_title and xmp.title != info_title:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-013",
                severity=Severity.ADVISORY,
                message="Info dict /Title does not match XMP dc:title",
                iso_clause="ISO 15930-7:2010 6.7.7",
                details={"info_title": info_title, "xmp_title": xmp.title},
            )
        )

    # PDFX4-014: Info /CreationDate matches XMP xmp:CreateDate
    info_create = document.info_dict.get("/CreationDate") or document.info_dict.get("CreationDate")
    if info_create and xmp.create_date and not _dates_match(str(info_create), xmp.create_date):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-014",
                severity=Severity.ADVISORY,
                message="Info dict /CreationDate does not match XMP xmp:CreateDate",
                iso_clause="ISO 15930-7:2010 6.7.7",
            )
        )

    # PDFX4-015: Info /ModDate matches XMP xmp:ModifyDate
    info_mod = document.info_dict.get("/ModDate") or document.info_dict.get("ModDate")
    if info_mod and xmp.modify_date and not _dates_match(str(info_mod), xmp.modify_date):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-015",
                severity=Severity.ADVISORY,
                message="Info dict /ModDate does not match XMP xmp:ModifyDate",
                iso_clause="ISO 15930-7:2010 6.7.7",
            )
        )

    return findings


def _dates_match(pdf_date: str, xmp_date: str) -> bool:
    """Compare PDF date string (D:YYYYMMDDHHmmSS) with XMP ISO 8601 date.

    This is a simplified comparison — extracts the date portion and compares.
    """
    # Strip PDF date prefix
    pdf_clean = pdf_date.replace("D:", "").replace("'", "")[:14]
    # Extract digits from XMP date
    xmp_clean = ""
    for ch in xmp_date:
        if ch.isdigit():
            xmp_clean += ch
        if len(xmp_clean) >= 14:
            break
    # Compare available digits
    min_len = min(len(pdf_clean), len(xmp_clean), 8)  # At least compare YYYYMMDD
    if min_len < 8:
        return True  # Not enough data to compare
    return pdf_clean[:min_len] == xmp_clean[:min_len]
