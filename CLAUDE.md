# Engine — Agent Notes

## Viewer capabilities

When you add an analyzer that computes a **data_capability** (separations, TAC, fonts, images, layers, or anything newly exposed to the viewer), you MUST:

1. Register the capability name in the viewer capability map (see `lintpdf/api/routes/viewer.py` — the `get_viewer_config` handler and the `POST .../capabilities/{capability}` on-demand endpoint).
2. Add the flag to `FindingResponse` / `JobResponse` surfaces if the capability implies a new per-finding field.
3. Document it in `packages/web/src/content/docs/viewer-capabilities.md` (fillable table + analyzer description) and the `ApiViewerSection.tsx` config FieldTable.
4. If the capability is **not** on-demand-fillable (e.g., `layers` — PDF optional-content groups can only be discovered at ingest), state that explicitly in both places. Silent "load button does nothing" is the worst UX.

Single rule: the viewer capability registry and the docs stay 1:1. If you only change one, reviewers should bounce the PR.

## External parsers

Each `external_format` enum value (`pitstop_xml`, `callas_json`, `callas_xml`, `acrobat_xml`, `lintpdf_json`) has exactly one parser under `lintpdf/imports/` and exactly one sample in `docs/examples/`. Adding a new built-in format means all three:

1. New parser under `lintpdf/imports/<vendor>.py`, registered in `lintpdf/imports/detect.py`.
2. New `docs/examples/<vendor>-report.{xml,json}` sample that round-trips through the parser cleanly.
3. New row in the `external_format` enum appendix (`ApiEnumsSection.tsx`) and the supported-formats table in `external-imports.md`.

## No format autopsies

Parsers must fail cleanly with a `422` carrying the field path that broke. Never swallow a parse error and emit zero findings — the caller will assume their report was clean.

---

## Plugin protocol + analyzer conventions (Phase 1)

Every analyzer satisfies the Protocol in `src/lintpdf/plugin/`:

```python
class Analyzer(Protocol):
    manifest: PluginManifest                                 # plugin.manifest
    def analyze_v2(self, ctx: AnalyzerContext) -> list[Finding]: ...
```

Existing analyzers that still implement legacy `analyze(...)` keep
working — `BaseAnalyzer.analyze_v2` and `BaseAIAnalyzer.analyze_v2`
ship default impls that forward to `analyze`. New analyzers must
override `analyze_v2` directly and skip the legacy method.

**Forbidden imports inside `src/lintpdf/analyzers/**` and
`src/lintpdf/ai/analyzers/**`** (use `ctx.services.*` or
`ctx.config["ai_config"]` instead):

- `lintpdf.tenants.*` → `ctx.config["ai_config"]` (when reading tenant AI
  config) or `ctx.services.tenants` (when reading entitlements).
- `lintpdf.api.models.TenantAIConfig` → read from
  `ctx.config["ai_config"]` (a plain dict).
- `lintpdf.audit.metering` → `ctx.services.metering`.
- `lintpdf.audit.cost`, `lintpdf.ai.cost_cap`, `lintpdf.ai.credits`
  → `ctx.services.cost_cap`.
- `lintpdf.api.database` → `ctx.services.database`.
- `lintpdf.ai.gpu_client` → `ctx.services.gpu_client`.
- `lintpdf.conformance.verapdf_client` → `ctx.services.verapdf_client`.

`scripts/check_engine_purity.sh` is the tripwire — it counts existing
violations (baseline: 125) and fails CI when the count goes UP. Down-
counts (Phase 2 migrations) are encouraged; regenerate the baseline
with the script's hint after a clean migration commit. The hook in
`.githooks/pre-commit` runs this guard automatically whenever any
`packages/engine/*.py` file is staged.

---

## Service ownership boundary

Keep ownership explicit across core repos:

- `loupe-pdf` owns display + visual inspection UX. Built-in
  `FindingsSidebar` + `DielineInfoPanel` components (0.3.0-beta.71 +)
  + `splitFindingsByLocation` / `hasViewerLocation` helpers so
  adapters map findings into the canvas consistently.
- `lint-pdf` owns reporting, rules, and preflight workflow semantics.
- `codex-pdf` owns extraction + normalized reusable intelligence
  payloads. Floor pin: `codex-pdf>=1.15.0` (AI Signal Phases 0–4 +
  dieline.count root-cause fix).

Rules for this repo:

- Prefer consuming Codex signals/summaries instead of re-implementing extraction primitives.
- Keep policy decisions and report semantics here.
- Avoid viewer/UI behavior in engine logic.

AI signal extraction: the `codex_signals_*` analyzers in
`src/lintpdf/ai/analyzers/codex_signals/` (0.1.0b16 +) read codex's
AI signal fields (language, logos, symbols, barcodes, classification,
spell) instead of running their own Claude calls. Codex pays the
LLM bill once per `(pdf_hash, signal_kind)` and caches; lint just
reads. Service-boundary win: codex stays data-collection, lint
stays policy-over-data.

Future offshoots (Forge, Trap, Impose, Marks, etc.) must map each capability to one owner layer and integrate through stable contracts.

**Capability rule**: if two plugins read the same shared work
(rendered page image, OCR text regions), wrap it as a `Capabilities`
provider in `lintpdf/plugin/capabilities/` and have the orchestrator
fulfil it once. Two analyzers calling `render_page_to_image` directly
is a code smell.

**Tier guidance** in the manifest:

- `Tier.CPU` — runs in the orchestrator process; no external services.
- `Tier.GPU` — needs `gpu_client` and usually `page_images`.
- `Tier.EXTERNAL_AI` — calls an LLM/API; must use `cost_cap` +
  `metering` services.

**Service-skip pattern**: when a plugin lists a service in
`requires_services` but `ctx.services.<name>` is `None` (or capability
in `requires_capabilities` but `ctx.capabilities.<name>` is `None`),
self-skip with `return []` and a `logger.warning(...)`. Never raise
— missing services on OSS hosts must degrade gracefully.

---

## Public-API discipline

**Pydantic schema fields**: every `Field(...)` in `api/schemas.py` MUST
include `description="..."`. The description is what `/openapi.json`
and `/redoc` surface to API consumers; missing descriptions silently
ship a worse developer experience.

`scripts/check_openapi_descriptions.py` enforces the rule with a
baseline counter (current: 0 — Phase 2 closed the 19-field backlog).
New fields without `description=` fail the build. The hook in
`.githooks/pre-commit` runs this guard automatically whenever any
`packages/engine/*.py` file is staged.

Other rules:

- Every FastAPI route handler MUST have a docstring summary and an
  explicit `responses=` mapping listing each non-200 status it can
  emit. The summary becomes the operation summary in the generated
  schema.
- No raw `dict[str, Any]` returns from public routes. Define a
  Pydantic response model — even a single-field one — so the client
  generator has a name to attach.
- Engine-public vs SaaS-only routes are not yet classified; that's
  Phase 2. Until then, every new route gets the same description
  discipline regardless of audience.

---

## Functionality preservation + Hosted SaaS continuity

Mandatory for every non-trivial change.

**Blast-radius before refactor**: before changing a symbol, grep for
its callers (`grep -rn "symbol_name" src/ tests/`) to confirm you know
who depends on it. For renames or removals, do the same sweep across
the whole tree. The `ctxo` MCP tools (`get_blast_radius`,
`find_importers`, `get_change_intelligence`, `get_pr_impact`) provide
this analysis on a richer dependency graph but only for TypeScript,
Go, and C#; lint-pdf is Python and no `@ctxo/lang-python` plugin is
published yet — grep is the working substitute. Revisit when ctxo
ships Python support.

**Behavior-locking test FIRST**: when changing analyzer behaviour or
schema shape, snapshot the current output into a test that fails if
the output changes. Commit the test first; commit the refactor
second.

**Customer surface frozen**: hosted LintPDF (`lintpdf.com` /
`app.lintpdf.com` / `reports.lintpdf.com`) MUST produce bit-for-bit
identical responses through every Phase. The
`tests/regression/test_customer_surface_parity.py` and
`tests/regression/test_finding_parity.py` suites are the gate. (Both
land in Phase 2 — Phase 1's tripwire is the engine-purity script.)

**Coverage acceptance bar**: test count never drops; coverage of
touched files never drops. Net coverage drops require either added
tests or an explicit dead-code justification in the PR description.

**Never bypass the sandbox**: no `--no-verify`, `--no-gpg-sign`, or
`--accept-data-loss`. If a hook fails on a file you didn't stage,
fix the underlying error or unstage the hunk — see the project's
root `CLAUDE.md` "Working Agreements" section for the rationale.
