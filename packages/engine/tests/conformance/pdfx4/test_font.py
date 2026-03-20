"""Tests for PDF/X-4 font checks (PDFX4-036-042)."""

from __future__ import annotations

# skipcq: PYL-R0201
from typing import Any

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._font import validate_fonts
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(font_resources: dict[str, Any] | None = None) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        resources={"/Font": font_resources} if font_resources else {},
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


class TestFontEmbedding:
    def test_not_embedded_aground(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "TrueType",
                "/BaseFont": "Arial",
                "/FontDescriptor": {"/Flags": 32},  # No FontFile entries
            }
        }
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-036"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    def test_embedded_ok(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "TrueType",
                "/BaseFont": "Arial",
                "/FontDescriptor": {"/FontFile2": b"binary"},
            }
        }
        f = validate_fonts(_doc(fonts))
        assert not [x for x in f if x.inspection_id == "PDFX4-036"]

    def test_cid_font_not_embedded(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "Type0",
                "/BaseFont": "MSGothic",
                "/DescendantFonts": [
                    {
                        "/Subtype": "CIDFontType2",
                        "/FontDescriptor": {"/Flags": 32},  # No FontFile
                    }
                ],
            }
        }
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-036"]
        assert len(ids) == 1


class TestTrueTypeEmbedding:
    def test_truetype_missing_fontfile2(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "TrueType",
                "/BaseFont": "Arial",
                "/FontDescriptor": {"/FontFile": b"binary"},  # Wrong key for TT
            }
        }
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-037"]
        assert len(ids) == 1

    def test_truetype_fontfile3_opentype_ok(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "TrueType",
                "/BaseFont": "Arial",
                "/FontDescriptor": {"/FontFile3": b"binary"},
            }
        }
        f = validate_fonts(_doc(fonts))
        assert not [x for x in f if x.inspection_id == "PDFX4-037"]


class TestType3Font:
    def test_type3_no_charprocs(self) -> None:
        fonts = {"/F1": {"/Subtype": "Type3", "/BaseFont": "Custom"}}
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-038"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    def test_type3_with_charprocs_ok(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "Type3",
                "/BaseFont": "Custom",
                "/CharProcs": {"/a": b"stream"},
            }
        }
        f = validate_fonts(_doc(fonts))
        assert not [x for x in f if x.inspection_id == "PDFX4-038"]


class TestCIDToGIDMap:
    def test_missing_cidtogidmap(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "Type0",
                "/BaseFont": "MSGothic",
                "/DescendantFonts": [
                    {
                        "/Subtype": "CIDFontType2",
                        "/FontDescriptor": {"/FontFile2": b"binary"},
                    }
                ],
            }
        }
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-039"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    def test_cidtogidmap_present_ok(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "Type0",
                "/BaseFont": "MSGothic",
                "/DescendantFonts": [
                    {
                        "/Subtype": "CIDFontType2",
                        "/CIDToGIDMap": "Identity",
                        "/FontDescriptor": {"/FontFile2": b"binary"},
                    }
                ],
            }
        }
        f = validate_fonts(_doc(fonts))
        assert not [x for x in f if x.inspection_id == "PDFX4-039"]


class TestExternalRef:
    def test_external_font_ref(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "Type1",
                "/BaseFont": "Helvetica",
                "/FontDescriptor": {"/FontFile3": {"/F": "/path/to/font.pfa", "/Length": 100}},
            }
        }
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-040"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND


class TestMissingDescriptor:
    def test_no_descriptor_squall(self) -> None:
        fonts = {"/F1": {"/Subtype": "Type1", "/BaseFont": "Helvetica"}}
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-041"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    def test_type3_no_descriptor_ok(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "Type3",
                "/BaseFont": "Custom",
                "/CharProcs": {"/a": b"s"},
            }
        }
        f = validate_fonts(_doc(fonts))
        assert not [x for x in f if x.inspection_id == "PDFX4-041"]


class TestEmptyFontProgram:
    def test_empty_font_program_aground(self) -> None:
        fonts = {
            "/F1": {
                "/Subtype": "Type1",
                "/BaseFont": "Helvetica",
                "/FontDescriptor": {"/FontFile": {"/Length": 0}},
            }
        }
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-042"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND
