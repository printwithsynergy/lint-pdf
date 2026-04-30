"""Tests for PDF/X-4 annotation checks (PDFX4-057-062)."""

from __future__ import annotations

from siftpdf.analyzers.finding import Severity
from siftpdf.conformance.pdfx4._annotations import validate_annotations
from siftpdf.semantic.model import PdfAnnotation, PdfBox, SemanticDocument, SemanticPage


def _doc(annotations: list[PdfAnnotation] | None = None) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        annotations=annotations or [],
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


class TestProhibitedAnnotations:
    @staticmethod
    def test_sound_no_fly() -> None:
        f = validate_annotations(_doc([PdfAnnotation(subtype="Sound", page_num=1)]))
        ids = [x for x in f if x.inspection_id == "PDFX4-057"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_movie_no_fly() -> None:
        f = validate_annotations(_doc([PdfAnnotation(subtype="Movie", page_num=1)]))
        ids = [x for x in f if x.inspection_id == "PDFX4-058"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_3d_no_fly() -> None:
        f = validate_annotations(_doc([PdfAnnotation(subtype="3D", page_num=1)]))
        ids = [x for x in f if x.inspection_id == "PDFX4-059"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_richmedia_no_fly() -> None:
        f = validate_annotations(_doc([PdfAnnotation(subtype="RichMedia", page_num=1)]))
        ids = [x for x in f if x.inspection_id == "PDFX4-060"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ERROR

    @staticmethod
    def test_screen_no_fly() -> None:
        f = validate_annotations(_doc([PdfAnnotation(subtype="Screen", page_num=1)]))
        ids = [x for x in f if x.inspection_id == "PDFX4-060"]
        assert len(ids) == 1

    @staticmethod
    def test_link_ok() -> None:
        f = validate_annotations(_doc([PdfAnnotation(subtype="Link", page_num=1)]))
        # Link annotations are allowed in PDF/X-4
        prohibited = [
            x for x in f if x.inspection_id in ("PDFX4-057", "PDFX4-058", "PDFX4-059", "PDFX4-060")
        ]
        assert len(prohibited) == 0


class TestPrinterMark:
    @staticmethod
    def test_printermark_not_printable() -> None:
        annot = PdfAnnotation(subtype="PrinterMark", page_num=1, flags=0)
        f = validate_annotations(_doc([annot]))
        ids = [x for x in f if x.inspection_id == "PDFX4-061"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY

    @staticmethod
    def test_printermark_printable_ok() -> None:
        annot = PdfAnnotation(subtype="PrinterMark", page_num=1, flags=0x04)
        f = validate_annotations(_doc([annot]))
        assert not [x for x in f if x.inspection_id == "PDFX4-061"]


class TestTrapNet:
    @staticmethod
    def test_trapnet_advisory() -> None:
        annot = PdfAnnotation(subtype="TrapNet", page_num=1)
        f = validate_annotations(_doc([annot]))
        ids = [x for x in f if x.inspection_id == "PDFX4-062"]
        assert len(ids) == 1
        assert ids[0].severity == Severity.ADVISORY


class TestNoAnnotations:
    @staticmethod
    def test_empty_annotations_ok() -> None:
        f = validate_annotations(_doc())
        assert len(f) == 0
