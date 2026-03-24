"""Tests for EcgAnalyzer."""

from lintpdf.analyzers.ecg_analyzer import EcgAnalyzer
from lintpdf.semantic.model import PdfBox, PdfColorSpace, SemanticDocument, SemanticPage


def _make_doc(color_spaces=None):
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        color_spaces=color_spaces or {},
    )
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


class TestEcgAnalyzer:
    def test_no_findings_without_spot_colors(self):
        doc = _make_doc()
        findings = EcgAnalyzer().analyze(doc, [])
        ecg = [f for f in findings if f.inspection_id.startswith("LPDF_ECG_")]
        # Should get readiness advisory
        assert any(f.inspection_id == "LPDF_ECG_001" for f in ecg)

    def test_spot_colors_detected(self):
        cs = PdfColorSpace(
            name="CS1",
            cs_type="Separation",
            components=1,
            colorant_names=("PANTONE 485 C",),
        )
        doc = _make_doc(color_spaces={"CS1": cs})
        findings = EcgAnalyzer().analyze(doc, [])
        ecg_001 = [f for f in findings if f.inspection_id == "LPDF_ECG_001"]
        assert len(ecg_001) >= 1
