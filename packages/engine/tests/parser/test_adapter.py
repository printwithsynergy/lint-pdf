"""Tests for ParserAdapter ABC — verify interface contract."""

from __future__ import annotations

# skipcq: PYL-R0201
import pytest

from grounded.parser.adapter import (
    ParserAdapter,
    PdfDocument,
    PdfObject,
    PdfPage,
    PdfStream,
)


class TestPdfStream:
    """Test PdfStream dataclass."""

    def test_create_stream(self) -> None:
        stream = PdfStream(
            dictionary={"/Type": "/XObject", "/Length": 100},
            data=b"stream content",
            is_compressed=False,
        )
        assert stream.data == b"stream content"
        assert stream.is_compressed is False
        assert stream.compression_filter is None
        assert stream.object_number == 0

    def test_create_compressed_stream(self) -> None:
        stream = PdfStream(
            dictionary={"/Filter": "/FlateDecode"},
            data=b"decompressed data",
            is_compressed=True,
            compression_filter="/FlateDecode",
            object_number=5,
            generation_number=0,
        )
        assert stream.is_compressed is True
        assert stream.compression_filter == "/FlateDecode"
        assert stream.object_number == 5

    def test_stream_is_frozen(self) -> None:
        stream = PdfStream(dictionary={}, data=b"", is_compressed=False)
        with pytest.raises(AttributeError):
            stream.data = b"new"  # type: ignore[misc]


class TestPdfObject:
    """Test PdfObject dataclass."""

    def test_create_dict_object(self) -> None:
        obj = PdfObject(
            object_number=1,
            generation_number=0,
            is_indirect=True,
            value={"/Type": "/Catalog"},
            obj_type="dict",
        )
        assert obj.object_number == 1
        assert obj.is_indirect is True
        assert obj.obj_type == "dict"

    def test_create_array_object(self) -> None:
        obj = PdfObject(
            object_number=2,
            generation_number=0,
            is_indirect=True,
            value=[1, 2, 3],
            obj_type="array",
        )
        assert obj.obj_type == "array"
        assert obj.value == [1, 2, 3]

    def test_frozen(self) -> None:
        obj = PdfObject(
            object_number=1,
            generation_number=0,
            is_indirect=True,
            value=None,
            obj_type="null",
        )
        with pytest.raises(AttributeError):
            obj.value = "changed"  # type: ignore[misc]


class TestPdfPage:
    """Test PdfPage dataclass."""

    def test_create_page_minimal(self) -> None:
        page = PdfPage(
            page_num=1,
            page_dict={"/Type": "/Page"},
            media_box=(0.0, 0.0, 612.0, 792.0),
        )
        assert page.page_num == 1
        assert page.media_box == (0.0, 0.0, 612.0, 792.0)
        assert page.crop_box is None
        assert page.rotate == 0
        assert page.user_unit == 1.0

    def test_create_page_full(self) -> None:
        page = PdfPage(
            page_num=3,
            page_dict={"/Type": "/Page"},
            media_box=(0.0, 0.0, 595.0, 842.0),
            crop_box=(10.0, 10.0, 585.0, 832.0),
            bleed_box=(5.0, 5.0, 590.0, 837.0),
            trim_box=(15.0, 15.0, 580.0, 827.0),
            art_box=(20.0, 20.0, 575.0, 822.0),
            rotate=90,
            user_unit=2.0,
        )
        assert page.trim_box is not None
        assert page.rotate == 90
        assert page.user_unit == 2.0


class TestPdfDocument:
    """Test PdfDocument dataclass."""

    def test_create_document_minimal(self) -> None:
        doc = PdfDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
        )
        assert doc.version == "1.7"
        assert doc.page_count == 1
        assert doc.is_encrypted is False
        assert doc.info_dict == {}
        assert doc.pages == []
        assert doc.output_intents == []
        assert doc.metadata_stream is None

    def test_create_document_with_pages(self) -> None:
        pages = [
            PdfPage(page_num=1, page_dict={}, media_box=(0, 0, 612, 792)),
            PdfPage(page_num=2, page_dict={}, media_box=(0, 0, 612, 792)),
        ]
        doc = PdfDocument(
            version="2.0",
            page_count=2,
            is_encrypted=False,
            pages=pages,
        )
        assert len(doc.pages) == 2
        assert doc.pages[0].page_num == 1
        assert doc.pages[1].page_num == 2


class TestParserAdapterInterface:
    """Verify ParserAdapter cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            ParserAdapter()  # type: ignore[abstract]  # skipcq: PYL-E0110

    def test_has_required_methods(self) -> None:
        """Verify all required abstract methods exist."""
        required_methods = [
            "open",
            "get_page",
            "get_catalog",
            "get_content_stream",
            "get_resources",
            "resolve_reference",
            "get_page_tree",
            "get_object_by_number",
            "get_page_parent_chain",
        ]
        for method_name in required_methods:
            assert hasattr(ParserAdapter, method_name), f"Missing method: {method_name}"
