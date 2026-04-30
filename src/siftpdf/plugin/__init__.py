"""Plugin protocol — public surface.

Phase 1 of the SiftPDF / LintPDF split (see ``packages/engine/CLAUDE.md``).
Analyzers expose a uniform ``Analyzer`` Protocol with a manifest +
``analyze_v2(ctx)`` entry point. SaaS-coupled features (metering, cost
cap, GPU inference, veraPDF, tenant config) are reached through
``ctx.services`` Protocols, never through direct imports.

Existing analyzers that still implement the legacy ``analyze(...)``
signature continue to work — the host bridge in ``plugin.host`` adapts
them to the Protocol on the fly. New analyzers should implement
``analyze_v2`` directly.
"""

from siftpdf.plugin.manifest import PluginManifest, Tier
from siftpdf.plugin.protocol import (
    Analyzer,
    AnalyzerContext,
    Capabilities,
    ContentStreamEventProvider,
    PageImageProvider,
    TextRegionProvider,
)
from siftpdf.plugin.registry import (
    ENTRY_POINT_GROUP,
    discover_all,
    discover_entry_points,
    discover_legacy_ai,
)
from siftpdf.plugin.services import (
    CostCapService,
    DatabaseService,
    GPUClient,
    LLMClient,
    MeteringService,
    Renderer,
    Services,
    TenantsService,
    VeraPDFClient,
    noop_cost_cap,
    noop_metering,
    noop_tenants,
    noop_verapdf,
)

__all__ = [
    "ENTRY_POINT_GROUP",
    "Analyzer",
    "AnalyzerContext",
    "Capabilities",
    "ContentStreamEventProvider",
    "CostCapService",
    "DatabaseService",
    "GPUClient",
    "LLMClient",
    "MeteringService",
    "PageImageProvider",
    "PluginManifest",
    "Renderer",
    "Services",
    "TenantsService",
    "TextRegionProvider",
    "Tier",
    "VeraPDFClient",
    "discover_all",
    "discover_entry_points",
    "discover_legacy_ai",
    "noop_cost_cap",
    "noop_metering",
    "noop_tenants",
    "noop_verapdf",
]
