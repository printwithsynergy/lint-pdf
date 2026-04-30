"""Tests for StructureAnalyzer — document structure feature detection."""

from __future__ import annotations

from siftpdf.analyzers.finding import Severity
from siftpdf.analyzers.structure import StructureAnalyzer
from siftpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_document(catalog: dict | None = None) -> SemanticDocument:
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        catalog=catalog or {},
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestJavaScript:
    @staticmethod
    def test_js_in_names() -> None:
        doc = _make_document({"/Names": {"/JavaScript": {"some": "js"}}})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_001" in ids

    @staticmethod
    def test_js_in_open_action() -> None:
        doc = _make_document({"/OpenAction": {"/S": "/JavaScript", "/JS": "alert()"}})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_001" in ids

    @staticmethod
    def test_js_in_aa() -> None:
        doc = _make_document({"/AA": {"/WC": {"/S": "/JavaScript"}}})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_001" in ids

    @staticmethod
    def test_no_js_clean() -> None:
        doc = _make_document({})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_001" not in ids

    @staticmethod
    def test_js_severity_aground() -> None:
        doc = _make_document({"/Names": {"/JavaScript": {}}})
        findings = [
            f for f in StructureAnalyzer().analyze(doc, []) if f.inspection_id == "LPDF_STRUCT_001"
        ]
        assert findings[0].severity == Severity.ERROR


class TestFormFields:
    @staticmethod
    def test_form_fields_detected() -> None:
        doc = _make_document({"/AcroForm": {"/Fields": [{}, {}]}})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_002" in ids

    @staticmethod
    def test_empty_fields_no_finding() -> None:
        doc = _make_document({"/AcroForm": {"/Fields": []}})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_002" not in ids


class TestLayers:
    @staticmethod
    def test_ocg_detected() -> None:
        doc = _make_document({"/OCProperties": {"/OCGs": [{}, {}, {}]}})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_003" in ids

    @staticmethod
    def test_no_ocg_clean() -> None:
        doc = _make_document({})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_003" not in ids


class TestEmbeddedFiles:
    @staticmethod
    def test_embedded_files_detected() -> None:
        doc = _make_document({"/Names": {"/EmbeddedFiles": {"some": "tree"}}})
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_004" in ids


class TestThreeDContent:
    @staticmethod
    def test_3d_annotation() -> None:
        doc = SemanticDocument(
            version="1.7",
            page_count=1,
            is_encrypted=False,
            pages=[
                SemanticPage(
                    page_num=1,
                    media_box=PdfBox(0, 0, 612, 792),
                    resources={"/Annots": [{"/Subtype": "/3D"}]},
                )
            ],
        )
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_005" in ids

    @staticmethod
    def test_no_3d_clean() -> None:
        doc = _make_document()
        findings = StructureAnalyzer().analyze(doc, [])
        ids = [f.inspection_id for f in findings]
        assert "LPDF_STRUCT_005" not in ids
