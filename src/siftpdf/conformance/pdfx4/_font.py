"""PDF/X-4 font checks (PDFX4-036-042).

Validates font embedding requirements per ISO 15930-7:2010 section 6.3.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from siftpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from siftpdf.semantic.model import SemanticDocument

_PREFIX = "PDFX4"


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
    """Check a single font dictionary for PDF/X-4 compliance."""
    findings: list[Finding] = []

    subtype = font_dict.get("/Subtype") or font_dict.get("Subtype") or ""
    base_font = font_dict.get("/BaseFont") or font_dict.get("BaseFont") or font_name
    descriptor = font_dict.get("/FontDescriptor") or font_dict.get("FontDescriptor")

    # PDFX4-036: All fonts must be embedded
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
                    inspection_id=f"{_PREFIX}-036",
                    severity=Severity.ERROR,
                    message=f"Font '{base_font}' is not embedded (required for PDF/X-4)",
                    page_num=page_num,
                    iso_clause="ISO 15930-7:2010 6.3",
                    object_id=font_name,
                    object_type="font",
                )
            )
    elif subtype != "Type3":
        # No font descriptor and not Type3 — likely not embedded
        # Type0 composite fonts have descriptors on descendant CIDFont
        descendant = font_dict.get("/DescendantFonts") or font_dict.get("DescendantFonts")
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
                            inspection_id=f"{_PREFIX}-036",
                            severity=Severity.ERROR,
                            message=f"CID font '{base_font}' is not embedded",
                            page_num=page_num,
                            iso_clause="ISO 15930-7:2010 6.3",
                            object_id=font_name,
                            object_type="font",
                        )
                    )

    # PDFX4-037: TrueType must be fully embedded (not subset if possible)
    # In practice, subsetting is acceptable. We check that the font file exists.
    if subtype in ("TrueType", "/TrueType") and isinstance(descriptor, dict):
        has_ttf = (
            descriptor.get("/FontFile2") is not None or descriptor.get("FontFile2") is not None
        )
        if not has_ttf:
            # Might use FontFile3 for OpenType
            has_otf = (
                descriptor.get("/FontFile3") is not None or descriptor.get("FontFile3") is not None
            )
            if not has_otf:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-037",
                        severity=Severity.ERROR,
                        message=f"TrueType font '{base_font}' font program missing",
                        page_num=page_num,
                        iso_clause="ISO 15930-7:2010 6.3.2",
                        object_id=font_name,
                        object_type="font",
                    )
                )

    # PDFX4-038: Type3 fonts must be self-contained
    if subtype in ("Type3", "/Type3"):
        char_procs = font_dict.get("/CharProcs") or font_dict.get("CharProcs")
        if not isinstance(char_procs, dict) or not char_procs:
            findings.append(
                Finding(
                    inspection_id=f"{_PREFIX}-038",
                    severity=Severity.ERROR,
                    message=f"Type3 font '{base_font}' has no /CharProcs",
                    page_num=page_num,
                    iso_clause="ISO 15930-7:2010 6.3.3",
                    object_id=font_name,
                    object_type="font",
                )
            )

    # PDFX4-039: CIDToGIDMap required for CIDFont with TrueType outlines
    descendant = font_dict.get("/DescendantFonts") or font_dict.get("DescendantFonts")
    if isinstance(descendant, list) and descendant:
        cid_font = descendant[0] if isinstance(descendant[0], dict) else {}
        cid_subtype = cid_font.get("/Subtype") or cid_font.get("Subtype") or ""
        if cid_subtype in ("CIDFontType2", "/CIDFontType2"):
            gid_map = cid_font.get("/CIDToGIDMap") or cid_font.get("CIDToGIDMap")
            if gid_map is None:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-039",
                        severity=Severity.WARNING,
                        message=f"CIDFontType2 '{base_font}' missing /CIDToGIDMap",
                        page_num=page_num,
                        iso_clause="ISO 15930-7:2010 6.3.4",
                        object_id=font_name,
                        object_type="font",
                    )
                )

    # PDFX4-040: No external font references
    if isinstance(descriptor, dict):
        font_file3 = descriptor.get("/FontFile3") or descriptor.get("FontFile3")
        if isinstance(font_file3, dict):
            ref = font_file3.get("/F") or font_file3.get("F")
            if ref is not None:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-040",
                        severity=Severity.ERROR,
                        message=f"Font '{base_font}' has external file reference",
                        page_num=page_num,
                        iso_clause="ISO 15930-7:2010 6.3",
                        object_id=font_name,
                        object_type="font",
                    )
                )

    # PDFX4-041: FontDescriptor present (for non-Type3)
    if (
        subtype not in ("Type3", "/Type3")
        and descriptor is None
        and not (isinstance(descendant, list) and descendant)
    ):
        findings.append(
            Finding(
                inspection_id=f"{_PREFIX}-041",
                severity=Severity.WARNING,
                message=f"Font '{base_font}' missing /FontDescriptor",
                page_num=page_num,
                iso_clause="ISO 32000-2:2020 9.8",
                object_id=font_name,
                object_type="font",
            )
        )

    # PDFX4-042: Font program valid (basic check — program bytes exist)
    if isinstance(descriptor, dict):
        for key in ("/FontFile", "/FontFile2", "/FontFile3"):
            font_file = descriptor.get(key)
            if isinstance(font_file, dict) and font_file.get("/Length", 0) == 0:
                findings.append(
                    Finding(
                        inspection_id=f"{_PREFIX}-042",
                        severity=Severity.ERROR,
                        message=f"Font '{base_font}' has empty font program ({key})",
                        page_num=page_num,
                        iso_clause="ISO 15930-7:2010 6.3",
                        object_id=font_name,
                        object_type="font",
                    )
                )

    return findings
