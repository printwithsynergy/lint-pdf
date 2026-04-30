"""Tests for PreflightOrchestrator."""

from __future__ import annotations

from lintpdf.analyzers.finding import Severity
from lintpdf.profiles.orchestrator import PreflightOrchestrator, PreflightResult
from lintpdf.profiles.schema import CheckConfig, PreflightProfile, ThresholdConfig
from lintpdf.semantic.model import PdfBox, PdfFont, SemanticDocument, SemanticPage


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
    @staticmethod
    def test_basic_run() -> None:
        fp = PreflightProfile(name="Test")
        orch = PreflightOrchestrator(fp, profile_id="test")
        result = orch.run_on_document(_minimal_doc(), [])

        assert isinstance(result, PreflightResult)
        assert result.profile_id == "test"
        assert result.summary.page_count == 1
        assert result.summary.file_size_bytes == 0
        assert result.duration_ms >= 0
        assert result.metadata["pdf_version"] == "1.7"

    @staticmethod
    def test_findings_populated() -> None:
        # A doc with an unembedded font should trigger LPDF_FONT_001
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = PreflightProfile(name="Test")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])

        font_findings = [f for f in result.findings if f.inspection_id == "LPDF_FONT_001"]
        assert len(font_findings) >= 1
        assert result.summary.total_findings > 0

    @staticmethod
    def test_check_filtering() -> None:
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = PreflightProfile(
            name="Test",
            checks=CheckConfig(disabled=["LPDF_FONT_*"]),
        )
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])

        font_findings = [f for f in result.findings if f.inspection_id.startswith("LPDF_FONT")]
        assert len(font_findings) == 0

    @staticmethod
    def test_severity_override() -> None:
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = PreflightProfile(
            name="Test",
            checks=CheckConfig(
                severity_overrides={"LPDF_FONT_001": "advisory"},
            ),
        )
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])

        font_findings = [f for f in result.findings if f.inspection_id == "LPDF_FONT_001"]
        assert len(font_findings) >= 1
        assert all(f.severity == Severity.ADVISORY for f in font_findings)

    @staticmethod
    def test_passed_when_no_aground() -> None:
        fp = PreflightProfile(name="Test")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(), [])
        # Minimal doc should have no AGROUND
        assert result.summary.passed is True

    @staticmethod
    def test_failed_when_aground() -> None:
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )
        fp = PreflightProfile(name="Test")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(fonts={"F1": font}), [])
        assert result.summary.error_count > 0
        assert result.summary.passed is False

    @staticmethod
    def test_conformance_pdfx4() -> None:
        fp = PreflightProfile(name="Test", conformance="pdfx4")
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(), [])
        # Should include PDFX4 findings (e.g. missing XMP, output intent)
        pdfx4_findings = [f for f in result.findings if f.inspection_id.startswith("PDFX4")]
        assert len(pdfx4_findings) > 0

    @staticmethod
    def test_no_conformance_no_pdfx4() -> None:
        fp = PreflightProfile(name="Test", conformance=None)
        orch = PreflightOrchestrator(fp)
        result = orch.run_on_document(_minimal_doc(), [])
        pdfx4_findings = [f for f in result.findings if f.inspection_id.startswith("PDFX4")]
        assert len(pdfx4_findings) == 0

    @staticmethod
    def test_threshold_propagation() -> None:
        # Use high min_dpi so even 300dpi images would fail
        fp = PreflightProfile(
            name="Test",
            thresholds=ThresholdConfig(min_dpi=9999.0),
        )
        orch = PreflightOrchestrator(fp)
        # Just verify it runs without error
        result = orch.run_on_document(_minimal_doc(), [])
        assert isinstance(result, PreflightResult)

    @staticmethod
    def test_epm_substrate_path_forwarded_to_tier_a_analyzer() -> None:
        """Orchestrator reads epm_substrate_profile_path from
        ThresholdConfig and constructs EpmTierAAnalyzer with it."""
        fp = PreflightProfile(
            name="Test",
            thresholds=ThresholdConfig(
                epm_mode=True,
                epm_substrate_class="uncoated_heavy",
                epm_substrate_profile_path="/var/lib/lintpdf/profiles/coated.icc",
            ),
        )
        orch = PreflightOrchestrator(fp)
        analyzers = orch._create_analyzers()
        from lintpdf.analyzers.epm_v2_a import EpmTierAAnalyzer

        tier_a = next((a for a in analyzers if isinstance(a, EpmTierAAnalyzer)), None)
        assert tier_a is not None, "EpmTierAAnalyzer was not registered"
        assert tier_a._substrate_class == "uncoated_heavy"
        assert tier_a._substrate_profile_path == "/var/lib/lintpdf/profiles/coated.icc"
