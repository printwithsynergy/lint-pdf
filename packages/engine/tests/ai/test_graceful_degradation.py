"""Tests for graceful degradation when GPU service is unavailable.

Verifies that:
1. Circuit breaker prevents cascading failures
2. Advisory findings are returned when GPU is down
3. Rule-based (engine) findings are unaffected by GPU failures
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from grounded.ai.gpu_client import CircuitBreaker, GPUInferenceClient, GPUServiceUnavailableError
from grounded.profiles.orchestrator import PreflightOrchestrator, PreflightResult
from grounded.profiles.schema import AIFeatureConfig, CheckConfig, PreflightProfile
from grounded.semantic.model import PdfBox, PdfFont, SemanticDocument, SemanticPage


def _minimal_doc(fonts: dict[str, PdfFont] | None = None) -> SemanticDocument:
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


class TestGPUUnavailableProducesAdvisory:
    """When the GPU service is down, AI analyzers should produce advisory findings
    rather than crashing the pipeline."""

    @staticmethod
    def test_circuit_breaker_open_returns_advisory_finding() -> None:
        """An AI analyzer that uses the GPU client should handle GPUServiceUnavailableError
        and the orchestrator should catch any exceptions gracefully."""
        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=True, categories=["all"]),
            checks=CheckConfig(enabled=["GRD_*", "AI_*"]),
        )

        # Simulate an analyzer that raises when GPU is down
        mock_analyzer = MagicMock()
        mock_analyzer.category = "image_quality"
        mock_analyzer.feature_slug = "image_quality_assessment"
        mock_analyzer.analyze.side_effect = GPUServiceUnavailableError(
            "GPU circuit breaker is open"
        )

        doc = _minimal_doc()

        with patch(
            "grounded.ai.registry.get_ai_analyzers",
            return_value=[mock_analyzer],
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        # Pipeline should complete successfully
        assert isinstance(result, PreflightResult)
        # The AI exception was caught, so 0 AI findings
        assert result.metadata["ai_findings_count"] == 0


class TestRuleBasedFindingsUnaffected:
    """Engine (rule-based) findings should be produced regardless of GPU state."""

    @staticmethod
    def test_engine_findings_present_despite_gpu_failure() -> None:
        """Even when AI analyzers fail, engine analyzers should produce findings."""
        font = PdfFont(
            name="F1",
            base_font="Arial",
            font_type="TrueType",
            embedded=False,
            subset=False,
        )

        fp = PreflightProfile(
            name="Test",
            ai=AIFeatureConfig(enabled=True, categories=["all"]),
        )

        mock_analyzer = MagicMock()
        mock_analyzer.category = "image_quality"
        mock_analyzer.feature_slug = "image_quality"
        mock_analyzer.analyze.side_effect = GPUServiceUnavailableError("GPU down")

        doc = _minimal_doc(fonts={"F1": font})

        with patch(
            "grounded.ai.registry.get_ai_analyzers",
            return_value=[mock_analyzer],
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        # Engine findings (unembedded font) should still be present
        engine_findings = [f for f in result.findings if f.source == "engine"]
        assert len(engine_findings) > 0
        font_findings = [f for f in engine_findings if f.inspection_id == "GRD_FONT_001"]
        assert len(font_findings) >= 1


class TestCircuitBreakerIntegration:
    """Integration-level tests for circuit breaker behavior."""

    @staticmethod
    def test_circuit_opens_after_three_failures() -> None:
        cb = CircuitBreaker(failure_threshold=3, failure_window_seconds=60.0)
        assert cb.state == "closed"

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

        cb.record_failure()
        assert cb.state == "open"

        with pytest.raises(GPUServiceUnavailableError):
            cb.check()

    @staticmethod
    def test_successful_probe_closes_circuit() -> None:
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        cb.record_success()
        assert cb.state == "closed"

        # Should not raise
        cb.check()

    @staticmethod
    def test_multiple_analyzers_share_client_breaker() -> None:
        """All GPU method calls on a single client share the same circuit breaker."""
        import httpx

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.post.side_effect = httpx.ConnectError("refused")

            client = GPUInferenceClient("http://gpu:8080", timeout=1.0)

            # 3 failures across different methods
            with pytest.raises(GPUServiceUnavailableError):
                client.assess_image_quality(b"img")
            with pytest.raises(GPUServiceUnavailableError):
                client.classify_document(b"img")
            with pytest.raises(GPUServiceUnavailableError):
                client.detect_logos(b"img")

            # Circuit should now be open
            assert client._breaker.state == "open"

            # Next call should fail fast (circuit open)
            mock_client_cls.return_value.post.reset_mock()
            with pytest.raises(GPUServiceUnavailableError, match="circuit breaker"):
                client.detect_nsfw(b"img")
            mock_client_cls.return_value.post.assert_not_called()
