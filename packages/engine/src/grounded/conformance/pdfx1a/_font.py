"""PDF/X-1a font checks (PDFX1A-011-015).

Validates font embedding requirements per ISO 15930-4:2003 section 6.3.
All fonts must be embedded; Type 3 fonts are prohibited.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFX1A"


def validate_fonts(document: SemanticDocument) -> list[Finding]:
    """Run font conformance checks."""
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
    """Check a single font dictionary for PDF/X-1a compliance."""
    findings: list[Finding] = []

    subtype = font_dict.get("/Subtype") or font_dict.get("Subtype") or ""
    base_font = font_dict.get("/BaseFont") or font_dict.get("BaseFont") or font_name
    descriptor = font_dict.get("/FontDescriptor") or font_dict.get("FontDescriptor")

    # PDFX1A-012: Type 3 font used (prohibited in PDF/X-1a)
    if subtype in ("Type3", "/Type3"):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-012",
                severity=Severity.ERROR,
                message=f"Type 3 font '{base_font}' used (prohibited in PDF/X-1a)",
                page_num=page_num,
                iso_clause="ISO 15930-4:2003 6.3",
                object_id=font_name,
                object_type="font",
            )
        )
        return findings

    # PDFX1A-011: Font not embedded
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
                    inspection_id=f"{_PREFIX}-011",
                    severity=Severity.ERROR,
                    message=f"Font '{base_font}' is not embedded (required for PDF/X-1a)",
                    page_num=page_num,
                    iso_clause="ISO 15930-4:2003 6.3",
                    object_id=font_name,
                    object_type="font",
                )
            )
    else:
        # No font descriptor — check descendant for composite fonts
        descendant = font_dict.get("/DescendantFonts") or font_dict.get("DescendantFonts")
        if isinstance(descendant, list) and descendant:
            cid_font = descendant[0] if isinstance(descendant[0], dict) else {}
            cid_descriptor = cid_font.get("/FontDescriptor") or cid_font.get("FontDescriptor")
            if isinstance(cid_descriptor, dict):
                has_cid_file = (
                    cid_descriptor.get("/FontFile") is not None
                    or cid_descriptor.get("/FontFile2") is not None
                    or cid_descriptor.get("/FontFile3") is not None
                    or cid_descriptor.get("FontFile") is not None
                    or cid_descriptor.get("FontFile2") is not None
                    or cid_descriptor.get("FontFile3") is not None
                )
                if not has_cid_file:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-011",
                            severity=Severity.ERROR,
                            message=(
                                f"CID font '{base_font}' is not embedded (required for PDF/X-1a)"
                            ),
                            page_num=page_num,
                            iso_clause="ISO 15930-4:2003 6.3",
                            object_id=font_name,
                            object_type="font",
                        )
                    )

                # PDFX1A-014: CID font missing CIDSystemInfo
                cid_system_info = cid_font.get("/CIDSystemInfo") or cid_font.get("CIDSystemInfo")
                if cid_system_info is None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-014",
                            severity=Severity.WARNING,
                            message=f"CID font '{base_font}' missing /CIDSystemInfo",
                            page_num=page_num,
                            iso_clause="ISO 15930-4:2003 6.3",
                            object_id=font_name,
                            object_type="font",
                        )
                    )
            else:
                # PDFX1A-013: Font missing FontDescriptor
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-013",
                        severity=Severity.WARNING,
                        message=f"Font '{base_font}' missing /FontDescriptor",
                        page_num=page_num,
                        iso_clause="ISO 15930-4:2003 6.3",
                        object_id=font_name,
                        object_type="font",
                    )
                )
        else:
            # PDFX1A-013: Font missing FontDescriptor (simple font, no descendants)
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-013",
                    severity=Severity.WARNING,
                    message=f"Font '{base_font}' missing /FontDescriptor",
                    page_num=page_num,
                    iso_clause="ISO 15930-4:2003 6.3",
                    object_id=font_name,
                    object_type="font",
                )
            )

    # PDFX1A-014: CID font missing CIDSystemInfo (via direct descriptor)
    if isinstance(descriptor, dict):
        descendant = font_dict.get("/DescendantFonts") or font_dict.get("DescendantFonts")
        if isinstance(descendant, list) and descendant:
            cid_font = descendant[0] if isinstance(descendant[0], dict) else {}
            cid_system_info = cid_font.get("/CIDSystemInfo") or cid_font.get("CIDSystemInfo")
            if cid_system_info is None:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-014",
                        severity=Severity.WARNING,
                        message=f"CID font '{base_font}' missing /CIDSystemInfo",
                        page_num=page_num,
                        iso_clause="ISO 15930-4:2003 6.3",
                        object_id=font_name,
                        object_type="font",
                    )
                )

    # PDFX1A-015: Font missing encoding
    encoding = font_dict.get("/Encoding") or font_dict.get("Encoding")
    if encoding is None and subtype not in (
        "Type3",
        "/Type3",
        "Type0",
        "/Type0",
        "CIDFontType0",
        "/CIDFontType0",
        "CIDFontType2",
        "/CIDFontType2",
    ):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-015",
                severity=Severity.WARNING,
                message=f"Font '{base_font}' missing /Encoding",
                page_num=page_num,
                iso_clause="ISO 15930-4:2003 6.3",
                object_id=font_name,
                object_type="font",
            )
        )

    return findings
