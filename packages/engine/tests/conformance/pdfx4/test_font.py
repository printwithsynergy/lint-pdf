"""Tests for PDF/X-4 font checks (PDFX4-036-042)."""

from __future__ import annotations

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
    @staticmethod
    def test_not_embedded_aground() -> None:
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

    @staticmethod
    def test_embedded_ok() -> None:
        fonts = {
            "/F1": {
                "/Subtype": "TrueType",
                "/BaseFont": "Arial",
                "/FontDescriptor": {"/FontFile2": b"binary"},
            }
        }
        f = validate_fonts(_doc(fonts))
        assert not [x for x in f if x.inspection_id == "PDFX4-036"]

    @staticmethod
    def test_cid_font_not_embedded() -> None:
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
    @staticmethod
    def test_truetype_missing_fontfile2() -> None:
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

    @staticmethod
    def test_truetype_fontfile3_opentype_ok() -> None:
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
    @staticmethod
    def test_type3_no_charprocs() -> None:
        fonts = {"/F1": {"/Subtype": "Type3", "/BaseFont": "Custom"}}
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-038"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.AGROUND

    @staticmethod
    def test_type3_with_charprocs_ok() -> None:
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
    @staticmethod
    def test_missing_cidtogidmap() -> None:
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

    @staticmethod
    def test_cidtogidmap_present_ok() -> None:
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
    @staticmethod
    def test_external_font_ref() -> None:
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
    @staticmethod
    def test_no_descriptor_squall() -> None:
        fonts = {"/F1": {"/Subtype": "Type1", "/BaseFont": "Helvetica"}}
        f = validate_fonts(_doc(fonts))
        ids = [x for x in f if x.inspection_id == "PDFX4-041"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.SQUALL

    @staticmethod
    def test_type3_no_descriptor_ok() -> None:
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
    @staticmethod
    def test_empty_font_program_aground() -> None:
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
