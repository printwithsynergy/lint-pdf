"""PDF/A font checks (PDFA-019-025).

Validates font embedding and structure requirements per ISO 19005.
All fonts must be embedded with ToUnicode CMaps for text extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.semantic.model import SemanticDocument

_PREFIX = "PDFA"


def validate_fonts(document: SemanticDocument, level: str) -> list[Finding]:
    """Run font conformance checks."""
    findings: list[Finding] = []

    for page in document.pages:
        font_resources = page.resources.get("/Font") or page.resources.get("Font")
        if not isinstance(font_resources, dict):
            continue

        for font_name, font_dict in font_resources.items():
            if not isinstance(font_dict, dict):
                continue

            findings.extend(_check_font(font_name, font_dict, page.page_num, level))

    return findings


def _check_font(  # skipcq: PY-R1000
    font_name: str, font_dict: dict[str, Any], page_num: int, level: str
) -> list[Finding]:
    """Check a single font dictionary for PDF/A compliance."""
    findings: list[Finding] = []

    subtype = font_dict.get("/Subtype") or font_dict.get("Subtype") or ""
    base_font = font_dict.get("/BaseFont") or font_dict.get("BaseFont") or font_name
    descriptor = font_dict.get("/FontDescriptor") or font_dict.get("FontDescriptor")

    # PDFA-022: Type 3 font used (prohibited in PDF/A-1)
    if subtype in ("Type3", "/Type3"):
        if level.startswith("1"):
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-022",
                    severity=Severity.ERROR,
                    message=f"Type 3 font '{base_font}' used (prohibited in PDF/A-1)",
                    page_num=page_num,
                    iso_clause="ISO 19005-1 6.3.5",
                    object_id=font_name,
                    object_type="font",
                )
            )
        return findings

    # PDFA-019: Font not embedded
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
                    inspection_id=f"{_PREFIX}-019",
                    severity=Severity.ERROR,
                    message=f"Font '{base_font}' is not embedded (required for PDF/A)",
                    page_num=page_num,
                    iso_clause="ISO 19005 6.3.3",
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
                            inspection_id=f"{_PREFIX}-019",
                            severity=Severity.ERROR,
                            message=(
                                f"CID font '{base_font}' is not embedded "
                                f"(required for PDF/A)"
                            ),
                            page_num=page_num,
                            iso_clause="ISO 19005 6.3.3",
                            object_id=font_name,
                            object_type="font",
                        )
                    )

                # PDFA-023: CID font missing CIDToGIDMap
                cid_to_gid = cid_font.get("/CIDToGIDMap") or cid_font.get("CIDToGIDMap")
                if cid_to_gid is None:
                    findings.append(
                        Finding(
                            inspection_id=f"{_PREFIX}-023",
                            severity=Severity.WARNING,
                            message=f"CID font '{base_font}' missing /CIDToGIDMap",
                            page_num=page_num,
                            iso_clause="ISO 19005 6.3.5",
                            object_id=font_name,
                            object_type="font",
                        )
                    )

    # PDFA-020: Font missing ToUnicode CMap (required for text extraction)
    to_unicode = font_dict.get("/ToUnicode") or font_dict.get("ToUnicode")
    # ToUnicode not required for symbolic fonts, Type 1 with standard encoding,
    # or CID fonts with certain CMap names. Check for simple/TrueType fonts mainly.
    if to_unicode is None and subtype not in (
        "Type0", "/Type0",
        "CIDFontType0", "/CIDFontType0",
        "CIDFontType2", "/CIDFontType2",
    ):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-020",
                severity=Severity.WARNING,
                message=(
                    f"Font '{base_font}' missing /ToUnicode CMap "
                    f"(required for text extraction in PDF/A)"
                ),
                page_num=page_num,
                iso_clause="ISO 19005 6.3.6",
                object_id=font_name,
                object_type="font",
            )
        )

    # PDFA-021: Font missing /Widths array
    widths = font_dict.get("/Widths") or font_dict.get("Widths")
    if widths is None and subtype not in (
        "Type0", "/Type0",
        "CIDFontType0", "/CIDFontType0",
        "CIDFontType2", "/CIDFontType2",
        "Type3", "/Type3",
    ):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-021",
                severity=Severity.WARNING,
                message=f"Font '{base_font}' missing /Widths array",
                page_num=page_num,
                iso_clause="ISO 19005 6.3.4",
                object_id=font_name,
                object_type="font",
            )
        )

    # PDFA-024: Font missing encoding
    encoding = font_dict.get("/Encoding") or font_dict.get("Encoding")
    if encoding is None and subtype not in (
        "Type3", "/Type3",
        "Type0", "/Type0",
        "CIDFontType0", "/CIDFontType0",
        "CIDFontType2", "/CIDFontType2",
    ):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-024",
                severity=Severity.WARNING,
                message=f"Font '{base_font}' missing /Encoding",
                page_num=page_num,
                iso_clause="ISO 19005 6.3.3",
                object_id=font_name,
                object_type="font",
            )
        )

    # PDFA-025: TrueType font missing required tables
    if subtype in ("TrueType", "/TrueType") and isinstance(descriptor, dict):
        # Check for required TrueType tables in FontFile2
        font_file2 = descriptor.get("/FontFile2") or descriptor.get("FontFile2")
        if isinstance(font_file2, dict):
            # Check metadata hints about missing tables
            missing_tables = font_file2.get("/MissingTables") or font_file2.get("MissingTables")
            if missing_tables:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-025",
                        severity=Severity.WARNING,
                        message=(
                            f"TrueType font '{base_font}' missing required tables: "
                            f"{missing_tables}"
                        ),
                        page_num=page_num,
                        iso_clause="ISO 19005 6.3.5",
                        object_id=font_name,
                        object_type="font",
                    )
                )

    return findings
