"""PDF/X-3 font checks (PDFX3-009 through PDFX3-013).

Validates font embedding requirements per ISO 15930-6:2003 section 6.3.
All fonts must be embedded. Same rules as PDF/X-1a.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX3"


def validate_fonts(document: SemanticDocument) -> list[Finding]:
    """Run font conformance checks for PDF/X-3."""
    findings: list[Finding] = []

    for page in document.pages:
        font_resources = page.resources.get("/Font") or page.resources.get("Font")
        if not isinstance(font_resources, dict):
            continue

        for font_name, font_dict in font_resources.items():
            if not isinstance(font_dict, dict):
                continue

            findings.extend(_check_font(font_name, font_dict, page.page_num))

    return findings


def _check_font(
    font_name: str, font_dict: dict[str, Any], page_num: int
) -> list[Finding]:  # skipcq: PY-R1000
    """Check a single font dictionary for PDF/X-3 compliance."""
    findings: list[Finding] = []

    subtype = font_dict.get("/Subtype") or font_dict.get("Subtype") or ""
    base_font = font_dict.get("/BaseFont") or font_dict.get("BaseFont") or font_name
    descriptor = font_dict.get("/FontDescriptor") or font_dict.get("FontDescriptor")
    descendant = font_dict.get("/DescendantFonts") or font_dict.get("DescendantFonts")

    # PDFX3-009: All fonts must be embedded
    if isinstance(descriptor, dict):
        has_font_file = (
            descriptor.get("/FontFile") is not None
            or descriptor.get("/FontFile2") is not None
            or descriptor.get("/FontFile3") is not None
            or descriptor.get("FontFile") is not None
            or descriptor.get("FontFile2") is not None
            or descriptor.get("FontFile3") is not None
        )
        if not has_font_file:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-009",
                    severity=Severity.ERROR,
                    message=f"Font '{base_font}' is not embedded (required for PDF/X-3)",
                    page_num=page_num,
                    iso_clause="ISO 15930-6:2003 6.3",
                    object_id=font_name,
                    object_type="font",
                )
            )
    elif subtype not in ("Type3", "/Type3"):
        # Type0 composite fonts have descriptors on descendant CIDFont
        if isinstance(descendant, list) and descendant:
            cid_font = descendant[0] if isinstance(descendant[0], dict) else {}
            cid_descriptor = cid_font.get("/FontDescriptor") or cid_font.get("FontDescriptor")
            if isinstance(cid_descriptor, dict):
                has_cid_file = (
                    cid_descriptor.get("/FontFile") is not None
                    or cid_descriptor.get("/FontFile2") is not None
                    or cid_descriptor.get("/FontFile3") is not None
                )
                if not has_cid_file:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-009",
                            severity=Severity.ERROR,
                            message=f"CID font '{base_font}' is not embedded",
                            page_num=page_num,
                            iso_clause="ISO 15930-6:2003 6.3",
                            object_id=font_name,
                            object_type="font",
                        )
                    )

    # PDFX3-010: Type 3 font used (flagged for review)
    if subtype in ("Type3", "/Type3"):
        char_procs = font_dict.get("/CharProcs") or font_dict.get("CharProcs")
        if not isinstance(char_procs, dict) or not char_procs:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-010",
                    severity=Severity.ERROR,
                    message=f"Type3 font '{base_font}' has no /CharProcs",
                    page_num=page_num,
                    iso_clause="ISO 15930-6:2003 6.3",
                    object_id=font_name,
                    object_type="font",
                )
            )

    # PDFX3-011: Font missing FontDescriptor (for non-Type3, non-composite)
    if (
        subtype not in ("Type3", "/Type3")
        and descriptor is None
        and not (isinstance(descendant, list) and descendant)
    ):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-011",
                severity=Severity.WARNING,
                message=f"Font '{base_font}' missing /FontDescriptor",
                page_num=page_num,
                iso_clause="ISO 15930-6:2003 6.3",
                object_id=font_name,
                object_type="font",
            )
        )

    # PDFX3-012: CID font missing CIDSystemInfo
    if isinstance(descendant, list) and descendant:
        cid_font = descendant[0] if isinstance(descendant[0], dict) else {}
        cid_sys_info = cid_font.get("/CIDSystemInfo") or cid_font.get("CIDSystemInfo")
        if cid_sys_info is None:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-012",
                    severity=Severity.WARNING,
                    message=f"CID font '{base_font}' missing /CIDSystemInfo",
                    page_num=page_num,
                    iso_clause="ISO 15930-6:2003 6.3",
                    object_id=font_name,
                    object_type="font",
                )
            )

    # PDFX3-013: Font missing encoding
    if subtype not in ("Type3", "/Type3"):
        encoding = font_dict.get("/Encoding") or font_dict.get("Encoding")
        if encoding is None and not (isinstance(descendant, list) and descendant):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-013",
                    severity=Severity.ADVISORY,
                    message=f"Font '{base_font}' has no explicit /Encoding entry",
                    page_num=page_num,
                    iso_clause="ISO 15930-6:2003 6.3",
                    object_id=font_name,
                    object_type="font",
                )
            )

    return findings
