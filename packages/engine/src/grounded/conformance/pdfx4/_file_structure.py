"""PDF/X-4 file structure checks (PDFX4-001-004, 080-084).

Validates PDF version, header markers, cross-reference integrity,
and trailer requirements per ISO 15930-7:2010 and ISO 32000-2:2020.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


def validate_file_structure(document: SemanticDocument) -> list[Finding]:  # skipcq: PY-R1000
    """Run file structure conformance checks."""
    findings: list[Finding] = []

    # PDFX4-001: PDF version >= 1.6
    version = document.version
    try:
        ver_num = float(version)
    except (ValueError, TypeError):
        ver_num = 0.0

    if ver_num < 1.6:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-001",
                severity=Severity.AGROUND,
                message=f"PDF version {version} is below minimum 1.6 required for PDF/X-4",
                iso_clause="ISO 15930-7:2010 6.1.2",
            )
        )

    # PDFX4-002: %PDF header present (validated by parser, check version exists)
    if not version:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-002",
                severity=Severity.AGROUND,
                message="PDF header version not detected",
                iso_clause="ISO 32000-2:2020 7.5.2",
            )
        )

    # PDFX4-003: Binary marker in header
    # The binary marker is the comment line with high-byte chars after %PDF header.
    # We check via trailer/catalog metadata if available.
    header_bytes = document.trailer.get("/HeaderBytes") or document.catalog.get("/HeaderBytes")
    if header_bytes is not None and not header_bytes:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-003",
                severity=Severity.ADVISORY,
                message="Binary marker missing from PDF header",
                iso_clause="ISO 32000-2:2020 7.5.2",
            )
        )

    # PDFX4-004: Linearized structure valid (if linearized)
    is_linearized = (
        document.catalog.get("/Linearized") is not None
        or document.trailer.get("/Linearized") is not None
    )
    if is_linearized:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-004",
                severity=Severity.ADVISORY,
                message="Linearized PDF detected (verify linearization table integrity)",
                iso_clause="ISO 32000-2:2020 Annex F",
            )
        )

    # PDFX4-080: All streams decompress (verified at parse time)
    # This is a structural check — if parsing succeeded, streams are valid.
    # We flag if the parser reported decompression failures.
    decompress_errors = document.catalog.get("/DecompressErrors")
    if isinstance(decompress_errors, list) and decompress_errors:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-080",
                severity=Severity.AGROUND,
                message=f"Stream decompression failures: {len(decompress_errors)} stream(s)",
                iso_clause="ISO 32000-2:2020 7.3.8",
                details={"error_count": len(decompress_errors)},
            )
        )

    # PDFX4-081: No broken object references
    broken_refs = document.catalog.get("/BrokenReferences")
    if isinstance(broken_refs, list) and broken_refs:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-081",
                severity=Severity.AGROUND,
                message=f"Broken object references found: {len(broken_refs)} reference(s)",
                iso_clause="ISO 32000-2:2020 7.3.10",
                details={"broken_count": len(broken_refs)},
            )
        )

    # PDFX4-082: Cross-reference table valid
    xref_errors = document.catalog.get("/XRefErrors")
    if isinstance(xref_errors, list) and xref_errors:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-082",
                severity=Severity.AGROUND,
                message="Cross-reference table errors detected",
                iso_clause="ISO 32000-2:2020 7.5.4",
            )
        )

    # PDFX4-083: /ID array in trailer
    trailer_id = document.trailer.get("/ID")
    if trailer_id is None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-083",
                severity=Severity.SQUALL,
                message="Trailer /ID array missing (required for PDF/X-4)",
                iso_clause="ISO 32000-2:2020 14.4",
            )
        )

    # PDFX4-084: Incremental updates flagged
    if document.trailer.get("/Prev") is not None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-084",
                severity=Severity.ADVISORY,
                message="Incremental updates detected (trailer has /Prev reference)",
                iso_clause="ISO 32000-2:2020 7.5.6",
            )
        )

    return findings
