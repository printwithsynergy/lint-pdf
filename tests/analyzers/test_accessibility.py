"""Tests for AccessibilityAnalyzer — document accessibility checks."""

from __future__ import annotations

from lintpdf.analyzers.accessibility import AccessibilityAnalyzer
from lintpdf.analyzers.finding import Severity
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document(
    catalog: dict | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        catalog=catalog or {},
    )


class TestNoStructureTree:
    """Test LPDF_ACCESS_001: No structure tree."""

    @staticmethod
    def test_no_struct_tree_flags() -> None:
        doc = _make_document(catalog={})
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_ACCESS_001"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY

    @staticmethod
    def test_struct_tree_present_no_flag() -> None:
        doc = _make_document(catalog={"/StructTreeRoot": {"Type": "StructTreeRoot"}})
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_ACCESS_001"]
        assert len(f) == 0


class TestNoDocumentLanguage:
    """Test LPDF_ACCESS_002: No document language."""

    @staticmethod
    def test_no_lang_flags() -> None:
        doc = _make_document(catalog={})
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_ACCESS_002"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY

    @staticmethod
    def test_lang_present_no_flag() -> None:
        doc = _make_document(catalog={"/Lang": "en-US"})
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_ACCESS_002"]
        assert len(f) == 0


class TestTaggedPdf:
    """Test LPDF_ACCESS_003: Tagged PDF present."""

    @staticmethod
    def test_tagged_pdf_flagged() -> None:
        doc = _make_document(
            catalog={
                "/StructTreeRoot": {"Type": "StructTreeRoot"},
                "/MarkInfo": {"/Marked": True},
            }
        )
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_ACCESS_003"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY

    @staticmethod
    def test_struct_tree_without_mark_info_no_tagged_flag() -> None:
        doc = _make_document(catalog={"/StructTreeRoot": {"Type": "StructTreeRoot"}})
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_ACCESS_003"]
        assert len(f) == 0

    @staticmethod
    def test_mark_info_not_marked_no_flag() -> None:
        doc = _make_document(
            catalog={
                "/StructTreeRoot": {"Type": "StructTreeRoot"},
                "/MarkInfo": {"/Marked": False},
            }
        )
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_ACCESS_003"]
        assert len(f) == 0

    @staticmethod
    def test_full_accessible_doc() -> None:
        """Fully accessible doc: struct tree, lang, marked."""
        doc = _make_document(
            catalog={
                "/StructTreeRoot": {"Type": "StructTreeRoot"},
                "/Lang": "en-US",
                "/MarkInfo": {"/Marked": True},
            }
        )
        analyzer = AccessibilityAnalyzer()
        findings = analyzer.analyze(doc, [])
        # Should only have ACCESS_003 (tagged), no ACCESS_001 or 002
        ids = {f.inspection_id for f in findings}
        assert "LPDF_ACCESS_001" not in ids
        assert "LPDF_ACCESS_002" not in ids
        assert "LPDF_ACCESS_003" in ids
