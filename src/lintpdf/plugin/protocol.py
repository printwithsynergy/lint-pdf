"""Plugin protocol — Analyzer + AnalyzerContext + capability protocols.

`AnalyzerContext` is the single argument passed to ``Analyzer.analyze_v2``.
It carries everything an analyzer needs:
- The semantic document + content stream events (same as legacy).
- Raw PDF bytes (only AI analyzers need these; the field is always present
  but expensive to materialise — orchestrator decides when to populate).
- Free-form ``config`` dict (replaces the old ``TenantAIConfig`` parameter
  on AI analyzers; per-plugin config lives at ``config[plugin_id]``;
  AI-config lives at ``config["ai_config"]``).
- ``services`` — the Services protocol for SaaS-coupled features.
- ``capabilities`` — pull-based providers for cross-cutting work
  (page rendering, text-region detection, etc.) that multiple plugins
  consume but only one needs to run.

The protocol is deliberately structural: any class that exposes
``manifest: PluginManifest`` and ``analyze_v2(ctx) -> list[Finding]``
satisfies it. Existing analyzers keep their legacy ``analyze(...)``
signature; the host bridge in ``plugin.host`` adapts them to ``analyze_v2``
during Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from lintpdf.analyzers.finding import Finding
    from lintpdf.plugin.manifest import PluginManifest
    from lintpdf.plugin.services import Services
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# ---------------------------------------------------------------------------
# Capability protocols
# ---------------------------------------------------------------------------


class PageImageProvider(Protocol):
    """Rasterises a PDF page to PNG/JPEG bytes at a given DPI.

    Multiple plugins want page images at the same DPI; the orchestrator
    runs one provider once and shares the bytes across them.
    """

    def get_page_image(self, *, page_num: int, dpi: int) -> bytes: ...


class TextRegionProvider(Protocol):
    """Returns OCR-detected text-region bounding boxes for a page.

    Used by the OCR-text-as-outlines pipeline + several AI analyzers.
    """

    def get_text_regions(self, *, page_num: int, dpi: int) -> list[dict[str, Any]]: ...


class ContentStreamEventProvider(Protocol):
    """Returns the (already-parsed) content stream events for a page.

    The orchestrator typically passes events directly via
    ``AnalyzerContext.events``; this provider exists for plugins that
    need on-demand re-parsing (e.g., after editing a document).
    """

    def get_events(self, *, page_num: int) -> list[ContentStreamEvent]: ...


@dataclass(frozen=True)
class Capabilities:
    """Aggregate capability surface exposed via ``ctx.capabilities``.

    Each attribute is optional — a plugin that lists ``"page_images"`` in
    its manifest's ``requires_capabilities`` and finds it ``None`` here
    must self-skip with a warning rather than raise.
    """

    page_images: PageImageProvider | None = None
    text_regions: TextRegionProvider | None = None
    content_stream_events: ContentStreamEventProvider | None = None


# ---------------------------------------------------------------------------
# AnalyzerContext
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalyzerContext:
    """Single-argument input bundle for ``Analyzer.analyze_v2``.

    Attributes:
        document: Enriched semantic document with resolved properties.
        events: Content stream events from the interpreter.
        pdf_bytes: Raw PDF bytes. May be ``b""`` for plugins that don't
            need them (the orchestrator avoids materialising large PDFs
            redundantly).
        config: Free-form config dict. Plugin config lives at
            ``config[plugin_id]``; legacy AI config lives at
            ``config["ai_config"]`` (a plain dict mirroring the old
            ``TenantAIConfig`` shape).
        tenant_id: Optional tenant identifier used by services that
            scope per-tenant (metering, cost_cap, tenants).
        services: Service protocols. SaaS hosts pass concrete impls; OSS
            hosts pass the no-op stubs from ``plugin.services``.
        capabilities: Pull-based capability providers. ``None``-valued
            attrs mean the orchestrator hasn't run the corresponding
            provider for this job.
    """

    document: SemanticDocument
    events: list[ContentStreamEvent]
    pdf_bytes: bytes = b""
    config: dict[str, Any] = field(default_factory=dict)
    tenant_id: str | None = None
    services: Services | None = None
    capabilities: Capabilities = field(default_factory=Capabilities)


# ---------------------------------------------------------------------------
# Analyzer protocol
# ---------------------------------------------------------------------------


class Analyzer(Protocol):
    """Structural protocol every analyzer plugin satisfies.

    Two members:
        manifest: Plugin manifest (id, version, tier, capability/service
            requirements, declared check IDs).
        analyze_v2: Detection entry point. Returns Findings.

    The legacy ``analyze(...)`` method on ``BaseAnalyzer`` /
    ``BaseAIAnalyzer`` continues to work through Phase 1 — the host
    bridge wraps legacy analyzers so they satisfy this Protocol.
    """

    manifest: PluginManifest

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]: ...
