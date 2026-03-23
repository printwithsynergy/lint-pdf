"""Tests for PreflightOrchestrator AI integration.

Verifies that the orchestrator runs AI analyzers when configured,
merges AI findings with engine findings, and tags AI findings correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from grounded.analyzers.finding import Finding, Severity
from grounded.profiles.orchestrator import PreflightOrchestrator, PreflightResult
from grounded.profiles.schema import AIFeatureConfig, CheckConfig, PreflightProfile


def _minimal_doc() -> MagicMock:
    """Create a minimal SemanticDocument mock."""
    from grounded.semantic.model import PdfBox, SemanticDocument, SemanticPage

    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        trim_box=PdfBox(10, 10, 602, 782),
        fonts={},
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


def _ai_finding(
    inspection_id: str = "AI_TEST_001",
    severity: Severity = Severity.ADVISORY,
    category: str = "test_category",
) -> Finding:
    """Create a sample AI finding."""
    return Finding(
        inspection_id=inspection_id,
        severity=severity,
        message=f"Test AI finding: {inspection_id}",
        source="ai",
        category=category,
    )


class TestOrchestratorWithAI:
    """Tests for AI analyzer integration in orchestrator."""

    @staticmethod
    def test_ai_disabled_produces_no_ai_findings() -> None:
        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=False),
        )
        orch = PreflightOrchestrator(fp, profile_id="test")
        result = orch.run_on_document(_minimal_doc(), [])

        ai_findings = [f for f in result.findings if f.source == "ai"]
        assert len(ai_findings) == 0

    @staticmethod
    def test_ai_enabled_runs_analyzers() -> None:
        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=True, categories=["all"]),
            checks=CheckConfig(enabled=["GRD_*", "AI_*"]),
        )

        mock_analyzer = MagicMock()
        mock_analyzer.category = "barcode"
        mock_analyzer.feature_slug = "barcode_decode"
        mock_analyzer.analyze.return_value = [_ai_finding("GRD_BC_001", category="barcode")]

        doc = _minimal_doc()

        with patch(
            "grounded.ai.registry.get_ai_analyzers",
            return_value=[mock_analyzer],
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        assert result.metadata["ai_enabled"] is True
        assert result.metadata["ai_findings_count"] == 1
        mock_analyzer.analyze.assert_called_once()

    @staticmethod
    def test_ai_findings_merged_with_engine_findings() -> None:
        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=True, categories=["barcode"]),
            checks=CheckConfig(enabled=["GRD_*", "AI_*"]),
        )

        ai_finding = _ai_finding("AI_BC_001", category="barcode")

        mock_analyzer = MagicMock()
        mock_analyzer.category = "barcode"
        mock_analyzer.feature_slug = "barcode_decode"
        mock_analyzer.analyze.return_value = [ai_finding]

        doc = _minimal_doc()

        with patch(
            "grounded.ai.registry.get_ai_analyzers",
            return_value=[mock_analyzer],
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            # Patch _parse_and_interpret to return our mock doc
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        # Should have both engine and AI findings
        ai_results = [f for f in result.findings if f.source == "ai"]
        assert len(ai_results) == 1
        assert ai_results[0].inspection_id == "AI_BC_001"
        assert ai_results[0].category == "barcode"

        # Metadata should report AI info
        assert result.metadata["ai_enabled"] is True
        assert result.metadata["ai_findings_count"] == 1

    @staticmethod
    def test_ai_analyzer_exception_caught() -> None:
        """If an AI analyzer throws, it should not crash the pipeline."""
        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=True, categories=["all"]),
            checks=CheckConfig(enabled=["GRD_*", "AI_*"]),
        )

        mock_analyzer = MagicMock()
        mock_analyzer.category = "barcode"
        mock_analyzer.feature_slug = "barcode_decode"
        mock_analyzer.analyze.side_effect = RuntimeError("GPU exploded")

        doc = _minimal_doc()

        with patch(
            "grounded.ai.registry.get_ai_analyzers",
            return_value=[mock_analyzer],
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        # Pipeline should succeed with 0 AI findings
        assert result.metadata["ai_findings_count"] == 0
        assert isinstance(result, PreflightResult)

    @staticmethod
    def test_ai_findings_have_correct_source_and_category() -> None:
        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=True, features=["spell_check"]),
            checks=CheckConfig(enabled=["GRD_*", "AI_*"]),
        )

        spell_finding = Finding(
            inspection_id="AI_SPELL_001",
            severity=Severity.ADVISORY,
            message="Misspelling: teh",
            source="ai",
            category="content_quality",
        )

        mock_analyzer = MagicMock()
        mock_analyzer.category = "content_quality"
        mock_analyzer.feature_slug = "spell_check"
        mock_analyzer.analyze.return_value = [spell_finding]

        doc = _minimal_doc()

        with patch(
            "grounded.ai.registry.get_ai_analyzers",
            return_value=[mock_analyzer],
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        ai_findings = [f for f in result.findings if f.source == "ai"]
        assert len(ai_findings) == 1
        assert ai_findings[0].source == "ai"
        assert ai_findings[0].category == "content_quality"

    @staticmethod
    def test_ai_import_error_handled_gracefully() -> None:
        """If AI modules are not installed, pipeline should still succeed."""
        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=True),
            checks=CheckConfig(enabled=["GRD_*"]),
        )

        doc = _minimal_doc()

        with patch(
            "grounded.ai.registry.get_ai_analyzers",
            side_effect=ImportError("no AI"),
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        assert isinstance(result, PreflightResult)
        assert result.metadata["ai_findings_count"] == 0
