"""Tests for PDF/X-4 page box checks (PDFX4-049-056)."""

from __future__ import annotations

from grounded.analyzers.finding import Severity
from grounded.conformance.pdfx4._boxes import validate_boxes
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc(pages: list[SemanticPage] | None = None) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=pages or [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestMediaBox:
    @staticmethod
    def test_mediabox_required() -> None:
        page = SemanticPage.__new__(SemanticPage)
        object.__setattr__(page, "page_num", 1)
        object.__setattr__(page, "media_box", None)
        object.__setattr__(page, "crop_box", None)
        object.__setattr__(page, "bleed_box", None)
        object.__setattr__(page, "trim_box", None)
        object.__setattr__(page, "art_box", None)
        object.__setattr__(page, "rotate", 0)
        object.__setattr__(page, "user_unit", 1.0)
        object.__setattr__(page, "fonts", {})
        object.__setattr__(page, "images", [])
        object.__setattr__(page, "color_spaces", {})
        object.__setattr__(page, "resources", {})
        object.__setattr__(page, "content_stream", b"")
        object.__setattr__(page, "annotations", [])
        object.__setattr__(page, "transparency_group", None)
        f = validate_boxes(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-049"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR


class TestTrimOrArtBox:
    @staticmethod
    def test_neither_trim_nor_art() -> None:
        page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
        f = validate_boxes(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-050"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_trim_present_ok() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(10, 10, 602, 782),
        )
        f = validate_boxes(_doc(pages=[page]))
        assert not [x for x in f if x.inspection_id == "PDFX4-050"]


class TestTrimArtConflict:
    @staticmethod
    def test_both_different_squall() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(10, 10, 602, 782),
            art_box=PdfBox(20, 20, 592, 772),
        )
        f = validate_boxes(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-051"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.WARNING

    @staticmethod
    def test_both_same_ok() -> None:
        box = PdfBox(10, 10, 602, 782)
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            trim_box=box,
            art_box=box,
        )
        f = validate_boxes(_doc(pages=[page]))
        assert not [x for x in f if x.inspection_id == "PDFX4-051"]


class TestBleedBoxNesting:
    @staticmethod
    def test_bleed_outside_media() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(-10, -10, 622, 802),
            trim_box=PdfBox(10, 10, 602, 782),
        )
        f = validate_boxes(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-052"]
        assert len(ids) == 1


class TestTrimBoxNesting:
    @staticmethod
    def test_trim_outside_bleed() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            bleed_box=PdfBox(20, 20, 592, 772),
            trim_box=PdfBox(10, 10, 602, 782),
        )
        f = validate_boxes(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-053"]
        assert len(ids) == 1


class TestCropBoxNesting:
    @staticmethod
    def test_crop_outside_media() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            crop_box=PdfBox(-5, -5, 620, 800),
            trim_box=PdfBox(10, 10, 602, 782),
        )
        f = validate_boxes(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-055"]
        assert len(ids) == 1


class TestArtBoxNesting:
    @staticmethod
    def test_art_outside_trim() -> None:
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            trim_box=PdfBox(20, 20, 592, 772),
            art_box=PdfBox(10, 10, 602, 782),
        )
        f = validate_boxes(_doc(pages=[page]))
        ids = [x for x in f if x.inspection_id == "PDFX4-056"]
        assert len(ids) == 1
