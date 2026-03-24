"""Tests for PDF/X-4 resource checks (PDFX4-088-092)."""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.conformance.pdfx4._resources import validate_resources
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(pages: list[SemanticPage] | None = None) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=pages or [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestNullXObject:
    @staticmethod
    def test_null_xobject_aground() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/XObject": {"/Im1": None}},
        )
        f = validate_resources(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-088"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_valid_xobject_ok() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/XObject": {"/Im1": {"/Subtype": "/Image"}}},
        )
        f = validate_resources(_doc(pages=[page]))
        assert not [x for x in f if x.inspection_id == "PDFX4-088"]


class TestNullFont:
    @staticmethod
    def test_null_font_aground() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/Font": {"/F1": None}},
        )
        f = validate_resources(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-089"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR


class TestNullColorSpace:
    @staticmethod
    def test_null_colorspace_aground() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ColorSpace": {"/CS1": None}},
        )
        f = validate_resources(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-090"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR


class TestNullExtGState:
    @staticmethod
    def test_null_extgstate_aground() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            resources={"/ExtGState": {"/GS1": None}},
        )
        f = validate_resources(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-091"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR


class TestResourcePresence:
    @staticmethod
    def test_content_no_resources_advisory() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            content_stream=b"BT /F1 12 Tf ET",
        )
        f = validate_resources(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-092"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    @staticmethod
    def test_no_content_no_finding() -> None:
        page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
        f = validate_resources(_doc(pages=[page]))
        assert not [x for x in f if x.inspection_id == "PDFX4-092"]
