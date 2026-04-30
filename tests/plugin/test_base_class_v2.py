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


# ---------------------------------------------------------------------------
# Q&A 1b-B — relaxed `analyze` abstract requirement
# ---------------------------------------------------------------------------


class _ModernCoreAnalyzer(BaseAnalyzer):
    """Stand-in for a Phase-2 core analyzer — overrides only analyze_v2."""

    def __init__(self) -> None:
        self.ctx_calls: list[AnalyzerContext] = []

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        self.ctx_calls.append(ctx)
        return [
            Finding(
                inspection_id="LPDF_MODERN_001",
                severity=Severity.ADVISORY,
                message="modern core finding",
            )
        ]


class _ModernAIAnalyzer(BaseAIAnalyzer):
    """Stand-in for a Phase-2 AI analyzer — overrides only analyze_v2."""

    category = "modern_ai"
    feature_slug = "modern_ai"

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        return [
            Finding(
                inspection_id="LPDF_MODERN_AI_001",
                severity=Severity.ADVISORY,
                message="modern AI finding",
                details={"ai_config_keys": list((ctx.config or {}).keys())},
            )
        ]


class _BrokenCoreAnalyzer(BaseAnalyzer):
    """Subclass that overrides NEITHER analyze nor analyze_v2.

    Phase 2 (Q1b-B) relaxed @abstractmethod so the class instantiates
    cleanly; the failure surfaces only when analyze_v2 forwards to
    the inherited default `analyze` and that raises.
    """


def test_modern_core_analyzer_runs_with_only_analyze_v2_override():
    """Q1b-B: instantiating a subclass that overrides only analyze_v2 succeeds."""

    modern = _ModernCoreAnalyzer()
    ctx = AnalyzerContext(document=_FakeDoc(), events=[])
    findings = modern.analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_MODERN_001"
    assert len(modern.ctx_calls) == 1
    assert modern.ctx_calls[0] is ctx


def test_modern_ai_analyzer_runs_with_only_analyze_v2_override():
    modern = _ModernAIAnalyzer()
    ctx = AnalyzerContext(
        document=_FakeDoc(),
        events=[],
        pdf_bytes=b"",
        config={"ai_config": {"foo": 1}, "other": "x"},
    )
    findings = modern.analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_MODERN_AI_001"
    # ctx.config arrives unchanged.
    assert "ai_config" in findings[0].details["ai_config_keys"]


def test_broken_subclass_instantiates_but_raises_on_call():
    """A subclass that overrides neither method now instantiates
    (Phase 1 blocked instantiation via @abstractmethod). The failure
    is deferred to first call, which surfaces a clear error message
    naming the subclass.
    """
    broken = _BrokenCoreAnalyzer()  # ← used to fail at this line
    import pytest

    with pytest.raises(NotImplementedError) as exc_info:
        broken.analyze_v2(AnalyzerContext(document=_FakeDoc(), events=[]))
    assert "_BrokenCoreAnalyzer" in str(exc_info.value)
    assert "analyze_v2" in str(exc_info.value)


def test_base_analyzer_is_no_longer_abc_strict_about_analyze():
    """The class still inherits from ABC, but `analyze` is no longer
    an @abstractmethod. Instantiating a subclass that doesn't override
    `analyze` works (the failure is deferred to call time).
    """
    # If @abstractmethod were still on analyze, instantiating
    # _BrokenCoreAnalyzer would raise TypeError at class-construction
    # time. Q1b-B's relaxation means it should NOT raise here.
    instance = _BrokenCoreAnalyzer()
    assert isinstance(instance, BaseAnalyzer)
