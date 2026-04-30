"""Integration test — orchestrator dispatches to a REAL AI analyzer.

This test exists because the Phase 2 alpha-stream migration shipped a
production-breaking regression (PR #357 onward, fixed in PR #368): the
orchestrator at ``profiles/orchestrator.py`` called the legacy 4-arg
``analyzer.analyze(...)`` shape, while migrated analyzers only
overrode ``analyze_v2(ctx)``. The default ``analyze`` raised
``NotImplementedError``, the orchestrator's ``except`` caught it, and
every AI finding was silently dropped in production.

The pre-existing test suite did not catch the regression because:

1. Per-analyzer unit tests call ``analyze_v2(_ctx(...))`` directly,
   bypassing the orchestrator.
2. ``tests/ai/test_orchestrator_ai.py`` uses ``MagicMock``, which
   auto-creates ``.analyze`` and ``.analyze_v2`` attributes
   regardless of which one the orchestrator actually calls.

This test runs a REAL registered AI analyzer
(``AlcoholLabelingAnalyzer`` — chosen because it's pure CPU, has
zero external dependencies, and reads only ``document.pages[].
content_stream``) through the full ``PreflightOrchestrator`` dispatch
path. If the orchestrator stops calling ``analyze_v2`` correctly (or
the analyzer's contract changes in a way that breaks dispatch), this
test fails with a finding-count mismatch — surfacing the regression
before deploy.

This is the "functionality preservation gate" for the analyze_v2
dispatch path. Future plugin-protocol changes that touch how the
orchestrator constructs ``AnalyzerContext`` MUST keep this test
green.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lintpdf.profiles.orchestrator import PreflightOrchestrator
from lintpdf.profiles.schema import AIFeatureConfig, CheckConfig, PreflightProfile
from lintpdf.semantic.model import PdfBox, SemanticDocument, SemanticPage


def _doc_with_alcohol_text(text: str) -> SemanticDocument:
    """Build a single-page SemanticDocument whose content stream
    contains arbitrary literal text. The Alcohol analyzer reads
    ``page.content_stream`` and matches against ABV / class
    keyword patterns; embedding the text directly gives us a
    deterministic input."""
    page = SemanticPage(
        page_num=1,
        media_box=PdfBox(0, 0, 612, 792),
        content_stream=text.encode("latin-1"),
    )
    return SemanticDocument(
        version="1.7",
        page_count=1,
        is_encrypted=False,
        pages=[page],
    )


class TestOrchestratorDispatchesToAnalyzeV2:
    """The orchestrator MUST call analyze_v2(ctx) on registered AI
    analyzers. If it falls back to legacy analyze() — which raises
    NotImplementedError on migrated analyzers — every AI finding is
    silently swallowed.
    """

    @staticmethod
    def test_real_alcohol_analyzer_emits_findings_via_orchestrator() -> None:
        """A document with an alcohol class keyword + ABV but no TTB
        warning + no country of origin must produce ``AI_ALC_001``
        through the full orchestrator dispatch path. If the
        orchestrator silently drops findings (the regression fixed
        in PR #368), we'd get only ``AI_SCAN_001`` and the assertion
        would fail."""
        from lintpdf.ai.analyzers.regulatory_compliance.alcohol import (
            AlcoholLabelingAnalyzer,
        )

        doc = _doc_with_alcohol_text("(Cabernet Sauvignon) Tj (12.5% ALC/VOL) Tj (Vintage 2020) Tj")

        fp = PreflightProfile(
            name="orchestrator-dispatch-test",
            ai=AIFeatureConfig(enabled=True, categories=["regulatory_compliance"]),
            checks=CheckConfig(enabled=["AI_*"]),
        )

        # Register only the real Alcohol analyzer so the test isolates
        # one analyzer's path through the orchestrator.
        analyzer = AlcoholLabelingAnalyzer()

        with (
            patch(
                "lintpdf.ai.registry.get_ai_analyzers",
                return_value=[analyzer],
            ),
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        ai_alc_findings = [f for f in result.findings if f.inspection_id == "AI_ALC_001"]
        assert len(ai_alc_findings) == 1, (
            "Expected exactly one AI_ALC_001 finding from the Alcohol analyzer "
            "running through the orchestrator. Zero findings means the "
            "orchestrator's analyze_v2 dispatch path is broken (see PR #368)."
        )

        # Sanity-check: the orchestrator's audit-trail marker must also
        # be present, confirming the AI pipeline ran.
        ai_scan_markers = [f for f in result.findings if f.inspection_id == "AI_SCAN_001"]
        assert len(ai_scan_markers) == 1

        # Metadata accounting: at least 1 ALC finding + 1 SCAN audit
        # marker. The Alcohol analyzer may emit additional T5 / format
        # findings depending on the input — the regression we're guarding
        # against produces 1 (only SCAN), not "at least 2".
        assert result.metadata["ai_enabled"] is True
        assert result.metadata["ai_findings_count"] >= 2

    @staticmethod
    def test_real_analyzer_with_no_match_returns_only_audit_marker() -> None:
        """A document that doesn't trigger alcohol detection (no ABV
        pattern, no class keyword) must return zero AI_ALC findings,
        but the AI_SCAN_001 audit marker must still fire — the
        analyzer ran, it just had nothing to report. This confirms
        the orchestrator dispatched the analyzer (vs. silently
        skipping it)."""
        from lintpdf.ai.analyzers.regulatory_compliance.alcohol import (
            AlcoholLabelingAnalyzer,
        )

        doc = _doc_with_alcohol_text("(Just some plain marketing copy with no alcohol terms.) Tj")

        fp = PreflightProfile(
            name="orchestrator-dispatch-test-empty",
            ai=AIFeatureConfig(enabled=True, categories=["regulatory_compliance"]),
            checks=CheckConfig(enabled=["AI_*"]),
        )

        analyzer = AlcoholLabelingAnalyzer()

        with patch(
            "lintpdf.ai.registry.get_ai_analyzers",
            return_value=[analyzer],
        ):
            orch = PreflightOrchestrator(fp, profile_id="test", pdf_bytes=b"fake")
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        assert [f for f in result.findings if f.inspection_id == "AI_ALC_001"] == []
        assert len([f for f in result.findings if f.inspection_id == "AI_SCAN_001"]) == 1

    @staticmethod
    def test_orchestrator_passes_ai_config_through_to_analyzer() -> None:
        """The orchestrator must serialise ai_config into ctx.config
        so reconstitution-based analyzers (cosmetics, eu_fir, etc.)
        see their gating attributes. Verifies the PR #368 fix's
        model_dump call survives — a bug here would cause
        is_cosmetic_applicable / is_eu_food_applicable / etc. to
        receive ``None`` and either over-fire or under-fire.

        Uses CosmeticsLabelingAnalyzer because it's the cleanest
        ai_config-gated analyzer — passing ``industry_type=
        dietary_supplement`` should suppress its findings.
        """
        from lintpdf.ai.analyzers.regulatory_compliance.cosmetics import (
            CosmeticsLabelingAnalyzer,
        )

        # Document text that WOULD trigger AI_COSM_001 if the gate
        # weren't engaged. Includes INCI header + a cosmetic-class
        # keyword + missing PAO/batch/etc.
        doc = _doc_with_alcohol_text(
            "(Shampoo) Tj (INGREDIENTS:) Tj (Aqua, Sodium Laureth Sulfate) Tj"
        )

        fp = PreflightProfile(
            name="orchestrator-dispatch-test-gated",
            ai=AIFeatureConfig(
                enabled=True,
                categories=["regulatory_compliance"],
            ),
            checks=CheckConfig(enabled=["AI_*"]),
        )

        analyzer = CosmeticsLabelingAnalyzer()

        # industry_type lives on the tenant's TenantAIConfig (passed
        # to the orchestrator separately), not on the PreflightProfile.
        # Stand in with a SimpleNamespace whose attributes mirror the
        # TenantAIConfig surface the analyzer reads.
        from types import SimpleNamespace

        ai_config = SimpleNamespace(
            industry_type="dietary_supplement",
            regulatory_market=None,
            brand_palette=None,
        )

        with patch(
            "lintpdf.ai.registry.get_ai_analyzers",
            return_value=[analyzer],
        ):
            orch = PreflightOrchestrator(
                fp, profile_id="test", ai_config=ai_config, pdf_bytes=b"fake"
            )
            with patch.object(orch, "_parse_and_interpret", return_value=(doc, [])):
                result = orch.run(b"fake")

        # is_cosmetic_applicable returns False for industry_type=
        # dietary_supplement, so the cosmetic analyzer should bail
        # out before producing any AI_COSM_* findings. If ai_config
        # isn't piped through ctx, it'd return None and the analyzer
        # would over-fire.
        cosm_findings = [f for f in result.findings if f.inspection_id.startswith("AI_COSM")]
        assert cosm_findings == [], (
            "Cosmetic analyzer fired despite industry_type=dietary_supplement "
            "— ai_config is not flowing through orchestrator's ctx.config."
        )


if __name__ == "__main__":  # pragma: no cover — convenience entry point
    pytest.main([__file__, "-xvs"])
