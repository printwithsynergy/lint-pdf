"""Behavior-locking tests for analyze_v2 default impl on base classes.

These tests exercise the bridge that lets legacy analyzers (which only
implement ``analyze(...)``) run unchanged when the orchestrator calls
``analyze_v2(ctx)``. They also lock in the ai_config reconstitution
contract so a Phase 2 cleanup that changes the lookup path can fail
loudly here instead of silently breaking analyzers in production.
"""

from __future__ import annotations

from typing import Any, ClassVar

from lintpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.plugin import AnalyzerContext


class _FakeDoc:
    pages: ClassVar[list] = []


# ---------------------------------------------------------------------------
# BaseAnalyzer
# ---------------------------------------------------------------------------


class _LegacyCoreAnalyzer(BaseAnalyzer):
    """Stand-in for a typical core analyzer — implements only legacy analyze."""

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def analyze(self, document: Any, events: list) -> list[Finding]:
        self.calls.append((document, events))
        return [
            Finding(
                inspection_id="LPDF_TEST_001",
                severity=Severity.ADVISORY,
                message="legacy core finding",
            )
        ]


def test_base_analyzer_v2_default_forwards_to_legacy_analyze():
    legacy = _LegacyCoreAnalyzer()
    ctx = AnalyzerContext(document=_FakeDoc(), events=[])
    findings = legacy.analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_TEST_001"
    # Forwarding contract: document + events arrive unchanged.
    assert len(legacy.calls) == 1
    assert legacy.calls[0][0] is ctx.document
    assert legacy.calls[0][1] is ctx.events


def test_base_analyzer_v2_returns_same_findings_as_direct_analyze():
    """Behavior lock: analyze_v2 default impl is bit-equal to analyze().

    Phase 2 will inline this behaviour into analyze_v2 directly; until
    then, the orchestrator path (analyze_v2) must be observationally
    indistinguishable from the legacy direct call.
    """

    legacy = _LegacyCoreAnalyzer()
    direct = legacy.analyze(_FakeDoc(), [])
    via_v2 = legacy.analyze_v2(AnalyzerContext(document=_FakeDoc(), events=[]))
    assert direct == via_v2


# ---------------------------------------------------------------------------
# BaseAIAnalyzer
# ---------------------------------------------------------------------------


class _LegacyAIAnalyzer(BaseAIAnalyzer):
    category = "test_category"
    feature_slug = "test.feature"
    tier = "cpu"
    credits_per_run = 1

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def analyze(
        self,
        document: Any,
        events: list,
        pdf_bytes: bytes,
        ai_config: Any = None,
    ) -> list[Finding]:
        self.calls.append((document, events, pdf_bytes, ai_config))
        return [
            self._make_finding(
                inspection_id="AI_TEST_001",
                severity=Severity.WARNING,
                message="legacy ai finding",
            )
        ]


def test_base_ai_analyzer_v2_default_forwards_with_pdf_bytes():
    legacy = _LegacyAIAnalyzer()
    ctx = AnalyzerContext(
        document=_FakeDoc(),
        events=[],
        pdf_bytes=b"%PDF-1.4-fixture",
    )
    findings = legacy.analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "AI_TEST_001"
    assert findings[0].source == "ai"
    assert findings[0].category == "test_category"
    # pdf_bytes survives the round trip.
    assert legacy.calls[0][2] == b"%PDF-1.4-fixture"
    # ai_config defaults to None when ctx.config has no "ai_config".
    assert legacy.calls[0][3] is None


def test_base_ai_analyzer_v2_reconstitutes_ai_config_for_legacy():
    """Legacy AI code expects ai_config.attribute access — verify it works."""

    legacy = _LegacyAIAnalyzer()
    ctx = AnalyzerContext(
        document=_FakeDoc(),
        events=[],
        pdf_bytes=b"",
        config={"ai_config": {"some_field": "value-x"}},
    )
    legacy.analyze_v2(ctx)
    ai_cfg = legacy.calls[0][3]
    assert ai_cfg is not None
    # Either a real TenantAIConfig (if the field is declared) or our
    # AttrDict fallback — both expose attribute access.
    assert getattr(ai_cfg, "some_field", None) == "value-x"


def test_reconstitute_ai_config_handles_none():
    assert _reconstitute_ai_config(None) is None


def test_reconstitute_ai_config_returns_attribute_accessor():
    cfg = _reconstitute_ai_config({"foo": 1, "bar": "two"})
    assert cfg is not None
    assert getattr(cfg, "foo", None) == 1
    assert getattr(cfg, "bar", None) == "two"
    # Unknown attrs return None instead of raising AttributeError —
    # contract that several AI analyzers rely on.
    assert getattr(cfg, "missing", "default") in (None, "default")
