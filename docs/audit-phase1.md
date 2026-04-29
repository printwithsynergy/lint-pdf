# Engine audit — Phase 1 / Track A discovery

Captured during the Phase 1 plugin-protocol track. Every count and file
path here was verified at audit time; the
`scripts/engine_purity_baseline.txt` and
`scripts/openapi_descriptions_baseline.txt` baselines are derived from
this audit.

## Engine package shape

- Package name: **`lintpdf`** (Phase 1). Renames to **`siftpdf`** in
  Phase 3 when the engine moves to `thinkneverland/sift-pdf`.
- Python: `>=3.11`, `uv`-managed.
- Source root: `packages/engine/src/lintpdf/`.
- Entry-point group introduced in Phase 1: `lintpdf.plugins` (no
  third-party packages declare it yet — the legacy decorator registry
  is the active source).

## Base classes

| File | Class | Phase 1 change |
|---|---|---|
| `src/lintpdf/analyzers/base.py` | `BaseAnalyzer` | + `analyze_v2(ctx)` default impl forwards to `analyze()` |
| `src/lintpdf/ai/base.py` | `BaseAIAnalyzer` | + `analyze_v2(ctx)` default impl forwards to `analyze()` with TenantAIConfig reconstitution |

`_reconstitute_ai_config(d)` in `ai/base.py` is the bridge that turns
the dict at `ctx.config["ai_config"]` back into an attribute-accessible
object — either a real `TenantAIConfig` (when the model accepts the
shape) or an `_AttrDict` fallback.

## Analyzer counts

| Layer | Files | Notes |
|---|---|---|
| `analyzers/` | 56 source `.py` files (44 `BaseAnalyzer` subclasses) | Pure detection; no SaaS imports today. |
| `ai/analyzers/` | 61 `@register_ai_analyzer` subclasses across 13 subdirs | Heavy SaaS coupling — every subclass takes `TenantAIConfig`. |

## SaaS-coupling baseline (`scripts/engine_purity_baseline.txt`)

Banned patterns scanned across `src/lintpdf/analyzers/` +
`src/lintpdf/ai/analyzers/`:

| Pattern | Approx file hits |
|---|---|
| `TenantAIConfig` | 52 |
| `from lintpdf.api.models` | 42 |
| `from lintpdf.tenants.*` | 9 |
| `from lintpdf.audit.metering` | 3 |
| `from lintpdf.api.database` | 2 |
| `from lintpdf.ai.cost_cap` | 2 |
| `from lintpdf.audit.cost` | 0 |
| `from lintpdf.ai.credits` | 0 |
| `from lintpdf.ai.gpu_client` | 5 |
| `from lintpdf.conformance.verapdf_client` | 0 (analyzers reach this via the orchestrator only) |
| **Total baseline entries** | **125** |

Phase 2 migrates each of the 63 unique files (counted by union, before
expanding patterns) onto `ctx.services.*` and `ctx.config["ai_config"]`.
Track A's job is to make those migrations *possible* without behaviour
drift; Phase 2 actually performs them.

## Existing registries (Phase 2 unifies)

| Registry | Source | Population |
|---|---|---|
| AI analyzers | `lintpdf/ai/registry.py` | Decorator-driven (`@register_ai_analyzer`); 61 entries. |
| Regulatory references | `lintpdf/regulatory/registry.py` | Static. |
| Preflight profiles | `lintpdf/profiles/registry.py` | JSON-driven (built-in profiles). |
| Wake-on-demand specs | `lintpdf/warming/registry.py` | Static. |

Phase 2 introduces a single entry-point-driven plugin registry that
subsumes the AI registry; the others stay (they're not analyzer
registries, they're config tables).

## Capability precursors

| Symbol | Location | Consumed by |
|---|---|---|
| `render_page_to_image` | `ai/rendering.py:226` | `ai/ocr_claude.py:122`, `ai/legend_claude.py:72` |
| `get_gpu_client()` | `ai/gpu_client.py:443` | 5 GPU analyzers (banding, safe-zone, skin-tone, regulatory-symbols, …) |
| `validate_with_verapdf()` | `conformance/verapdf_client.py` | `profiles/orchestrator.py:430-436`, `conformance/verapdf_runner.py:107` |

Track A wraps the first two as `RendererBackedPageImageProvider` and
`GPUTextRegionProvider` under `lintpdf/plugin/capabilities/`. veraPDF
remains accessed via the orchestrator until Phase 2 introduces a
"PDF/A conformance" capability.

## OpenAPI Field-description baseline

`scripts/check_openapi_descriptions.py` enforces:

```
current_undescribed_fields_in_api/schemas.py <= baseline
```

Initial baseline: **19 undescribed fields**. New fields fail the build
unless they ship `Field(..., description="...")`. Phase 2 backfills
the 19.

(Note: an earlier version of the discovery report estimated ~108
undescribed fields. The script's regex collapses multi-line `Field(...)`
calls, which makes the count more conservative — descriptions that
actually exist but were missed by an eyeball-grep get counted properly.
The 19 number is the ground truth from the regex.)

## Test infrastructure

- pytest. Markers: `slow`, `corpus`, `integration`, `live_ai`.
  `asyncio_mode = "auto"`.
- 263 test modules, ~4300 tests pass on a fast run (excluding slow /
  corpus / integration / live_ai).
- 18 pre-existing failures on `main` at the time of this audit:
  - `tests/reports/test_check_names_shape.py` (6 — friendly-name
    shape rules, unrelated to plugin protocol).
  - `tests/test_worker.py` (12 — Celery worker config, unrelated).
- Track A adds 28 new tests under `tests/plugin/`, all green.

## Railway services

| Service | Role | Phase 1 impact |
|---|---|---|
| **engine** | FastAPI API. | None — additive only. |
| **clamav** | Malware scan sidecar. | None. |
| **verapdf** | PDF/A conformance sidecar. | None. |

Read-only inspection only during Phase 1 (no redeploys, no env-var
changes).

## Discovery → plan deltas

The original prompt assumptions for Track A held up well. Two material
deltas:

- The prompt referenced "the legacy five" registries; reality is **4**.
- `ENABLE_SAAS` is a marketing-site (`packages/web`) toggle only — the
  Python engine doesn't reference it. Phase 1 leaves the toggle
  untouched.
- The OpenAPI baseline shipped at **19**, not the prompt's estimated
  ~108 — see the note above.

## What Track A delivers

- `lintpdf/plugin/` package: manifest, protocol, services, registry,
  host, capabilities (8 modules).
- `analyze_v2` default impl on both base classes (no behaviour change
  for any existing analyzer).
- Tripwire CI guards: `check_engine_purity.sh`,
  `check_openapi_descriptions.py`, with checked-in baselines.
- 28 plugin tests — protocol, base-class, services no-ops, registry
  shape, host bridge, OpenAPI counter regex.
- This audit + `docs/plugin-api.md`.

## What Track A explicitly does NOT do

- Migrate any analyzer onto `ctx.services.*` or
  `ctx.config["ai_config"]` — that's Phase 2 (file-by-file with
  behaviour-locking tests per analyzer).
- Delete the legacy `analyze()` method or the decorator registry —
  Phase 2.
- Backfill the 19 undescribed `Field(...)` calls — Phase 2.
- Wire the new guards into the project's pre-commit hook — separate
  follow-up coordinated with reviewers.
- Touch any FastAPI route — route classification is Phase 2.
- Touch the marketing-site `ENABLE_SAAS` posture (PRs #313 / #315 /
  #317 — verified unchanged).
- Touch Railway / Modal state — read-only access only.
