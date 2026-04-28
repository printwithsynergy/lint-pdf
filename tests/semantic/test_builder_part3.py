"""Tests for Part 3 builder additions — annotations, transparency group, trailer."""

from __future__ import annotations

from unittest.mock import MagicMock

from lintpdf.parser.adapter import PdfDocument, PdfPage
from lintpdf.semantic.builder import SemanticModelBuilder


def _make_adapter() -> MagicMock:
    """Create a mock ParserAdapter."""
    adapter = MagicMock()
    adapter.get_resources.return_value = {}
    adapter.get_content_stream.return_value = b""
    adapter.get_page_parent_chain.return_value = []
    return adapter


def _make_page(
    page_num: int = 1,
    page_dict: dict | None = None,
) -> PdfPage:
    return PdfPage(
        page_num=page_num,
        page_dict=page_dict or {},
        media_box=(0, 0, 612, 792),
    )


def _make_document(
    pages: list[PdfPage] | None = None,
    trailer: dict | None = None,
) -> PdfDocument:
    page_list = pages or [_make_page()]
    return PdfDocument(
        version="1.7",
        page_count=len(page_list),
        is_encrypted=False,
        pages=page_list,
        trailer=trailer or {},
    )


class TestTrailerThreading:
    """Test that trailer is threaded from PdfDocument to SemanticDocument."""

    @staticmethod
    def test_trailer_passed_through() -> None:
        adapter = _make_adapter()
        builder = SemanticModelBuilder(adapter)
        trailer = {"/Size": 42, "/ID": ["abc", "def"]}
        doc = _make_document(trailer=trailer)
        sem_doc = builder.build(doc)
        assert sem_doc.trailer == trailer

    @staticmethod
    def test_empty_trailer() -> None:
        adapter = _make_adapter()
        builder = SemanticModelBuilder(adapter)
        doc = _make_document()
        sem_doc = builder.build(doc)
        assert sem_doc.trailer == {}


class TestAnnotationExtraction:
    """Test annotation extraction from page dict."""

    @staticmethod
    def test_no_annots() -> None:
        adapter = _make_adapter()
        builder = SemanticModelBuilder(adapter)
        doc = _make_document()
        sem_doc = builder.build(doc)
        assert sem_doc.pages[0].annotations == []

    @staticmethod
    def test_annots_extracted() -> None:
        adapter = _make_adapter()
        adapter.get_resources.return_value = {}

        page_dict = {
            "/Annots": [
                {"/Subtype": "/Text", "/Rect": [10, 20, 100, 50], "/F": 4},
                {"/Subtype": "/Link", "/Rect": [0, 0, 200, 30]},
            ]
        }
        page = _make_page(page_dict=page_dict)
        doc = _make_document(pages=[page])
        builder = SemanticModelBuilder(adapter)
        sem_doc = builder.build(doc)

        annots = sem_doc.pages[0].annotations
        assert len(annots) == 2
        assert annots[0].subtype == "Text"
        assert annots[0].is_printable is True
        assert annots[0].rect is not None
        assert annots[0].rect.x0 == 10
        assert annots[1].subtype == "Link"
        assert annots[1].is_printable is False

    @staticmethod
    def test_annot_with_swapped_rect() -> None:
        """Rects with inverted coordinates should be normalized."""
        adapter = _make_adapter()
        page_dict = {
            "/Annots": [
                {"/Subtype": "/Text", "/Rect": [100, 50, 10, 20]},
            ]
        }
        page = _make_page(page_dict=page_dict)
        doc = _make_document(pages=[page])
        builder = SemanticModelBuilder(adapter)
        sem_doc = builder.build(doc)

        annot = sem_doc.pages[0].annotations[0]
        assert annot.rect is not None
        assert annot.rect.x0 == 10
        assert annot.rect.x1 == 100

    @staticmethod
    def test_annot_without_subtype_skipped() -> None:
        adapter = _make_adapter()
        page_dict = {
            "/Annots": [
                {"/Rect": [0, 0, 100, 100]},  # No /Subtype
            ]
        }
        page = _make_page(page_dict=page_dict)
        doc = _make_document(pages=[page])
        builder = SemanticModelBuilder(adapter)
        sem_doc = builder.build(doc)
        assert sem_doc.pages[0].annotations == []

    @staticmethod
    def test_annot_with_contents() -> None:
        adapter = _make_adapter()
        page_dict = {
            "/Annots": [
                {"/Subtype": "/FreeText", "/Contents": "Hello world"},
            ]
        }
        page = _make_page(page_dict=page_dict)
        doc = _make_document(pages=[page])
        builder = SemanticModelBuilder(adapter)
        sem_doc = builder.build(doc)
        assert sem_doc.pages[0].annotations[0].contents == "Hello world"


class TestTransparencyGroupExtraction:
    """Test transparency group extraction from page dict."""

    @staticmethod
    def test_no_group() -> None:
        adapter = _make_adapter()
        builder = SemanticModelBuilder(adapter)
        doc = _make_document()
        sem_doc = builder.build(doc)
        assert sem_doc.pages[0].transparency_group is None

    @staticmethod
    def test_transparency_group_extracted() -> None:
        adapter = _make_adapter()
        page_dict = {
            "/Group": {
                "/S": "/Transparency",
                "/CS": "/DeviceCMYK",
                "/I": True,
                "/K": False,
            }
        }
        page = _make_page(page_dict=page_dict)
        doc = _make_document(pages=[page])
        builder = SemanticModelBuilder(adapter)
        sem_doc = builder.build(doc)

        group = sem_doc.pages[0].transparency_group
        assert group is not None
        assert group["/CS"] == "/DeviceCMYK"
        assert group["/I"] is True

    @staticmethod
    def test_non_transparency_group_ignored() -> None:
        adapter = _make_adapter()
        page_dict = {
            "/Group": {"/S": "/SomeOtherType"},
        }
        page = _make_page(page_dict=page_dict)
        doc = _make_document(pages=[page])
        builder = SemanticModelBuilder(adapter)
        sem_doc = builder.build(doc)
        assert sem_doc.pages[0].transparency_group is None
