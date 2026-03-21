"""Tests for IccProfileAnalyzer."""
from grounded.analyzers.icc_profile_analyzer import IccProfileAnalyzer
from grounded.analyzers.finding import Severity
from grounded.semantic.model import (
    SemanticDocument, SemanticPage, PdfBox, PdfColorSpace,
)

def _make_doc(output_intents=None, color_spaces=None):
    """Build a minimal SemanticDocument for testing."""
    page_cs = color_spaces or {}
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=page_cs,
    )
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        output_intents=output_intents or [],
        pages=[page],
    )

class TestIccProfileAnalyzer:
    def test_no_findings_on_clean_document(self):
        doc = _make_doc()
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        # No ICCBased spaces, no output intents = no ICC findings
        icc_findings = [f for f in findings if f.inspection_id.startswith("GRD_ICC_")]
        assert len(icc_findings) == 0

    def test_valid_icc_based_color_space(self):
        cs = PdfColorSpace(name="CS1", cs_type="ICCBased", components=4, icc_profile_ref="profile_1")
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        # Should have ICC_002 advisory for detected profile
        icc_002 = [f for f in findings if f.inspection_id == "GRD_ICC_002"]
        assert len(icc_002) >= 1

    def test_invalid_icc_component_count(self):
        cs = PdfColorSpace(name="CS1", cs_type="ICCBased", components=5, icc_profile_ref="profile_1")
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_001 = [f for f in findings if f.inspection_id == "GRD_ICC_001"]
        assert len(icc_001) >= 1
        assert icc_001[0].severity == Severity.AGROUND

    def test_missing_icc_profile_ref(self):
        cs = PdfColorSpace(name="CS1", cs_type="ICCBased", components=3, icc_profile_ref=None)
        doc = _make_doc(color_spaces={"CS1": cs})
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_003 = [f for f in findings if f.inspection_id == "GRD_ICC_003"]
        assert len(icc_003) >= 1
        assert icc_003[0].severity == Severity.AGROUND

    def test_output_intent_validation(self):
        doc = _make_doc(output_intents=[
            {"S": "GTS_PDFX", "OutputConditionIdentifier": "FOGRA39"}
        ])
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_005 = [f for f in findings if f.inspection_id == "GRD_ICC_005"]
        assert len(icc_005) >= 1

    def test_invalid_output_intent(self):
        doc = _make_doc(output_intents=[{"S": "INVALID_TYPE"}])
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_004 = [f for f in findings if f.inspection_id == "GRD_ICC_004"]
        assert len(icc_004) >= 1
        assert icc_004[0].severity == Severity.SQUALL

    def test_multiple_inconsistent_output_intents(self):
        doc = _make_doc(output_intents=[
            {"S": "GTS_PDFX", "OutputConditionIdentifier": "FOGRA39"},
            {"S": "GTS_PDFA1", "OutputConditionIdentifier": "sRGB"},
        ])
        analyzer = IccProfileAnalyzer()
        findings = analyzer.analyze(doc, [])
        icc_006 = [f for f in findings if f.inspection_id == "GRD_ICC_006"]
        assert len(icc_006) >= 1
