"""Tests for DocumentAnalyzer Part 5 checks — LPDF_DOC_005, 006, 007."""

from __future__ import annotations

from lintpdf.analyzers.document import DocumentAnalyzer
from lintpdf.analyzers.finding import Severity
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document(
    catalog: dict | None = None,
    trailer: dict | None = None,
    info_dict: dict | None = None,
) -> SemanticDocument:
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
        catalog=catalog or {},
        trailer=trailer or {},
        info_dict=info_dict or {"/Title": "Test"},
    )


class TestLinearizedPdf:
    """Test LPDF_DOC_005: Linearized PDF detected."""

    @staticmethod
    def test_linearized_in_catalog_flags() -> None:
        doc = _make_document(catalog={"/Linearized": "1.0"})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_005"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY

    @staticmethod
    def test_linearized_in_trailer_flags() -> None:
        doc = _make_document(trailer={"/Linearized": "1.0"})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_005"]
        assert len(f) == 1

    @staticmethod
    def test_not_linearized_no_flag() -> None:
        doc = _make_document()
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_005"]
        assert len(f) == 0


class TestIncrementalUpdates:
    """Test LPDF_DOC_006: Incremental updates detected."""

    @staticmethod
    def test_prev_in_trailer_flags() -> None:
        doc = _make_document(trailer={"/Prev": 12345})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_006"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY

    @staticmethod
    def test_no_prev_no_flag() -> None:
        doc = _make_document(trailer={})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_006"]
        assert len(f) == 0


class TestFileSizeThreshold:
    """Test LPDF_DOC_007: File size exceeds threshold."""

    @staticmethod
    def test_large_file_flags() -> None:
        size = 600 * 1024 * 1024  # 600 MB
        doc = _make_document(info_dict={"/Title": "Big", "/FileSize": str(size)})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_007"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY
        assert f[0].details["file_size_bytes"] == size

    @staticmethod
    def test_small_file_no_flag() -> None:
        size = 10 * 1024 * 1024  # 10 MB
        doc = _make_document(info_dict={"/Title": "Small", "/FileSize": str(size)})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_007"]
        assert len(f) == 0

    @staticmethod
    def test_custom_threshold() -> None:
        size = 50 * 1024 * 1024  # 50 MB
        doc = _make_document(info_dict={"/Title": "Med", "/FileSize": str(size)})
        analyzer = DocumentAnalyzer(max_file_size_bytes=30 * 1024 * 1024)
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_007"]
        assert len(f) == 1

    @staticmethod
    def test_no_file_size_no_flag() -> None:
        doc = _make_document(info_dict={"/Title": "NoSize"})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_007"]
        assert len(f) == 0

    @staticmethod
    def test_invalid_file_size_no_flag() -> None:
        doc = _make_document(info_dict={"/Title": "Bad", "/FileSize": "not_a_number"})
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "LPDF_DOC_007"]
        assert len(f) == 0
