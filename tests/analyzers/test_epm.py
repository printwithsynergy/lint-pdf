"""Tests for EpmAnalyzer."""

from lintpdf.analyzers.epm_analyzer import EpmAnalyzer
from lintpdf.analyzers.finding import Severity
from lintpdf.semantic.events import PathPaintingEvent, TextRenderedEvent
from lintpdf.semantic.graphics_state import TransformationMatrix
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _make_doc():
    return SemanticDocument(
        version="2.0",
        page_count=1,
        is_encrypted=False,
        pages=[SemanticPage(page_num=1, media_box=PdfBox(0, 0, 612, 792))],
    )


class TestEpmAnalyzer:
    def test_no_findings_for_cmy_only_file(self):
        # PathPaintingEvent with no K channel
        events = [
            PathPaintingEvent(
                operator="f",
                page_num=1,
                operator_index=0,
                fill=True,
                stroke=False,
                fill_color_space="DeviceCMYK",
                fill_color_values=(0.5, 0.3, 0.2, 0.0),
            )
        ]
        analyzer = EpmAnalyzer()
        findings = analyzer.analyze(_make_doc(), events)
        epm_002 = [f for f in findings if f.inspection_id == "LPDF_EPM_002"]
        assert len(epm_002) == 0

    def test_pure_black_text_detected(self):
        events = [
            TextRenderedEvent(
                operator="Tj",
                page_num=1,
                operator_index=0,
                font_name="F1",
                font_size=12.0,
                color_space="DeviceCMYK",
                color_values=(0.0, 0.0, 0.0, 1.0),
                ctm=TransformationMatrix(1, 0, 0, 1, 72, 700),
                text_matrix=TransformationMatrix.identity(),
            )
        ]
        analyzer = EpmAnalyzer()
        findings = analyzer.analyze(_make_doc(), events)
        epm_002 = [f for f in findings if f.inspection_id == "LPDF_EPM_002"]
        assert len(epm_002) >= 1
        assert epm_002[0].severity == Severity.ERROR

    def test_k_channel_usage_detected(self):
        events = [
            PathPaintingEvent(
                operator="f",
                page_num=1,
                operator_index=0,
                fill=True,
                stroke=False,
                fill_color_space="DeviceCMYK",
                fill_color_values=(0.2, 0.3, 0.1, 0.5),
            )
        ]
        analyzer = EpmAnalyzer()
        findings = analyzer.analyze(_make_doc(), events)
        epm_001 = [f for f in findings if f.inspection_id == "LPDF_EPM_001"]
        assert len(epm_001) >= 1
