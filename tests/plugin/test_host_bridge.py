"""Host bridge tests — SaaS Services wiring + LegacyAIAdapter."""

from __future__ import annotations

from typing import Any, ClassVar

from siftpdf.plugin import AnalyzerContext, PluginManifest, Tier
from siftpdf.plugin.host import LegacyAIAdapter, default_services_for_saas


class _FakeDoc:
    pages: ClassVar[list] = []


class _FakeLegacyAI:
    """Minimal stand-in for a BaseAIAnalyzer subclass."""

    category = "test"
    feature_slug = "test_feature"
    tier = "cpu"
    credits_per_run = 1

    def __init__(self) -> None:
        self.last_call: tuple[Any, ...] | None = None

    def analyze(
        self,
        document: Any,
        events: list,
        pdf_bytes: bytes,
        ai_config: Any = None,
    ) -> list:
        self.last_call = (document, events, pdf_bytes, ai_config)
        return []


def test_default_services_returns_services_object():
    services = default_services_for_saas()
    # Every protocol attribute must exist (some may be None or no-ops).
    for attr in (
        "metering",
        "cost_cap",
        "gpu_client",
        "llm_client",
        "renderer",
        "verapdf_client",
        "database",
        "tenants",
    ):
        assert hasattr(services, attr), f"missing service: {attr}"


def test_legacy_adapter_synthesizes_manifest():
    legacy = _FakeLegacyAI()
    adapter = LegacyAIAdapter(legacy)
    m: PluginManifest = adapter.manifest
    assert m.id.startswith("siftpdf.legacy.")
    assert "_FakeLegacyAI" in m.id
    assert m.tier is Tier.CPU
    assert m.version == "0.0.0-legacy"
    assert "metering" in m.requires_services


def test_legacy_adapter_routes_analyze_v2_to_analyze():
    legacy = _FakeLegacyAI()
    adapter = LegacyAIAdapter(legacy)
    ctx = AnalyzerContext(
        document=_FakeDoc(),
        events=[],
        pdf_bytes=b"%PDF-1.4",
        config={"ai_config": None},
    )
    result = adapter.analyze_v2(ctx)
    assert result == []
    assert legacy.last_call is not None
    # last_call: (document, events, pdf_bytes, ai_config)
    assert legacy.last_call[2] == b"%PDF-1.4"
    assert legacy.last_call[3] is None  # ai_config dict was None


def test_legacy_adapter_falls_back_to_attrdict_when_tenantconfig_missing():
    """Even if TenantAIConfig reconstitution fails, attribute access works."""

    legacy = _FakeLegacyAI()
    adapter = LegacyAIAdapter(legacy)
    # Invent a config field that TenantAIConfig may not declare.
    ctx = AnalyzerContext(
        document=_FakeDoc(),
        events=[],
        pdf_bytes=b"",
        config={"ai_config": {"some_arbitrary_field": "v"}},
    )
    adapter.analyze_v2(ctx)
    assert legacy.last_call is not None
    ai_cfg = legacy.last_call[3]
    assert ai_cfg is not None
    # Either a real TenantAIConfig (if it accepted the field) or an
    # _AttrDict — both support attribute access.
    assert getattr(ai_cfg, "some_arbitrary_field", None) == "v"
