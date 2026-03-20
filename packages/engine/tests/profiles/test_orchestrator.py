"""Tests for PreflightOrchestrator."""

from __future__ import annotations

# skipcq: PYL-R0201
from grounded.analyzers.finding import Severity
from grounded.profiles.orchestrator import PreflightOrchestrator, PreflightResult
from grounded.profiles.schema import CheckConfig, ThresholdConfig, VoyagePlan
from grounded.semantic.model import PdfBox, PdfFont, SemanticDocument, SemanticPage


def _minimal_doc(
    fonts: dict[str, PdfFont] | None = None,
) -> SemanticDocument:
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(10, 10, 602, 782),
        fonts=fonts or {},
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


class TestOrchestratorOnDocument:
    def test_basic_run(self) -> None:
        fp = VoyagePlan(name="Test")
        orch = PreflightOrchestrator(fp, profile_id="test")
        result = orch.run_on_document(_minimal_doc(), [])

        assert isinstance(result, PreflightResult)
        assert result.profile_id == "test"
        assert result.summary.page_count == 1
        assert result.summary.file_size_bytes == 0
        assert result.duration_ms >= 0
        assert result.metadata["pdf_version"] == "1.7"

    def test_findings_populated(self) -> None:
        # A doc with an unembedded font should trigger GRD_FONT_001
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = VoyagePlan(name="Test")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])

        font_findings = [f for f in result.findings if f.inspection_id == "GRD_FONT_001"]
        assert len(font_findings) >= 1
        assert result.summary.total_findings > 0

    def test_check_filtering(self) -> None:
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = VoyagePlan(
            name="Test",
            checks=CheckConfig(disabled=["GRD_FONT_*"]),
        )
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])

        font_findings = [f for f in result.findings if f.inspection_id.startswith("GRD_FONT")]
        assert len(font_findings) == 0

    def test_severity_override(self) -> None:
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = VoyagePlan(
            name="Test",
            checks=CheckConfig(
                severity_overrides={"GRD_FONT_001": "advisory"},
            ),
        )
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])

        font_findings = [f for f in result.findings if f.inspection_id == "GRD_FONT_001"]
        assert len(font_findings) >= 1
        assert all(f.severity == Severity.ADVISORY for f in font_findings)

    def test_passed_when_no_aground(self) -> None:
        fp = VoyagePlan(name="Test")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(), [])
        # Minimal doc should have no AGROUND
        assert result.summary.passed is True

    def test_failed_when_aground(self) -> None:
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = VoyagePlan(name="Test")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])
        assert result.summary.aground_count > 0
        assert result.summary.passed is False

    def test_conformance_pdfx4(self) -> None:
        fp = VoyagePlan(name="Test", conformance="pdfx4")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(), [])
        # Should include PDFX4 findings (e.g. missing XMP, output intent)
        pdfx4_findings = [f for f in result.findings if f.inspection_id.startswith("PDFX4")]
        assert len(pdfx4_findings) > 0

    def test_no_conformance_no_pdfx4(self) -> None:
        fp = VoyagePlan(name="Test", conformance=None)
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(), [])
        pdfx4_findings = [f for f in result.findings if f.inspection_id.startswith("PDFX4")]
        assert len(pdfx4_findings) == 0

    def test_threshold_propagation(self) -> None:
        # Use high min_dpi so even 300dpi images would fail
        fp = VoyagePlan(
            name="Test",
            thresholds=ThresholdConfig(min_dpi=9999.0),
        )
        orch = PreflightOrchestrator(fp)
        # Just verify it runs without error
        result = orch.run_on_document(_minimal_doc(), [])
        assert isinstance(result, PreflightResult)
