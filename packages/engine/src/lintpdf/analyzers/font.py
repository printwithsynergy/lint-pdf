"""FontAnalyzer — embedding, subsetting, and encoding checks.

Processes SemanticDocument font data to detect font-related preflight issues.

Check IDs:
    GRD_FONT_001 — Font not embedded
    GRD_FONT_002 — Font not subsetted (full font embedded)
    GRD_FONT_003 — Standard 14 font used (may render differently)
    GRD_FONT_004 — Type 3 font detected (user-drawn glyphs)
    GRD_FONT_005 — CID font missing ToUnicode CMap
    GRD_FONT_006 — CID font missing CIDSystemInfo
    GRD_FONT_007 — Font has no encoding specified
    GRD_FONT_008 — TrueType font not embedded (rendering issues)
    GRD_FONT_009 — OpenType/CFF font not embedded
    GRD_FONT_010 — Font embedding incomplete (descriptor present but no font file)
    GRD_FONT_011 — Multiple Master font detected
    GRD_FONT_012 — Faux bold detected
    GRD_FONT_013 — Faux italic detected
    GRD_FONT_014 — Corrupt/damaged font program (type/stream mismatch)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import PdfFont, SemanticDocument


class FontAnalyzer(BaseAnalyzer):
    """Analyzer for font embedding, subsetting, and encoding issues."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        """Analyze all fonts across all pages."""
        findings: list[Finding] = []
        seen_fonts: set[str] = set()

        for page in document.pages:
            for font_name, font in page.fonts.items():
                # Deduplicate by base_font to avoid reporting the same font
                # on every page it appears
                font_key = font.base_font or font_name
                if font_key in seen_fonts:
                    continue
                seen_fonts.add(font_key)

                findings.extend(self._check_font(font, page.page_num))

        return findings

    @staticmethod
    def _check_font(font: PdfFont, page_num: int) -> list[Finding]:  # skipcq: PY-R1000
        """Run all checks on a single font."""
        findings: list[Finding] = []

        # GRD_FONT_001: Font not embedded (skip Standard 14)
        if not font.embedded and not font.is_standard_14():
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_001",
                    severity=Severity.ERROR,
                    message=f"Font '{font.base_font}' is not embedded",
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "font_type": font.font_type,
                    },
                    iso_clause="ISO 15930-7:2010 6.2.11.2",
                    object_id=font.name,
                    object_type="font",
                )
            )

        # GRD_FONT_002: Font embedded but not subsetted
        if font.embedded and not font.subset:
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_002",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Font '{font.base_font}' is fully embedded "
                        f"(not subsetted — increases file size)"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                    },
                    iso_clause="ISO 32000-2:2020 9.9",
                )
            )

        # GRD_FONT_003: Standard 14 font
        if font.is_standard_14():
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_003",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Standard 14 font '{font.base_font}' used "
                        f"(rendering may vary across viewers)"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                    },
                    iso_clause="ISO 32000-2:2020 9.6.2.2",
                )
            )

        # GRD_FONT_004: Type 3 font
        if font.is_type3():
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_004",
                    severity=Severity.WARNING,
                    message=(
                        f"Type 3 font '{font.base_font}' detected "
                        f"(user-drawn glyphs — may not render correctly)"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                    },
                    iso_clause="ISO 32000-2:2020 9.6.5",
                )
            )

        # CID font checks
        if font.is_cid_font():
            # GRD_FONT_005: CID font missing ToUnicode
            if not font.has_to_unicode:
                findings.append(
                    Finding(
                        inspection_id="GRD_FONT_005",
                        severity=Severity.WARNING,
                        message=(
                            f"CID font '{font.base_font}' missing "
                            f"ToUnicode CMap (text extraction unreliable)"
                        ),
                        page_num=page_num,
                        details={
                            "font_name": font.name,
                            "base_font": font.base_font,
                        },
                        iso_clause="ISO 32000-2:2020 9.10.2",
                    )
                )

            # GRD_FONT_006: CID font missing CIDSystemInfo
            if font.cid_system_info is None:
                findings.append(
                    Finding(
                        inspection_id="GRD_FONT_006",
                        severity=Severity.WARNING,
                        message=(f"CID font '{font.base_font}' missing CIDSystemInfo dictionary"),
                        page_num=page_num,
                        details={
                            "font_name": font.name,
                            "base_font": font.base_font,
                        },
                        iso_clause="ISO 32000-2:2020 9.7.4",
                    )
                )

        # GRD_FONT_007: No encoding
        if font.encoding is None and not font.is_type3() and not font.is_cid_font():
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_007",
                    severity=Severity.ADVISORY,
                    message=(f"Font '{font.base_font}' has no encoding specified"),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "font_type": font.font_type,
                    },
                    iso_clause="ISO 32000-2:2020 9.6.1",
                )
            )

        # GRD_FONT_008: TrueType not embedded
        if font.font_type == "TrueType" and not font.embedded:
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_008",
                    severity=Severity.ERROR,
                    message=(
                        f"TrueType font '{font.base_font}' is not embedded "
                        f"(will cause rendering failures)"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                    },
                    iso_clause="ISO 15930-7:2010 6.2.11.2",
                )
            )

        # GRD_FONT_009: Type0/CID not embedded
        if font.font_type == "Type0" and not font.embedded:
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_009",
                    severity=Severity.ERROR,
                    message=(f"Composite font '{font.base_font}' is not embedded"),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                    },
                    iso_clause="ISO 15930-7:2010 6.2.11.2",
                )
            )

        # GRD_FONT_010: Font descriptor present but no font file
        if (
            font.font_descriptor is not None
            and not font.embedded
            and not font.is_standard_14()
            and not font.is_type3()
        ):
            has_descriptor_but_no_file = (
                font.font_descriptor.get("FontFile") is None
                and font.font_descriptor.get("FontFile2") is None
                and font.font_descriptor.get("FontFile3") is None
            )
            if has_descriptor_but_no_file:
                findings.append(
                    Finding(
                        inspection_id="GRD_FONT_010",
                        severity=Severity.WARNING,
                        message=(
                            f"Font '{font.base_font}' has FontDescriptor "
                            f"but no embedded font program"
                        ),
                        page_num=page_num,
                        details={
                            "font_name": font.name,
                            "base_font": font.base_font,
                        },
                        iso_clause="ISO 32000-2:2020 9.8",
                    )
                )

        # GRD_FONT_011: Multiple Master font detected
        if font.font_type == "MMType1" or (font.base_font and font.base_font.endswith("MM")):
            findings.append(
                Finding(
                    inspection_id="GRD_FONT_011",
                    severity=Severity.WARNING,
                    message=(
                        f"Multiple Master font '{font.base_font}' detected "
                        f"(may not render correctly in all RIPs)"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "font_type": font.font_type,
                    },
                    iso_clause="ISO 32000-2:2020 9.6.2.3",
                    object_id=font.name,
                    object_type="font",
                )
            )

        # GRD_FONT_012: Faux bold detected
        if font.font_descriptor is not None:
            weight = font.font_descriptor.get("/FontWeight")
            stem_v = font.font_descriptor.get("/StemV")
            base_lower = (font.base_font or "").lower()
            if (
                (weight is not None and weight >= 700) or (stem_v is not None and stem_v > 165)
            ) and "bold" not in base_lower:
                display_weight = weight if weight is not None else f"StemV={stem_v}"
                findings.append(
                    Finding(
                        inspection_id="GRD_FONT_012",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Font '{font.base_font}' appears to use faux bold "
                            f"(font weight {display_weight} without bold variant)"
                        ),
                        page_num=page_num,
                        details={
                            "font_name": font.name,
                            "base_font": font.base_font,
                            "font_weight": weight,
                            "stem_v": stem_v,
                        },
                        iso_clause="ISO 32000-2:2020 9.8",
                    )
                )

        # GRD_FONT_013: Faux italic detected
        if font.font_descriptor is not None:
            italic_angle = font.font_descriptor.get("/ItalicAngle")
            base_lower = (font.base_font or "").lower()
            if (
                italic_angle is not None
                and abs(italic_angle) > 0
                and "italic" not in base_lower
                and "oblique" not in base_lower
            ):
                findings.append(
                    Finding(
                        inspection_id="GRD_FONT_013",
                        severity=Severity.ADVISORY,
                        message=(
                            f"Font '{font.base_font}' appears to use faux italic "
                            f"(ItalicAngle {italic_angle}\u00b0 without italic variant)"
                        ),
                        page_num=page_num,
                        details={
                            "font_name": font.name,
                            "base_font": font.base_font,
                            "italic_angle": italic_angle,
                        },
                        iso_clause="ISO 32000-2:2020 9.8",
                    )
                )

        # GRD_FONT_014: Mismatched font program type
        if font.embedded and font.font_descriptor is not None:
            font_file = font.font_descriptor.get("FontFile")
            font_file2 = font.font_descriptor.get("FontFile2")
            font_file3 = font.font_descriptor.get("FontFile3")
            has_any_file = font_file is not None or font_file2 is not None or font_file3 is not None
            if has_any_file:
                if font.font_type == "Type1" and font_file is None:
                    found_stream = "FontFile2" if font_file2 is not None else "FontFile3"
                    findings.append(
                        Finding(
                            inspection_id="GRD_FONT_014",
                            severity=Severity.WARNING,
                            message=(
                                f"Font '{font.base_font}' has mismatched font program type "
                                f"(expected FontFile, found {found_stream})"
                            ),
                            page_num=page_num,
                            details={
                                "font_name": font.name,
                                "base_font": font.base_font,
                                "font_type": font.font_type,
                                "expected": "FontFile",
                                "found": found_stream,
                            },
                            iso_clause="ISO 32000-2:2020 9.9",
                        )
                    )
                elif font.font_type == "TrueType" and font_file2 is None:
                    found_stream = "FontFile" if font_file is not None else "FontFile3"
                    findings.append(
                        Finding(
                            inspection_id="GRD_FONT_014",
                            severity=Severity.WARNING,
                            message=(
                                f"Font '{font.base_font}' has mismatched font program type "
                                f"(expected FontFile2, found {found_stream})"
                            ),
                            page_num=page_num,
                            details={
                                "font_name": font.name,
                                "base_font": font.base_font,
                                "font_type": font.font_type,
                                "expected": "FontFile2",
                                "found": found_stream,
                            },
                            iso_clause="ISO 32000-2:2020 9.9",
                        )
                    )

        return findings
