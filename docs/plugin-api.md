---
title: "Plugin API"
description: "Full Protocol reference for analyzer plugins — manifest fields, AnalyzerContext, banned imports, capability providers, and tier guidance."
group: "Reference"
order: 5
---

# Plugin API — engine analyzer protocol

Phase 1 deliverable for the LintPDF / LintPDF / LoupePDF brand split (see
the root `CLAUDE.md` "Brand stack + repo split" section). This document
describes the analyzer plugin contract introduced under
`packages/engine/src/lintpdf/plugin/`.

## At a glance

Every analyzer satisfies a single Protocol:

```python
class Analyzer(Protocol):
    manifest: PluginManifest
    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]: ...
```

`AnalyzerContext` carries everything the plugin needs:

```python
@dataclass(frozen=True)
class AnalyzerContext:
    document: SemanticDocument
    events: list[ContentStreamEvent]
    pdf_bytes: bytes = b""
    config: dict[str, Any] = ...        # per-plugin + ai_config
    tenant_id: str | None = None
    services: Services | None = None    # SaaS-coupled features
    capabilities: Capabilities = ...    # pull-based shared work
```

Existing analyzers that still implement the legacy `analyze(...)`
signature keep working unchanged. The base classes
(`BaseAnalyzer`, `BaseAIAnalyzer`) ship a default `analyze_v2(ctx)`
that forwards to legacy `analyze`. Phase 2 deletes the legacy method
once every analyzer overrides `analyze_v2` directly.

## Anatomy of a plugin

Three flavours map to the three tiers in the manifest.

### CPU plugin (deterministic engine analyzer)

```python
from lintpdf.analyzers.finding import Finding, Severity
from lintpdf.plugin import Analyzer, AnalyzerContext, PluginManifest, Tier


class HairlineAnalyzer:
    manifest = PluginManifest(
        id="lintpdf.geometry.hairline",
        version="1.0.0",
        tier=Tier.CPU,
        declared_check_ids=("LPDF_STROKE_001", "LPDF_STROKE_002"),
    )

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        findings: list[Finding] = []
        for event in ctx.events:
            # ...inspect stroke widths against a 0.25 pt threshold...
            pass
        return findings
```

CPU plugins need no services and no capabilities. They run on every
preflight job, in the same Worker process as the orchestrator.

### GPU plugin (vision analyzer)

```python
class BarcodeOrientationAnalyzer:
    manifest = PluginManifest(
        id="lintpdf.barcode.orientation",
        version="1.0.0",
        tier=Tier.GPU,
        requires_capabilities=("page_images",),
        requires_services=("gpu_client",),
        declared_check_ids=("LPDF_BARCODE_010",),
    )

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        if ctx.capabilities.page_images is None:
            return []  # capability not provisioned on this host — self-skip

        png = ctx.capabilities.page_images.get_page_image(page_num=1, dpi=300)
        # ...send to GPU sidecar, parse response...
        return []
```

GPU plugins declare the capabilities they need. The orchestrator
fulfils each capability once and shares the result with every
consumer plugin — no double-rendering.

### EXTERNAL_AI plugin (LLM-backed analyzer)

```python
class LegendInterpretAnalyzer:
    manifest = PluginManifest(
        id="lintpdf.legend.interpret",
        version="1.0.0",
        tier=Tier.EXTERNAL_AI,
        requires_capabilities=("page_images",),
        requires_services=("metering", "cost_cap", "llm_client"),
        declared_check_ids=("AI_LEGEND_001",),
    )

    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]:
        services = ctx.services
        if services is None or services.llm_client is None:
            return []

        services.cost_cap.check_or_raise(
            tenant_id=ctx.tenant_id or "anonymous",
            feature_slug="legend.interpret",
            estimated_units=1,
        )
        # ...call services.llm_client.complete(...)...
        services.metering.record_usage(
            tenant_id=ctx.tenant_id or "anonymous",
            feature_slug="legend.interpret",
            units=1,
        )
        return []
```

EXTERNAL_AI plugins always reach SaaS-coupled features through
`ctx.services.*` — never via direct imports. OSS-mode hosts wire no-op
stubs (`noop_metering()`, `noop_cost_cap()`) so the same code runs in
both worlds.

## Capabilities — pull-based shared work

| Capability | Protocol | Wraps |
|---|---|---|
| `page_images` | `PageImageProvider.get_page_image(page_num, dpi)` | `lintpdf.ai.rendering.render_page_to_image` |
| `text_regions` | `TextRegionProvider.get_text_regions(page_num, dpi)` | `gpu_client.detect_outlines` |
| `content_stream_events` | `ContentStreamEventProvider.get_events(page_num)` | reserved for on-demand re-parse |

Capability rule of thumb: *if two plugins want it, it's a capability;
if one plugin wants it, it's an internal helper.*

## Services — SaaS edge

| Service | Protocol | Hosted impl wraps | OSS no-op |
|---|---|---|---|
| `metering` | `MeteringService.record_usage(...)` | `lintpdf.audit.metering.record_usage` | `noop_metering()` |
| `cost_cap` | `CostCapService.check_or_raise(...)` | `lintpdf.ai.cost_cap.check_cap_or_raise` | `noop_cost_cap()` |
| `gpu_client` | `GPUClient.detect_outlines(...)` | `lintpdf.ai.gpu_client.get_gpu_client()` | `None` |
| `llm_client` | `LLMClient.complete(...)` | (Phase 2 — analyzers use Anthropic SDK directly today) | `None` |
| `renderer` | `Renderer.render_page(...)` | `lintpdf.ai.rendering.render_page_to_image` | `None` |
| `verapdf_client` | `VeraPDFClient.is_configured() / .validate(...)` | `lintpdf.conformance.verapdf_client` | `noop_verapdf()` (skip advisory) |
| `database` | `DatabaseService.session()` | `lintpdf.api.database.SessionLocal` | `None` |
| `tenants` | `TenantsService.get_ai_config(...) / .get_entitlements(...)` | `lintpdf.tenants.config_resolver / .entitlements` | `noop_tenants()` |

The `default_services_for_saas()` factory in `lintpdf/plugin/host.py`
constructs a hosted-LintPDF Services bundle by lazy-importing each
SaaS module. OSS hosts skip the factory and assemble a Services from
the no-op stubs.

## Discovery

```python
from lintpdf.plugin import discover_all

plugins = discover_all()  # entry points + legacy decorator registry
```

- Entry points: `[project.entry-points."lintpdf.plugins"]` in any
  installed package's pyproject.toml. Each entry resolves to a class
  or factory returning an `Analyzer`.
- Legacy fallback: every `@register_ai_analyzer` instance is wrapped
  in `LegacyAIAdapter` so callers see a uniform `Analyzer` Protocol.
  Phase 2 retires the fallback.

## Phase roadmap

| Phase | Scope |
|---|---|
| **1** *(current)* | Protocol + Services + Capabilities + LegacyAIAdapter + base-class `analyze_v2` default impl + tripwire CI guards. Existing analyzers run unchanged. |
| 2 | Migrate every analyzer in `analyzers/` and `ai/analyzers/` to override `analyze_v2` directly and read services / capabilities / config from the context. Delete legacy `analyze()` and the decorator registry. Backfill `Field(..., description=...)` for the existing schema-field backlog. |
| 3 | Repo extraction: engine moves to `thinkneverland/sift-pdf` and the Python package renames `lintpdf` → `lintpdf`. Entry-point group renames to `lintpdf.plugins`. SaaS depends on `lintpdf` as an external package. |
| 4 | OSS flip. Apache-2.0 license headers. v1.0 SemVer. LintPDF docs site. |

## Testing the contract

```sh
cd packages/engine
pytest tests/plugin -q                        # protocol + base-class
                                              # behavior-locking tests
bash scripts/check_engine_purity.sh           # SaaS-import tripwire
python scripts/check_openapi_descriptions.py  # OpenAPI tripwire
```

When a plugin author adds a new analyzer:

1. Implement `Analyzer` Protocol — `manifest` + `analyze_v2`.
2. Register via entry point (or `@register_ai_analyzer` for now —
   Phase 2 deletes the decorator path).
3. Add a behavior-locking test under `tests/plugin/` or
   `tests/regression/` that snapshots a representative finding.
4. If the manifest declares a new check ID, register a friendly name
   in `lintpdf/reports/check_names.py` (project rule, separate from
   the protocol).
5. If the plugin computes a `data_capability` exposed to the viewer,
   follow `packages/engine/CLAUDE.md` "Viewer capabilities" rules.
