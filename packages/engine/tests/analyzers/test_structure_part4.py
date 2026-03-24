"""Tests for StructureAnalyzer — GRD_STRUCT_006-007 (Part 4 deepening).

Tests XFA forms and tagged PDF detection.
"""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.analyzers.structure import StructureAnalyzer
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document(catalog: dict | None = None) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        catalog=catalog or {},
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestXFAForms:
    """Test GRD_STRUCT_006: XFA forms detection."""

    @staticmethod
    def test_xfa_detected() -> None:
        """AcroForm with /XFA triggers GRD_STRUCT_006."""
        doc = _make_document({"/AcroForm": {"/XFA": ["some", "xfa", "data"]}})
        findings = StructureAnalyzer().analyze(doc, [])
        xfa = [f for f in findings if f.inspection_id == "GRD_STRUCT_006"]
        assert len(xfa) == 1
        assert xfa[0].severity == Severity.ERROR

    @staticmethod
    def test_xfa_dict_value() -> None:
        """XFA with dict value also triggers."""
        doc = _make_document({"/AcroForm": {"/XFA": {"/data": "stream"}}})
        findings = StructureAnalyzer().analyze(doc, [])
        xfa = [f for f in findings if f.inspection_id == "GRD_STRUCT_006"]
        assert len(xfa) == 1

    @staticmethod
    def test_acroform_without_xfa_no_finding() -> None:
        """AcroForm without /XFA does not trigger GRD_STRUCT_006."""
        doc = _make_document({"/AcroForm": {"/Fields": [{}]}})
        findings = StructureAnalyzer().analyze(doc, [])
        xfa = [f for f in findings if f.inspection_id == "GRD_STRUCT_006"]
        assert len(xfa) == 0

    @staticmethod
    def test_no_acroform_no_finding() -> None:
        """No AcroForm does not trigger GRD_STRUCT_006."""
        doc = _make_document({})
        findings = StructureAnalyzer().analyze(doc, [])
        xfa = [f for f in findings if f.inspection_id == "GRD_STRUCT_006"]
        assert len(xfa) == 0

    @staticmethod
    def test_xfa_none_no_finding() -> None:
        """AcroForm with /XFA=None does not trigger GRD_STRUCT_006."""
        doc = _make_document({"/AcroForm": {"/XFA": None}})
        findings = StructureAnalyzer().analyze(doc, [])
        xfa = [f for f in findings if f.inspection_id == "GRD_STRUCT_006"]
        assert len(xfa) == 0


class TestTaggedPDF:
    """Test GRD_STRUCT_007: tagged PDF (structure tree)."""

    @staticmethod
    def test_mark_info_detected() -> None:
        """/MarkInfo in catalog triggers GRD_STRUCT_007."""
        doc = _make_document({"/MarkInfo": {"/Marked": True}})
        findings = StructureAnalyzer().analyze(doc, [])
        tag = [f for f in findings if f.inspection_id == "GRD_STRUCT_007"]
        assert len(tag) == 1
        assert tag[0].severity == Severity.ADVISORY
        assert tag[0].details["has_mark_info"] is True

    @staticmethod
    def test_struct_tree_root_detected() -> None:
        """/StructTreeRoot in catalog triggers GRD_STRUCT_007."""
        doc = _make_document({"/StructTreeRoot": {"/Type": "/StructTreeRoot"}})
        findings = StructureAnalyzer().analyze(doc, [])
        tag = [f for f in findings if f.inspection_id == "GRD_STRUCT_007"]
        assert len(tag) == 1
        assert tag[0].details["has_struct_tree"] is True

    @staticmethod
    def test_both_mark_and_tree() -> None:
        """Both /MarkInfo and /StructTreeRoot produce one finding."""
        doc = _make_document(
            {
                "/MarkInfo": {"/Marked": True},
                "/StructTreeRoot": {"/Type": "/StructTreeRoot"},
            }
        )
        findings = StructureAnalyzer().analyze(doc, [])
        tag = [f for f in findings if f.inspection_id == "GRD_STRUCT_007"]
        assert len(tag) == 1
        assert tag[0].details["has_mark_info"] is True
        assert tag[0].details["has_struct_tree"] is True

    @staticmethod
    def test_no_tagging_no_finding() -> None:
        """Empty catalog does not trigger GRD_STRUCT_007."""
        doc = _make_document({})
        findings = StructureAnalyzer().analyze(doc, [])
        tag = [f for f in findings if f.inspection_id == "GRD_STRUCT_007"]
        assert len(tag) == 0
