"""Tests for Part 3 model additions — PdfAnnotation, transparency_group, trailer."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.semantic.model import PdfAnnotation, PdfBox, SemanticDocument, SemanticPage


class TestPdfAnnotation:
    """Test PdfAnnotation dataclass."""

    def test_basic_annotation(self) -> None:
        annot = PdfAnnotation(subtype="Text", page_num=1)
        assert annot.subtype == "Text"
        assert annot.rect is None
        assert annot.flags == 0
        assert annot.contents == ""

    def test_annotation_with_rect(self) -> None:
        rect = PdfBox(100, 200, 300, 400)
        annot = PdfAnnotation(subtype="Link", rect=rect, page_num=1)
        assert annot.rect is not None
        assert annot.rect.width == 200.0

    def test_is_printable_flag(self) -> None:
        # Bit 3 (value 4) = Print flag
        annot = PdfAnnotation(subtype="Text", flags=0x04, page_num=1)
        assert annot.is_printable is True

    def test_not_printable(self) -> None:
        annot = PdfAnnotation(subtype="Text", flags=0, page_num=1)
        assert annot.is_printable is False

    def test_is_hidden_flag(self) -> None:
        # Bit 2 (value 2) = Hidden flag
        annot = PdfAnnotation(subtype="Text", flags=0x02, page_num=1)
        assert annot.is_hidden is True

    def test_not_hidden(self) -> None:
        annot = PdfAnnotation(subtype="Text", flags=0, page_num=1)
        assert annot.is_hidden is False

    def test_printable_and_hidden(self) -> None:
        # Both flags set
        annot = PdfAnnotation(subtype="Text", flags=0x06, page_num=1)
        assert annot.is_printable is True
        assert annot.is_hidden is True

    def test_frozen(self) -> None:
        annot = PdfAnnotation(subtype="Text", page_num=1)
        # Frozen dataclass — attributes cannot be modified
        try:
            annot.subtype = "Link"  # type: ignore[misc]
            raise AssertionError("Should not allow mutation")
        except AttributeError:
            pass


class TestSemanticPageAnnotations:
    """Test annotations field on SemanticPage."""

    def test_default_empty(self) -> None:
        page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
        assert page.annotations == []

    def test_with_annotations(self) -> None:
        annots = [
            PdfAnnotation(subtype="Text", page_num=1),
            PdfAnnotation(subtype="Link", page_num=1),
        ]
        page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792), annotations=annots)
        assert len(page.annotations) == 2
        assert page.annotations[0].subtype == "Text"


class TestSemanticPageTransparencyGroup:
    """Test transparency_group field on SemanticPage."""

    def test_default_none(self) -> None:
        page = SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))
        assert page.transparency_group is None

    def test_with_group(self) -> None:
        group = {"/S": "/Transparency", "/CS": "/DeviceCMYK", "/I": True, "/K": False}
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            transparency_group=group,
        )
        assert page.transparency_group is not None
        assert page.transparency_group["/CS"] == "/DeviceCMYK"


class TestSemanticDocumentTrailer:
    """Test trailer field on SemanticDocument."""

    def test_default_empty(self) -> None:
        doc = SemanticDocument(version="1.7", page_count=1, is_encrypted=False)
        assert doc.trailer == {}

    def test_with_trailer(self) -> None:
        trailer = {"/Size": 100, "/ID": ["abc", "def"]}
        doc = SemanticDocument(version="1.7", page_count=1, is_encrypted=False, trailer=trailer)
        assert doc.trailer["/Size"] == 100
