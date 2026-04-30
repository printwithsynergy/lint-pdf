"""Tests for LPDF_DOC_009 — PDF version vs profile range (T1-CMP02)."""

from __future__ import annotations

from siftpdf.analyzers.document import DocumentAnalyzer, _parse_version
from siftpdf.analyzers.finding import Severity
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_doc(version: str) -> SemanticDocument:
    return SemanticDocument(
        version=version,
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestParseVersion:
    @staticmethod
    def test_known_formats() -> None:
        assert _parse_version("1.4") == (1, 4)
        assert _parse_version("1.6") == (1, 6)
        assert _parse_version("2.0") == (2, 0)
        assert _parse_version("1.10") == (1, 10)

    @staticmethod
    def test_comparison_ordering() -> None:
        assert _parse_version("1.7") < _parse_version("2.0")
        assert _parse_version("2.0") > _parse_version("1.7")
        assert _parse_version("1.4") < _parse_version("1.6")

    @staticmethod
    def test_malformed_returns_none() -> None:
        assert _parse_version("") is None
        assert _parse_version("garbage") is None
        assert _parse_version("1") is None
        assert _parse_version("1.2.3") is None
        assert _parse_version("1.x") is None


class TestBelowMinimum:
    @staticmethod
    def test_fires_when_below_min() -> None:
        analyzer = DocumentAnalyzer(min_pdf_version="1.6", profile_name="PDFX-4")
        findings = analyzer._check_pdf_version_against_profile(_make_doc("1.4"))
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_DOC_009"
        assert f.severity == Severity.WARNING
        assert f.details["failure_mode"] == "below_minimum"
        assert f.details["pdf_version"] == "1.4"
        assert f.details["min_pdf_version"] == "1.6"
        assert f.details["profile_name"] == "PDFX-4"
        assert "PDFX-4" in f.message
        assert "1.4" in f.message
        assert "1.6" in f.message

    @staticmethod
    def test_silent_when_equal_to_min() -> None:
        analyzer = DocumentAnalyzer(min_pdf_version="1.6")
        assert analyzer._check_pdf_version_against_profile(_make_doc("1.6")) == []

    @staticmethod
    def test_silent_when_above_min() -> None:
        analyzer = DocumentAnalyzer(min_pdf_version="1.6")
        assert analyzer._check_pdf_version_against_profile(_make_doc("2.0")) == []


class TestAboveMaximum:
    @staticmethod
    def test_fires_when_above_max() -> None:
        analyzer = DocumentAnalyzer(max_pdf_version="1.4", profile_name="PDFX-1a")
        findings = analyzer._check_pdf_version_against_profile(_make_doc("2.0"))
        assert len(findings) == 1
        f = findings[0]
        assert f.inspection_id == "LPDF_DOC_009"
        assert f.details["failure_mode"] == "above_maximum"
        assert f.details["max_pdf_version"] == "1.4"

    @staticmethod
    def test_silent_when_equal_to_max() -> None:
        analyzer = DocumentAnalyzer(max_pdf_version="1.4")
        assert analyzer._check_pdf_version_against_profile(_make_doc("1.4")) == []

    @staticmethod
    def test_silent_when_below_max() -> None:
        analyzer = DocumentAnalyzer(max_pdf_version="2.0")
        assert analyzer._check_pdf_version_against_profile(_make_doc("1.6")) == []


class TestRangeInclusive:
    @staticmethod
    def test_pdfx_1a_exact_match_silent() -> None:
        """PDF/X-1a-2003: min=1.4, max=1.4 — only 1.4 passes."""
        analyzer = DocumentAnalyzer(min_pdf_version="1.4", max_pdf_version="1.4")
        assert analyzer._check_pdf_version_against_profile(_make_doc("1.4")) == []

    @staticmethod
    def test_pdfx_1a_above_max_fires() -> None:
        analyzer = DocumentAnalyzer(min_pdf_version="1.4", max_pdf_version="1.4")
        findings = analyzer._check_pdf_version_against_profile(_make_doc("1.6"))
        assert len(findings) == 1
        assert findings[0].details["failure_mode"] == "above_maximum"

    @staticmethod
    def test_pdfx_1a_below_min_fires() -> None:
        analyzer = DocumentAnalyzer(min_pdf_version="1.4", max_pdf_version="1.4")
        findings = analyzer._check_pdf_version_against_profile(_make_doc("1.3"))
        assert len(findings) == 1
        assert findings[0].details["failure_mode"] == "below_minimum"


class TestDisabled:
    @staticmethod
    def test_no_constraints_no_finding() -> None:
        """Default analyzer has neither min nor max set — check silently
        no-ops for back-compat."""
        analyzer = DocumentAnalyzer()
        assert analyzer._check_pdf_version_against_profile(_make_doc("1.3")) == []
        assert analyzer._check_pdf_version_against_profile(_make_doc("2.0")) == []

    @staticmethod
    def test_malformed_document_version_is_silent() -> None:
        analyzer = DocumentAnalyzer(min_pdf_version="1.6")
        assert analyzer._check_pdf_version_against_profile(_make_doc("garbage")) == []

    @staticmethod
    def test_malformed_profile_min_is_silent() -> None:
        """If the profile ships with a malformed version string, don't crash;
        silently skip the check."""
        analyzer = DocumentAnalyzer(min_pdf_version="not-a-version")
        assert analyzer._check_pdf_version_against_profile(_make_doc("1.4")) == []


class TestAnalyzeIntegration:
    @staticmethod
    def test_analyze_emits_doc_009() -> None:
        """Full analyze() call routes through _check_pdf_version_against_profile."""
        analyzer = DocumentAnalyzer(min_pdf_version="1.6", profile_name="PDFX-4")
        findings = analyzer.analyze(_make_doc("1.4"), events=[])
        doc_009 = [f for f in findings if f.inspection_id == "LPDF_DOC_009"]
        assert len(doc_009) == 1

    @staticmethod
    def test_analyze_without_constraints_skips() -> None:
        """Default construction → no LPDF_DOC_009, even on ancient PDFs."""
        analyzer = DocumentAnalyzer()
        findings = analyzer.analyze(_make_doc("1.0"), events=[])
        assert all(f.inspection_id != "LPDF_DOC_009" for f in findings)
