"""Tests for DocumentAnalyzer — document-level consistency checks."""

from __future__ import annotations

from siftpdf.analyzers.document import DocumentAnalyzer
from siftpdf.analyzers.finding import Severity
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document(
    pages: list[SemanticPage] | None = None,
    is_encrypted: bool = False,
    info_dict: dict | None = None,
) -> SemanticDocument:
    _pages = pages or [SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))]
    return SemanticDocument(
        version="1.7",
        page_count=len(_pages),
        is_encrypted=is_encrypted,
        info_dict=info_dict or {},
        pages=_pages,
    )


class TestEncryption:
    @staticmethod
    def test_encrypted_aground() -> None:
        doc = _make_document(is_encrypted=True)
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_004" in ids
        f = next((f for f in findings if f.inspection_id == "LPDF_DOC_004"), None)
        assert f is not None
        assert f.severity == Severity.ERROR

    @staticmethod
    def test_not_encrypted_clean() -> None:
        doc = _make_document(is_encrypted=False)
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_004" not in ids


class TestMissingTitle:
    @staticmethod
    def test_no_title_advisory() -> None:
        doc = _make_document(info_dict={})
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_003" in ids

    @staticmethod
    def test_with_title_clean() -> None:
        doc = _make_document(info_dict={"/Title": "My Document"})
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_003" not in ids


class TestMixedPageSizes:
    @staticmethod
    def test_mixed_sizes_advisory() -> None:
        pages = [
            SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792)),  # Letter
            SemanticPage(page_num=2, media_box=PdfBox(0, 0, 595, 842)),  # A4
        ]
        doc = _make_document(pages=pages)
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_001" in ids

    @staticmethod
    def test_same_sizes_clean() -> None:
        pages = [
            SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792)),
            SemanticPage(page_num=2, media_box=PdfBox(0, 0, 612, 792)),
        ]
        doc = _make_document(pages=pages)
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_001" not in ids

    @staticmethod
    def test_single_page_no_check() -> None:
        doc = _make_document()
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_001" not in ids


class TestInconsistentRotation:
    @staticmethod
    def test_inconsistent_rotation_advisory() -> None:
        pages = [
            SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792), rotate=0),
            SemanticPage(page_num=2, media_box=PdfBox(0, 0, 612, 792), rotate=90),
        ]
        doc = _make_document(pages=pages)
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_002" in ids

    @staticmethod
    def test_consistent_rotation_clean() -> None:
        pages = [
            SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792), rotate=90),
            SemanticPage(page_num=2, media_box=PdfBox(0, 0, 612, 792), rotate=90),
        ]
        doc = _make_document(pages=pages)
        findings = DocumentAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_DOC_002" not in ids
