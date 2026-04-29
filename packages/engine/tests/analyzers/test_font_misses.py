"""Tests for PR-I — font miss closures from the post-merge audit.

Two new behaviours:

1. ``LPDF_FONT_005`` (Missing ToUnicode) was gated to CID fonts only.
   Widened to fire on simple fonts too, severity ADVISORY (versus
   WARNING for CID).
2. New ``LPDF_FONT_NONE_DECLARED`` advisory for pages with non-trivial
   content streams but no declared fonts (outlined-text artwork).
"""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.font import FontAnalyzer
from lintpdf.semantic.model import (
    PdfBox,
    PdfFont,
    SemanticDocument,
    SemanticPage,
)


def _doc_with_fonts(fonts: dict[str, PdfFont], content: bytes = b"") -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        fonts=fonts,
        content_stream=content,
    )
    return SemanticDocument(version="1.7", page_count=1, is_encrypted=False, pages=[page])


def _doc_with_pages(pages: list[SemanticPage]) -> SemanticDocument:
    return SemanticDocument(version="1.7", page_count=len(pages), is_encrypted=False, pages=pages)


# ── LPDF_FONT_005 widened to non-CID ────────────────────────────────────────


class TestToUnicodeWidened:
    @staticmethod
    def test_simple_font_no_tounicode_fires_advisory() -> None:
        # Type1 simple font without ToUnicode — pre-PR-I this was silent.
        f = PdfFont(
            name="F1",
            base_font="Helvetica",
            font_type="Type1",
            embedded=True,
            subset=False,
            has_to_unicode=False,
        )
        doc = _doc_with_fonts({"F1": f})
        findings = FontAnalyzer().analyze(doc, [])
        f5 = [x for x in findings if x.inspection_id == "LPDF_FONT_005"]
        assert len(f5) == 1
        assert f5[0].severity == Severity.ADVISORY
        assert f5[0].details["is_cid"] is False

    @staticmethod
    def test_cid_font_no_tounicode_still_warning() -> None:
        # CIDFontType2 composite — keeps WARNING severity per spec.
        f = PdfFont(
            name="F2",
            base_font="STHeiti",
            font_type="CIDFontType2",
            embedded=True,
            subset=False,
            has_to_unicode=False,
            cid_system_info={"Registry": "Adobe", "Ordering": "GB1"},
        )
        doc = _doc_with_fonts({"F2": f})
        findings = FontAnalyzer().analyze(doc, [])
        f5 = [x for x in findings if x.inspection_id == "LPDF_FONT_005"]
        assert len(f5) == 1
        assert f5[0].severity == Severity.WARNING
        assert f5[0].details["is_cid"] is True

    @staticmethod
    def test_font_with_tounicode_no_finding() -> None:
        f = PdfFont(
            name="F1",
            base_font="Helvetica",
            font_type="Type1",
            embedded=True,
            subset=False,
            has_to_unicode=True,
        )
        doc = _doc_with_fonts({"F1": f})
        findings = FontAnalyzer().analyze(doc, [])
        assert not [x for x in findings if x.inspection_id == "LPDF_FONT_005"]


# ── LPDF_FONT_NONE_DECLARED ─────────────────────────────────────────────────


class TestNoneDeclared:
    @staticmethod
    def test_page_with_no_fonts_and_heavy_content_fires() -> None:
        # 2 KB content stream, no fonts → likely outlined.
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            fonts={},
            content_stream=b"x" * 2048,
        )
        findings = FontAnalyzer().analyze(_doc_with_pages([page]), [])
        nd = [x for x in findings if x.inspection_id == "LPDF_FONT_NONE_DECLARED"]
        assert len(nd) == 1
        assert nd[0].severity == Severity.ADVISORY
        assert nd[0].details["fonts_declared"] == 0
        assert nd[0].details["content_stream_bytes"] == 2048

    @staticmethod
    def test_page_with_fonts_no_finding() -> None:
        f = PdfFont(
            name="F1",
            base_font="Helvetica",
            font_type="Type1",
            embedded=True,
            subset=False,
        )
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            fonts={"F1": f},
            content_stream=b"x" * 2048,
        )
        findings = FontAnalyzer().analyze(_doc_with_pages([page]), [])
        assert not [x for x in findings if x.inspection_id == "LPDF_FONT_NONE_DECLARED"]

    @staticmethod
    def test_empty_content_stream_no_finding() -> None:
        # Truly empty page — not an outlined-art case.
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            fonts={},
            content_stream=b"",
        )
        findings = FontAnalyzer().analyze(_doc_with_pages([page]), [])
        assert not [x for x in findings if x.inspection_id == "LPDF_FONT_NONE_DECLARED"]

    @staticmethod
    def test_tiny_content_stream_no_finding() -> None:
        # 200 B content stream — unlikely to contain real outlined text.
        page = SemanticPage(
            page_num=1,
            media_box=PdfBox(0, 0, 612, 792),
            fonts={},
            content_stream=b"x" * 200,
        )
        findings = FontAnalyzer().analyze(_doc_with_pages([page]), [])
        assert not [x for x in findings if x.inspection_id == "LPDF_FONT_NONE_DECLARED"]

    @staticmethod
    def test_per_page_dedupe_one_finding_per_page() -> None:
        # Two outlined pages → two findings (one per page).
        pages = [
            SemanticPage(
                page_num=i, media_box=PdfBox(0, 0, 612, 792), fonts={}, content_stream=b"x" * 2048
            )
            for i in (1, 2)
        ]
        findings = FontAnalyzer().analyze(_doc_with_pages(pages), [])
        nd = [x for x in findings if x.inspection_id == "LPDF_FONT_NONE_DECLARED"]
        assert len(nd) == 2
        assert {f.page_num for f in nd} == {1, 2}
