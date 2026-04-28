"""Tests for SemanticModelBuilder — inheritance resolution and enrichment."""

from __future__ import annotations

import io

import pikepdf
import pytest

from lintpdf.parser.pikepdf_adapter import PikePDFAdapter
from lintpdf.semantic.builder import SemanticModelBuilder
from lintpdf.semantic.model import PdfBox


@pytest.fixture
def adapter() -> PikePDFAdapter:
    return PikePDFAdapter()


@pytest.fixture
def builder(adapter: PikePDFAdapter) -> SemanticModelBuilder:
    return SemanticModelBuilder(adapter)


@pytest.fixture
def simple_pdf_bytes() -> bytes:
    """Single page with MediaBox, TrimBox, BleedBox, and a font."""
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
            TrimBox=[20, 20, 592, 772],
            BleedBox=[10, 10, 602, 782],
            Resources=pikepdf.Dictionary(
                Font=pikepdf.Dictionary(
                    F1=pikepdf.Dictionary(
                        Type=pikepdf.Name.Font,
                        Subtype=pikepdf.Name.Type1,
                        BaseFont=pikepdf.Name.Helvetica,
                    )
                ),
            ),
        )
    )
    pdf.pages.append(page)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


@pytest.fixture
def multi_page_pdf_bytes() -> bytes:
    """3-page PDF with different configurations."""
    pdf = pikepdf.Pdf.new()

    page1 = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
        )
    )
    page2 = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
            TrimBox=[20, 20, 592, 772],
            BleedBox=[10, 10, 602, 782],
        )
    )
    page3 = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 595, 842],
            Rotate=90,
        )
    )

    pdf.pages.append(page1)
    pdf.pages.append(page2)
    pdf.pages.append(page3)

    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


@pytest.fixture
def pdf_with_content() -> bytes:
    """PDF with content stream operators and font."""
    pdf = pikepdf.Pdf.new()
    content = b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET"
    page = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
            Resources=pikepdf.Dictionary(
                Font=pikepdf.Dictionary(
                    F1=pikepdf.Dictionary(
                        Type=pikepdf.Name.Font,
                        Subtype=pikepdf.Name.Type1,
                        BaseFont=pikepdf.Name.Helvetica,
                    )
                ),
            ),
            Contents=pdf.make_stream(content),
        )
    )
    pdf.pages.append(page)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


class TestBuildDocument:
    """Test full document building."""

    def test_build_single_page(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        assert semantic_doc.page_count == 1
        assert semantic_doc.version
        assert len(semantic_doc.pages) == 1

    def test_build_multi_page(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        multi_page_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        semantic_doc = builder.build(doc)
        assert semantic_doc.page_count == 3
        assert len(semantic_doc.pages) == 3
        assert semantic_doc.pages[0].page_num == 1
        assert semantic_doc.pages[2].page_num == 3

    def test_preserves_document_metadata(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        assert semantic_doc.is_encrypted is False
        assert isinstance(semantic_doc.catalog, dict)


class TestBoxResolution:
    """Test box resolution and defaults."""

    def test_media_box_resolved(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        page = semantic_doc.pages[0]
        assert page.media_box == PdfBox(0, 0, 612, 792)

    def test_trim_box_resolved(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        page = semantic_doc.pages[0]
        assert page.trim_box == PdfBox(20, 20, 592, 772)

    def test_bleed_box_resolved(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        page = semantic_doc.pages[0]
        assert page.bleed_box == PdfBox(10, 10, 602, 782)

    def test_crop_box_defaults_to_media_box(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        page = semantic_doc.pages[0]
        # CropBox not set => defaults to MediaBox
        assert page.crop_box == page.media_box

    def test_missing_boxes_default_to_crop_box(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        multi_page_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        semantic_doc = builder.build(doc)
        page1 = semantic_doc.pages[0]
        # Page 1 has no TrimBox/BleedBox/ArtBox => all default to CropBox (which is MediaBox)
        assert page1.trim_box == page1.crop_box
        assert page1.bleed_box == page1.crop_box
        assert page1.art_box == page1.crop_box


class TestRotation:
    """Test rotation resolution."""

    def test_no_rotation(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        assert semantic_doc.pages[0].rotate == 0

    def test_rotation_90(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        multi_page_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        semantic_doc = builder.build(doc)
        page3 = semantic_doc.pages[2]
        assert page3.rotate == 90

    def test_effective_dimensions_with_rotation(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        multi_page_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        semantic_doc = builder.build(doc)
        page3 = semantic_doc.pages[2]
        # A4 (595x842) rotated 90 degrees
        assert page3.effective_width == 842.0
        assert page3.effective_height == 595.0


class TestFontExtraction:
    """Test font extraction from resources."""

    def test_font_extracted(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        page = semantic_doc.pages[0]
        assert "/F1" in page.fonts

    def test_font_properties(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        simple_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(simple_pdf_bytes)
        semantic_doc = builder.build(doc)
        font = semantic_doc.pages[0].fonts["/F1"]
        assert font.base_font == "Helvetica"
        assert font.font_type == "Type1"
        assert font.is_standard_14() is True

    def test_no_fonts_on_blank_page(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        multi_page_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        semantic_doc = builder.build(doc)
        page1 = semantic_doc.pages[0]
        assert len(page1.fonts) == 0


class TestContentStream:
    """Test content stream extraction."""

    def test_content_stream_extracted(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        pdf_with_content: bytes,
    ) -> None:
        doc = adapter.open(pdf_with_content)
        semantic_doc = builder.build(doc)
        page = semantic_doc.pages[0]
        assert len(page.content_stream) > 0
        assert b"BT" in page.content_stream

    def test_blank_page_empty_content(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        multi_page_pdf_bytes: bytes,
    ) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        semantic_doc = builder.build(doc)
        page1 = semantic_doc.pages[0]
        assert page1.content_stream == b""


class TestIntegration:
    """Integration: full open -> build -> inspect flow."""

    def test_full_flow(
        self,
        adapter: PikePDFAdapter,
        builder: SemanticModelBuilder,
        pdf_with_content: bytes,
    ) -> None:
        doc = adapter.open(pdf_with_content)
        semantic_doc = builder.build(doc)

        assert semantic_doc.page_count == 1
        page = semantic_doc.pages[0]

        # Box
        assert page.media_box.width == 612.0
        assert page.media_box.height == 792.0

        # Font
        assert len(page.fonts) > 0

        # Content
        assert len(page.content_stream) > 0

        # Dimensions
        assert page.effective_width == 612.0
        assert page.effective_height == 792.0
        assert page.effective_width_mm > 0
