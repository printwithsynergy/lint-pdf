"""Behavior-locking tests for analyze_v2 contract on base classes.

Phase 3b dropped the legacy ``BaseAIAnalyzer.analyze()`` 4-arg method.
Subclasses now MUST override ``analyze_v2(ctx)``. ``BaseAnalyzer``
still keeps the legacy 2-arg ``analyze(document, events)`` path
because the 4 deterministic non-AI analyzers (advanced_color_analyzer,
barcode, dieline, legend) haven't migrated yet — that's Phase 3c.

These tests lock in:
- ``BaseAnalyzer.analyze_v2`` default forwards to legacy ``analyze``.
- ``BaseAIAnalyzer.analyze_v2`` raises NotImplementedError when a
  subclass forgets to override.
- ``_reconstitute_ai_config`` round-trips dicts and handles None.
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest

from lintpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.plugin import AnalyzerContext


class _FakeDoc:
    pages: ClassVar[list] = []


# ---------------------------------------------------------------------------
# BaseAnalyzer (legacy 2-arg analyze still supported through Phase 3c)
# ---------------------------------------------------------------------------


class _LegacyCoreAnalyzer(BaseAnalyzer):
    """Stand-in for a non-AI deterministic analyzer — implements legacy analyze."""

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


def test_base_analyzer_v2_default_forwards_to_legacy_analyze() -> None:
    legacy = _LegacyCoreAnalyzer()
    ctx = AnalyzerContext(document=_FakeDoc(), events=[])
    findings = legacy.analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_TEST_001"
    assert len(legacy.calls) == 1
    assert legacy.calls[0][0] is ctx.document
    assert legacy.calls[0][1] is ctx.events


def test_base_analyzer_v2_returns_same_findings_as_direct_analyze() -> None:
    legacy = _LegacyCoreAnalyzer()
    direct = legacy.analyze(_FakeDoc(), [])
    via_v2 = legacy.analyze_v2(AnalyzerContext(document=_FakeDoc(), events=[]))
    assert direct == via_v2


# ---------------------------------------------------------------------------
# BaseAIAnalyzer (Phase 3b: analyze_v2 is the only entry point)
# ---------------------------------------------------------------------------


class _ModernAIAnalyzer(BaseAIAnalyzer):
    """Standard Phase-2 AI analyzer — overrides analyze_v2 directly."""

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


class _BrokenAIAnalyzer(BaseAIAnalyzer):
    """Subclass that forgets to override analyze_v2."""

    category = "broken"
    feature_slug = "broken"


def test_modern_ai_analyzer_runs_with_analyze_v2_override() -> None:
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
    assert "ai_config" in findings[0].details["ai_config_keys"]


def test_broken_ai_subclass_raises_clear_error() -> None:
    """Phase 3b: BaseAIAnalyzer.analyze_v2 default raises
    NotImplementedError naming the subclass when a subclass forgets
    to override it.
    """
    broken = _BrokenAIAnalyzer()
    with pytest.raises(NotImplementedError) as exc_info:
        broken.analyze_v2(AnalyzerContext(document=_FakeDoc(), events=[]))
    assert "_BrokenAIAnalyzer" in str(exc_info.value)
    assert "analyze_v2" in str(exc_info.value)


def test_legacy_analyze_method_no_longer_exists_on_base_ai_analyzer() -> None:
    """Phase 3b removed BaseAIAnalyzer.analyze(). Subclasses that
    accidentally still inherit a legacy 4-arg shape from somewhere
    won't shadow analyze_v2 — and the bare class definition no
    longer ships an analyze method at all.
    """
    assert "analyze" not in BaseAIAnalyzer.__dict__


# ---------------------------------------------------------------------------
# _reconstitute_ai_config (still used by 13+ analyzers)
# ---------------------------------------------------------------------------


def test_reconstitute_ai_config_handles_none() -> None:
    assert _reconstitute_ai_config(None) is None


def test_reconstitute_ai_config_returns_attribute_accessor() -> None:
    cfg = _reconstitute_ai_config({"foo": 1, "bar": "two"})
    assert cfg is not None
    assert getattr(cfg, "foo", None) == 1
    assert getattr(cfg, "bar", None) == "two"
    # Unknown attrs return None instead of raising AttributeError —
    # contract that several AI analyzers rely on.
    assert getattr(cfg, "missing", "default") in (None, "default")


# ---------------------------------------------------------------------------
# BaseAnalyzer relaxation (Q1b-B from Phase 2 — kept here for completeness)
# ---------------------------------------------------------------------------


class _ModernCoreAnalyzer(BaseAnalyzer):
    """Stand-in for a Phase-3 core analyzer — overrides only analyze_v2."""

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


class _BrokenCoreAnalyzer(BaseAnalyzer):
    """BaseAnalyzer subclass that overrides neither analyze nor analyze_v2."""


def test_modern_core_analyzer_runs_with_only_analyze_v2_override() -> None:
    modern = _ModernCoreAnalyzer()
    ctx = AnalyzerContext(document=_FakeDoc(), events=[])
    findings = modern.analyze_v2(ctx)
    assert len(findings) == 1
    assert findings[0].inspection_id == "LPDF_MODERN_001"


def test_broken_core_subclass_instantiates_but_raises_on_call() -> None:
    broken = _BrokenCoreAnalyzer()
    with pytest.raises(NotImplementedError) as exc_info:
        broken.analyze_v2(AnalyzerContext(document=_FakeDoc(), events=[]))
    assert "_BrokenCoreAnalyzer" in str(exc_info.value)
