"""Tests for ProcessingStepAnalyzer — OCG layer detection."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.analyzers.finding import Severity
from grounded.analyzers.processing import ProcessingStepAnalyzer
from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage


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


class TestProcessingStepLayers:
    """Test GRD_PROC_001: Processing step layers detected."""

    def test_dieline_layer_detected(self) -> None:
        doc = _make_document(
            catalog={
                "/OCProperties": {
                    "/OCGs": [{"/Name": "Dieline"}],
                }
            }
        )
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY
        assert "Dieline" in f[0].details["layer_names"]

    def test_varnish_layer_detected(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "Spot Varnish"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 1

    def test_foil_layer_detected(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "Gold Foil Layer"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 1

    def test_cut_contour_detected(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "CutContour"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 1

    def test_cut_contour_with_space(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "Cut Contour"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 1

    def test_no_processing_layers(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "Background Image"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 0

    def test_no_oc_properties(self) -> None:
        doc = _make_document(catalog={})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        assert len(findings) == 0

    def test_multiple_layers_single_finding(self) -> None:
        doc = _make_document(
            catalog={
                "/OCProperties": {
                    "/OCGs": [
                        {"/Name": "Dieline"},
                        {"/Name": "Varnish"},
                        {"/Name": "White Ink"},
                    ]
                }
            }
        )
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 1
        assert f[0].details["layer_count"] == 3

    def test_case_insensitive_matching(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "DIELINE"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_001"]
        assert len(f) == 1


class TestWhiteInkLayer:
    """Test GRD_PROC_002: White ink layer detected."""

    def test_white_ink_layer_flagged(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "White Ink"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_002"]
        assert len(f) == 1
        assert f[0].severity == Severity.ADVISORY

    def test_white_in_name_flagged(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "White"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_002"]
        assert len(f) == 1

    def test_non_white_layer_no_flag(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"/Name": "Varnish"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        f = [f for f in findings if f.inspection_id == "GRD_PROC_002"]
        assert len(f) == 0

    def test_ocg_without_name_skipped(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": [{"Type": "OCG"}]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        assert len(findings) == 0

    def test_non_dict_ocg_skipped(self) -> None:
        doc = _make_document(catalog={"/OCProperties": {"/OCGs": ["not_a_dict"]}})
        analyzer = ProcessingStepAnalyzer()
        findings = analyzer.analyze(doc, [])
        assert len(findings) == 0
