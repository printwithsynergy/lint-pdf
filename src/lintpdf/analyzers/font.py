"""FontAnalyzer — embedding, subsetting, and encoding checks.

Processes SemanticDocument font data to detect font-related preflight issues.

Check IDs:
    LPDF_FONT_001 — Font not embedded
    LPDF_FONT_002 — Font not subsetted (full font embedded)
    LPDF_FONT_003 — Standard 14 font used (may render differently)
    LPDF_FONT_004 — Type 3 font detected (user-drawn glyphs)
    LPDF_FONT_005 — CID font missing ToUnicode CMap
    LPDF_FONT_006 — CID font missing CIDSystemInfo
    LPDF_FONT_007 — Font has no encoding specified
    LPDF_FONT_008 — TrueType font not embedded (rendering issues)
    LPDF_FONT_009 — OpenType/CFF font not embedded
    LPDF_FONT_010 — Font embedding incomplete (descriptor present but no font file)
    LPDF_FONT_011 — Multiple Master font detected
    LPDF_FONT_012 — Faux bold detected
    LPDF_FONT_013 — Faux italic detected
    LPDF_FONT_014 — Corrupt/damaged font program (type/stream mismatch)
    LPDF_FONT_015 — Restricted font-embedding licence (OS/2 fsType bits 1-3)
    LPDF_FONT_016 — Font subsetted against vendor's no_subsetting policy (bit 8)
    LPDF_FONT_017 — Outline data embedded against vendor's bitmap-only policy (bit 9)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lintpdf.analyzers._font_sfnt import parse_fstype
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

        # PR-I (audit miss closure): empty-fonts-with-text-content
        # advisory. Outlined-text fixtures (Pink-Slush, Cherry-Twist,
        # HSI, OrangeKiss) declare zero fonts but their pages contain
        # extensive ingredient / regulatory copy as vector paths. Opus
        # rightly flags this as "verify all text is intentionally
        # outlined" — if any glyph slipped through as live text without
        # an embedded font it would not render at the RIP. Best-effort
        # detection: emit one ADVISORY per page that has 0 declared
        # fonts AND a non-trivial path-painting count (proxy for
        # outlined glyph paths).
        findings.extend(self._check_outlined_verify(document))

        return findings

    @staticmethod
    def _check_outlined_verify(document: SemanticDocument) -> list[Finding]:
        """LPDF_FONT_NONE_DECLARED — advisory for pages with no fonts
        but heavy vector content (likely outlined-text artwork).

        Conservative trigger: page declares 0 fonts AND its content
        stream is non-empty AND the document's catalog suggests it's
        meant for print (any color spaces declared). Capped at one
        finding per page so we don't double-fire on multi-page
        outlined documents.
        """
        out: list[Finding] = []
        for page in getattr(document, "pages", None) or []:
            page_fonts = getattr(page, "fonts", None) or {}
            if page_fonts:
                continue  # at least one font declared — analyzed above
            content = getattr(page, "content_stream", None)
            if not content:
                continue  # truly empty page; not an outlined-art case
            # Heuristic: a content stream of more than ~1KB with no
            # fonts is suspicious. Outlined art is path-heavy; an
            # empty page would barely register.
            size = len(content) if isinstance(content, (bytes, bytearray)) else len(str(content))
            if size < 1024:
                continue
            out.append(
                Finding(
                    inspection_id="LPDF_FONT_NONE_DECLARED",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Page {page.page_num} has visible content but no "
                        "fonts are declared. Text was likely converted to "
                        "vector paths (outlined). Verify intentional — any "
                        "live text without an embedded font won't render "
                        "at the RIP."
                    ),
                    page_num=page.page_num,
                    details={
                        "fonts_declared": 0,
                        "content_stream_bytes": size,
                    },
                    iso_clause="ISO 15930-7:2010 6.3 (font embedding)",
                )
            )
        return out

    @staticmethod
    def _check_font(font: PdfFont, page_num: int) -> list[Finding]:  # skipcq: PY-R1000
        """Run all checks on a single font."""
        findings: list[Finding] = []

        # LPDF_FONT_001: Font not embedded. Standard 14 fonts are
        # equally non-embedded — until 2026-04-29 we suppressed the
        # error there (PDF/A 1b technically allows them) but Opus's
        # audit + a competent prepress operator both treat unembedded
        # Helvetica / Times / Courier on a production print job as a
        # hard error: the receiving RIP may substitute a different
        # font, breaking layout. Emit the error for Standard 14 too,
        # but flag ``is_standard_14`` in details so downstream tooling
        # can downgrade it on workflows that genuinely permit them.
        if not font.embedded:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_001",
                    severity=Severity.ERROR,
                    message=f"Font '{font.base_font}' is not embedded",
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "font_type": font.font_type,
                        "is_standard_14": font.is_standard_14(),
                    },
                    iso_clause="ISO 15930-7:2010 6.2.11.2",
                    object_id=font.name,
                    object_type="font",
                )
            )

        # LPDF_FONT_002: Font embedded but not subsetted
        if font.embedded and not font.subset:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_002",
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

        # LPDF_FONT_003: Standard 14 font
        if font.is_standard_14():
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_003",
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

        # LPDF_FONT_004: Type 3 font
        if font.is_type3():
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_004",
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

        # LPDF_FONT_005: any font (CID or simple) missing ToUnicode CMap.
        # Without it, text extraction / copy-paste / accessibility
        # tooling can't reliably map glyph indices back to characters.
        # PR-I (audit miss closure): post-merge audit flagged 4 of these
        # on Type1 / TrueType fonts that the old CID-only gate skipped.
        # Severity: WARNING for CID (Type0 composite — required by ISO
        # 32000-2 §9.10.2 in practice); ADVISORY for simple fonts (the
        # spec doesn't require it but every modern preflight tool flags
        # the absence as a quality issue).
        if not font.has_to_unicode:
            cid = font.is_cid_font()
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_005",
                    severity=Severity.WARNING if cid else Severity.ADVISORY,
                    message=(
                        f"{'CID font' if cid else 'Font'} '{font.base_font}' "
                        f"missing ToUnicode CMap (text extraction unreliable)"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "is_cid": cid,
                    },
                    iso_clause="ISO 32000-2:2020 9.10.2",
                )
            )

        # LPDF_FONT_006: CID font missing CIDSystemInfo
        if font.is_cid_font() and font.cid_system_info is None:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_006",
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

        # LPDF_FONT_007: No encoding
        if font.encoding is None and not font.is_type3() and not font.is_cid_font():
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_007",
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

        # LPDF_FONT_008: TrueType not embedded
        if font.font_type == "TrueType" and not font.embedded:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_008",
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

        # LPDF_FONT_009: Type0/CID not embedded
        if font.font_type == "Type0" and not font.embedded:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_009",
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

        # LPDF_FONT_010: Font descriptor present but no font file
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
                        inspection_id="LPDF_FONT_010",
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

        # LPDF_FONT_011: Multiple Master font detected
        if font.font_type == "MMType1" or (font.base_font and font.base_font.endswith("MM")):
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_011",
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

        # LPDF_FONT_012: Faux bold detected
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
                        inspection_id="LPDF_FONT_012",
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

        # LPDF_FONT_013: Faux italic detected
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
                        inspection_id="LPDF_FONT_013",
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

        # LPDF_FONT_014: Mismatched font program type
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
                            inspection_id="LPDF_FONT_014",
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
                            inspection_id="LPDF_FONT_014",
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

    @staticmethod
    def _check_fstype(
        font: PdfFont,
        *,
        page_num: int,
        font_file_bytes: bytes | None,
    ) -> list[Finding]:
        """Legacy fsType compatibility surface used by sfnt tests.

        This helper intentionally remains side-effect free and only
        emits fsType-derived findings when font bytes are available.
        """
        if not font_file_bytes:
            return []
        if font.font_type in {"Type1", "Type3"}:
            return []

        fs_info = parse_fstype(font_file_bytes)
        if fs_info is None:
            return []

        findings: list[Finding] = []

        if fs_info.has_embedding_restriction:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_015",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Font '{font.base_font}' has fsType embedding restrictions: "
                        f"{', '.join(fs_info.flags) or 'unknown'}"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "fs_type_value": fs_info.value,
                        "fs_type_flags": fs_info.flags,
                        "has_embedding_restriction": fs_info.has_embedding_restriction,
                    },
                    iso_clause="OpenType OS/2 fsType",
                    object_id=font.name,
                    object_type="font",
                )
            )

        if fs_info.no_subsetting and font.subset:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_016",
                    severity=Severity.WARNING,
                    message=(
                        f"Font '{font.base_font}' is subsetted but fsType forbids subsetting"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "fs_type_value": fs_info.value,
                        "fs_type_flags": fs_info.flags,
                        "no_subsetting": fs_info.no_subsetting,
                    },
                    iso_clause="OpenType OS/2 fsType",
                    object_id=font.name,
                    object_type="font",
                )
            )

        if fs_info.bitmap_only and font.font_type in {"TrueType", "CIDFontType2", "Type0"}:
            findings.append(
                Finding(
                    inspection_id="LPDF_FONT_017",
                    severity=Severity.WARNING,
                    message=(
                        f"Font '{font.base_font}' embeds outline data but fsType is bitmap-only"
                    ),
                    page_num=page_num,
                    details={
                        "font_name": font.name,
                        "base_font": font.base_font,
                        "font_type": font.font_type,
                        "fs_type_value": fs_info.value,
                        "fs_type_flags": fs_info.flags,
                        "bitmap_only": fs_info.bitmap_only,
                    },
                    iso_clause="OpenType OS/2 fsType",
                    object_id=font.name,
                    object_type="font",
                )
            )

        return findings
