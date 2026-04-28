"""Tests for PikePDFAdapter — concrete pikepdf implementation.

Tests cover:
- Opening valid and malformed PDFs
- Page extraction with box metadata
- Content stream extraction (single and array)
- Resource dictionary extraction
- Object resolution
- Page tree traversal
- Content stream parsing (operator/operand pairs)
- Error handling for all failure modes
"""

from __future__ import annotations

import io

import pikepdf
import pytest

from lintpdf.exceptions import (
    PDFObjectNotFoundError,
    PDFParseError,
    PDFStructureError,
)
from lintpdf.parser.adapter import PdfDocument
from lintpdf.parser.pikepdf_adapter import PikePDFAdapter

# --- Fixtures ---


@pytest.fixture
def adapter() -> PikePDFAdapter:
    """Fresh adapter instance."""
    return PikePDFAdapter()


@pytest.fixture
def real_pdf_bytes() -> bytes:
    """Create a proper PDF using pikepdf (more reliable than hand-crafted bytes)."""
    pdf = pikepdf.Pdf.new()
    page = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
            Resources=pikepdf.Dictionary(
                Font=pikepdf.Dictionary(),
            ),
        )
    )
    pdf.pages.append(page)
    buf = io.BytesIO()
    pdf.save(buf)
    return buf.getvalue()


@pytest.fixture
def multi_page_pdf_bytes() -> bytes:
    """Create a 3-page PDF with different box configurations."""
    pdf = pikepdf.Pdf.new()

    # Page 1: just MediaBox
    page1 = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
        )
    )

    # Page 2: MediaBox + TrimBox + BleedBox
    page2 = pikepdf.Page(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Page,
            MediaBox=[0, 0, 612, 792],
            TrimBox=[20, 20, 592, 772],
            BleedBox=[10, 10, 602, 782],
        )
    )

    # Page 3: Rotated page
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
    """Create a PDF with actual content stream operators."""
    pdf = pikepdf.Pdf.new()

    # Create a content stream with text operators
    content = b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET"

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


# --- Open Tests ---


class TestOpen:
    """Test PikePDFAdapter.open()."""

    @staticmethod
    def test_open_valid_pdf(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        assert isinstance(doc, PdfDocument)
        assert doc.page_count == 1
        assert doc.is_encrypted is False
        assert doc.version  # Non-empty version string

    @staticmethod
    def test_open_multi_page(adapter: PikePDFAdapter, multi_page_pdf_bytes: bytes) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        assert doc.page_count == 3
        assert len(doc.pages) == 3

    @staticmethod
    def test_open_invalid_bytes_raises_structure_error(adapter: PikePDFAdapter) -> None:
        with pytest.raises(PDFStructureError, match="Failed to open PDF"):
            adapter.open(b"not a pdf at all")

    @staticmethod
    def test_open_empty_bytes_raises_structure_error(adapter: PikePDFAdapter) -> None:
        with pytest.raises(PDFStructureError):
            adapter.open(b"")

    def test_open_truncated_pdf_raises_structure_error(
        self, adapter: PikePDFAdapter, real_pdf_bytes: bytes
    ) -> None:
        truncated = real_pdf_bytes[:50]
        with pytest.raises(PDFStructureError):
            adapter.open(truncated)

    @staticmethod
    def test_version_extracted(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        # pikepdf creates PDFs as version 1.x or 2.x
        assert doc.version.startswith(("1.", "2."))

    @staticmethod
    def test_catalog_populated(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        assert isinstance(doc.catalog, dict)

    @staticmethod
    def test_trailer_populated(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        assert isinstance(doc.trailer, dict)


# --- Page Extraction Tests ---


class TestPageExtraction:
    """Test page extraction and metadata."""

    def test_page_num_is_1_indexed(
        self, adapter: PikePDFAdapter, multi_page_pdf_bytes: bytes
    ) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        assert doc.pages[0].page_num == 1
        assert doc.pages[1].page_num == 2
        assert doc.pages[2].page_num == 3

    @staticmethod
    def test_media_box_extracted(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        page = doc.pages[0]
        assert page.media_box is not None
        assert page.media_box == (0.0, 0.0, 612.0, 792.0)

    @staticmethod
    def test_optional_boxes(adapter: PikePDFAdapter, multi_page_pdf_bytes: bytes) -> None:
        doc = adapter.open(multi_page_pdf_bytes)

        # Page 1: only MediaBox
        assert doc.pages[0].media_box is not None
        assert doc.pages[0].trim_box is None
        assert doc.pages[0].bleed_box is None

        # Page 2: MediaBox + TrimBox + BleedBox
        assert doc.pages[1].trim_box is not None
        assert doc.pages[1].bleed_box is not None
        assert doc.pages[1].trim_box == (20.0, 20.0, 592.0, 772.0)

    @staticmethod
    def test_rotation_extracted(adapter: PikePDFAdapter, multi_page_pdf_bytes: bytes) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        assert doc.pages[0].rotate == 0
        assert doc.pages[2].rotate == 90

    @staticmethod
    def test_get_page_by_number(adapter: PikePDFAdapter, multi_page_pdf_bytes: bytes) -> None:
        doc = adapter.open(multi_page_pdf_bytes)
        page2 = adapter.get_page(doc, 2)
        assert page2.page_num == 2
        assert page2.trim_box is not None

    @staticmethod
    def test_get_page_out_of_range(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        with pytest.raises(IndexError, match="out of range"):
            adapter.get_page(doc, 0)
        with pytest.raises(IndexError, match="out of range"):
            adapter.get_page(doc, 5)


# --- Content Stream Tests ---


class TestContentStream:
    """Test content stream extraction."""

    @staticmethod
    def test_blank_page_returns_empty(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        content = adapter.get_content_stream(doc.pages[0])
        # Blank page may have empty or minimal content
        assert isinstance(content, bytes)

    def test_content_stream_with_text(
        self, adapter: PikePDFAdapter, pdf_with_content: bytes
    ) -> None:
        doc = adapter.open(pdf_with_content)
        content = adapter.get_content_stream(doc.pages[0])
        assert isinstance(content, bytes)
        assert len(content) > 0
        # Should contain the text operators we put in
        assert b"BT" in content
        assert b"Tj" in content

    def test_parse_content_stream_operators(
        self, adapter: PikePDFAdapter, pdf_with_content: bytes
    ) -> None:
        doc = adapter.open(pdf_with_content)
        instructions = adapter.parse_content_stream(doc.pages[0])
        assert isinstance(instructions, list)
        assert len(instructions) > 0

        # Each instruction is (operands, operator_name)
        operators = [op for _, op in instructions]
        assert "BT" in operators
        assert "Tf" in operators
        assert "Td" in operators
        assert "Tj" in operators
        assert "ET" in operators

    def test_parse_content_stream_operands(
        self, adapter: PikePDFAdapter, pdf_with_content: bytes
    ) -> None:
        doc = adapter.open(pdf_with_content)
        instructions = adapter.parse_content_stream(doc.pages[0])

        # Find the Tf operator — should have font name and size
        tf_instructions = [(ops, op) for ops, op in instructions if op == "Tf"]
        assert len(tf_instructions) >= 1
        operands, _ = tf_instructions[0]
        assert len(operands) == 2  # font_name, font_size
        assert operands[1] == 12  # font size 12


# --- Resources Tests ---


class TestResources:
    """Test resource dictionary extraction."""

    def test_resources_from_page_with_font(
        self, adapter: PikePDFAdapter, pdf_with_content: bytes
    ) -> None:
        doc = adapter.open(pdf_with_content)
        resources = adapter.get_resources(doc.pages[0])
        assert isinstance(resources, dict)
        assert "/Font" in resources

    @staticmethod
    def test_resources_from_blank_page(adapter: PikePDFAdapter) -> None:
        # Create a page with no resources
        pdf = pikepdf.Pdf.new()
        page = pikepdf.Page(
            pikepdf.Dictionary(
                Type=pikepdf.Name.Page,
                MediaBox=[0, 0, 612, 792],
            )
        )
        pdf.pages.append(page)
        buf = io.BytesIO()
        pdf.save(buf)

        doc = adapter.open(buf.getvalue())
        resources = adapter.get_resources(doc.pages[0])
        assert isinstance(resources, dict)


# --- Object Resolution Tests ---


class TestObjectResolution:
    """Test object retrieval and reference resolution."""

    @staticmethod
    def test_get_page_tree(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        page_tree = adapter.get_page_tree(doc)
        assert isinstance(page_tree, dict)

    @staticmethod
    def test_get_catalog(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        catalog = adapter.get_catalog(doc)
        assert isinstance(catalog, dict)

    @staticmethod
    def test_get_page_parent_chain(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        doc = adapter.open(real_pdf_bytes)
        chain = adapter.get_page_parent_chain(doc.pages[0])
        assert isinstance(chain, list)
        # Should have at least the /Pages root
        assert len(chain) >= 1


# --- Error Handling Tests ---


class TestErrorHandling:
    """Test error paths and graceful failures."""

    @staticmethod
    def test_ensure_open_raises_without_open() -> None:
        adapter = PikePDFAdapter()
        with pytest.raises(PDFParseError, match="No PDF is currently open"):
            adapter._ensure_open()

    def test_resolve_invalid_reference(
        self, adapter: PikePDFAdapter, real_pdf_bytes: bytes
    ) -> None:
        """pikepdf returns null for non-existent objects rather than raising.
        Verify we can at least resolve without crashing."""
        doc = adapter.open(real_pdf_bytes)
        # pikepdf silently returns null for missing objects
        result = adapter.resolve_reference(doc, "9999 0 R")
        assert result.object_number == 9999

    def test_resolve_malformed_reference(
        self, adapter: PikePDFAdapter, real_pdf_bytes: bytes
    ) -> None:
        doc = adapter.open(real_pdf_bytes)
        with pytest.raises(PDFObjectNotFoundError, match="Cannot parse"):
            adapter.resolve_reference(doc, "not_a_ref")

    @staticmethod
    def test_close_releases_resources(adapter: PikePDFAdapter, real_pdf_bytes: bytes) -> None:
        adapter.open(real_pdf_bytes)
        adapter.close()
        assert adapter._pdf is None
        assert adapter._pdf_bytes is None

    @staticmethod
    def test_close_idempotent(adapter: PikePDFAdapter) -> None:
        adapter.close()  # Should not raise
        adapter.close()  # Still should not raise


# --- Integration-Style Tests ---


class TestIntegration:
    """Integration tests covering full open → extract → close flow."""

    @staticmethod
    def test_full_flow_single_page(adapter: PikePDFAdapter, pdf_with_content: bytes) -> None:
        """Open PDF → extract pages → get content → get resources → parse → close."""
        # Open
        doc = adapter.open(pdf_with_content)
        assert doc.page_count == 1

        # Extract page
        page = adapter.get_page(doc, 1)
        assert page.media_box is not None

        # Get content stream
        content = adapter.get_content_stream(page)
        assert len(content) > 0

        # Get resources
        resources = adapter.get_resources(page)
        assert "/Font" in resources

        # Parse operators
        instructions = adapter.parse_content_stream(page)
        assert len(instructions) > 0

        # Get page tree
        page_tree = adapter.get_page_tree(doc)
        assert isinstance(page_tree, dict)

        # Get parent chain
        chain = adapter.get_page_parent_chain(page)
        assert len(chain) >= 1

        # Close
        adapter.close()

    def test_full_flow_multi_page(
        self, adapter: PikePDFAdapter, multi_page_pdf_bytes: bytes
    ) -> None:
        """Verify all pages extracted correctly in multi-page PDF."""
        doc = adapter.open(multi_page_pdf_bytes)
        assert doc.page_count == 3

        for i in range(1, 4):
            page = adapter.get_page(doc, i)
            assert page.page_num == i
            assert page.media_box is not None
            content = adapter.get_content_stream(page)
            assert isinstance(content, bytes)
            resources = adapter.get_resources(page)
            assert isinstance(resources, dict)

        adapter.close()
