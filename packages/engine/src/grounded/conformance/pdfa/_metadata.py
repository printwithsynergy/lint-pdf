"""PDF/A metadata checks (PDFA-001-010).

Validates metadata requirements per ISO 19005.
PDF/A requires XMP metadata with pdfaid:part and pdfaid:conformance,
output intent with ICC profile, and document info consistency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFA"


def validate_metadata(  # skipcq: PY-R1000
    document: SemanticDocument, level: str
) -> list[Finding]:
    """Run metadata conformance checks."""
    findings: list[Finding] = []

    catalog = document.catalog

    # PDFA-010: Document catalog /Metadata entry missing
    catalog_metadata = catalog.get("/Metadata") or catalog.get("Metadata")
    if catalog_metadata is None:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-010",
                severity=Severity.AGROUND,
                message="/Metadata entry missing from document catalog (required for PDF/A)",
                iso_clause="ISO 19005 6.7.1",
            )
        )

    # PDFA-001: XMP metadata stream missing
    xmp = document.xmp_metadata
    if not xmp:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-001",
                severity=Severity.AGROUND,
                message="XMP metadata stream missing (required for PDF/A)",
                iso_clause="ISO 19005 6.7.2",
            )
        )
        # Without XMP, skip checks that depend on it
    else:
        # PDFA-002: pdfaid:part missing in XMP
        pdfaid_part = xmp.get("pdfaid:part") or xmp.get("pdfaid_part")
        if not pdfaid_part:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-002",
                    severity=Severity.AGROUND,
                    message="pdfaid:part missing in XMP metadata (required for PDF/A identification)",
                    iso_clause="ISO 19005 6.7.11",
                )
            )

        # PDFA-003: pdfaid:conformance missing in XMP
        pdfaid_conf = xmp.get("pdfaid:conformance") or xmp.get("pdfaid_conformance")
        if not pdfaid_conf:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-003",
                    severity=Severity.AGROUND,
                    message=(
                        "pdfaid:conformance missing in XMP metadata "
                        "(required for PDF/A identification)"
                    ),
                    iso_clause="ISO 19005 6.7.11",
                )
            )

        # PDFA-004: Document info dict and XMP mismatch
        info_dict = document.info_dict
        _xmp_info_fields = {
            "Title": ("dc:title", "dc_title"),
            "Author": ("dc:creator", "dc_creator"),
            "Subject": ("dc:description", "dc_description"),
            "Creator": ("xmp:CreatorTool", "xmp_CreatorTool"),
            "Producer": ("pdf:Producer", "pdf_Producer"),
        }
        for info_key, (xmp_key, xmp_alt_key) in _xmp_info_fields.items():
            info_val = info_dict.get(f"/{info_key}") or info_dict.get(info_key)
            xmp_val = xmp.get(xmp_key) or xmp.get(xmp_alt_key)
            if info_val and xmp_val and str(info_val) != str(xmp_val):
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-004",
                        severity=Severity.SQUALL,
                        message=(
                            f"Info dict /{info_key} ('{info_val}') does not match "
                            f"XMP {xmp_key} ('{xmp_val}')"
                        ),
                        iso_clause="ISO 19005 6.7.3",
                        details={"info_key": info_key, "info_val": str(info_val), "xmp_val": str(xmp_val)},
                    )
                )

    info_dict = document.info_dict

    # PDFA-005: /CreationDate missing
    creation_date = info_dict.get("/CreationDate") or info_dict.get("CreationDate")
    if not creation_date:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-005",
                severity=Severity.SQUALL,
                message="/CreationDate missing from Info dictionary (required for PDF/A)",
                iso_clause="ISO 19005 6.7.3",
            )
        )

    # PDFA-006: /ModDate missing
    mod_date = info_dict.get("/ModDate") or info_dict.get("ModDate")
    if not mod_date:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-006",
                severity=Severity.SQUALL,
                message="/ModDate missing from Info dictionary (required for PDF/A)",
                iso_clause="ISO 19005 6.7.3",
            )
        )

    # PDFA-007: Output intent missing (required for PDF/A)
    intents = document.output_intents
    if not intents:
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-007",
                severity=Severity.AGROUND,
                message="No OutputIntent present (required for PDF/A)",
                iso_clause="ISO 19005 6.2.2",
            )
        )
    else:
        # PDFA-008: Output intent ICC profile missing
        has_profile = False
        for intent in intents:
            dest_profile = intent.get("/DestOutputProfile") or intent.get("DestOutputProfile")
            if dest_profile is not None:
                has_profile = True
                break
        if not has_profile:
            # Check for registered output condition identifier
            has_registered = False
            for intent in intents:
                oci = (
                    intent.get("/OutputConditionIdentifier")
                    or intent.get("OutputConditionIdentifier")
                )
                if oci:
                    has_registered = True
                    break
            if not has_registered:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-008",
                        severity=Severity.AGROUND,
                        message=(
                            "OutputIntent ICC profile missing and no registered "
                            "OutputConditionIdentifier found"
                        ),
                        iso_clause="ISO 19005 6.2.2",
                    )
                )

    # PDFA-009: PDF version too high for level
    version = document.version
    if version:
        try:
            ver_num = float(version)
        except (ValueError, TypeError):
            ver_num = 0.0

        if level.startswith("1"):
            # PDF/A-1b requires PDF 1.4 or lower
            if ver_num > 1.4:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-009",
                        severity=Severity.AGROUND,
                        message=(
                            f"PDF version {version} exceeds maximum allowed for PDF/A-1 "
                            f"(must be 1.4 or lower)"
                        ),
                        iso_clause="ISO 19005-1 6.1",
                        details={"version": version, "max_version": "1.4"},
                    )
                )
        elif level.startswith("2") or level.startswith("3"):
            # PDF/A-2b and PDF/A-3b require PDF 1.7 or lower
            if ver_num > 1.7:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-009",
                        severity=Severity.AGROUND,
                        message=(
                            f"PDF version {version} exceeds maximum allowed for PDF/A-{level[0]} "
                            f"(must be 1.7 or lower)"
                        ),
                        iso_clause=f"ISO 19005-{level[0]} 6.1",
                        details={"version": version, "max_version": "1.7"},
                    )
                )

    return findings
