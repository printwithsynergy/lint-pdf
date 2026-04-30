# Viewer-shared audit — Phase 1 / Track B discovery

Captured during the Phase 1 viewer-extraction track. Numbers and file
lists are ground truth at audit time and are the basis for the
Phase 2 component-by-component move.

## Package shape

- Name: `@lintpdf/viewer-shared` (workspace-private).
- 28 components in a flat `src/` layout (no `core/` or `lintpdf/`
  split today — Track B introduces the directories).
- Consumers: `packages/app/components/viewer/index.ts` (re-export
  barrel) and `packages/mobile/src/routes/ViewRoute.tsx`. No
  web/plugin/desktop consumers.
- ~8.3K LOC across components + utilities.

## Component classification

### Pure core (17) — moved to `src/core/components/` in PR #332

`PageCanvas`, `PageNavigator`, `ZoomControls`, `LayerPanel`,
`LayerCanvas`, `AnnotationToolbar`, `AnnotationCanvas`,
`AnnotationThread`, `ColorPickerTool`, `DensitometerTool`,
`DielineOverlay`, `SeparationCanvas`, `BoxOverlay`,
`TACHeatmapOverlay`, `MobileBottomSheet`, `MobileDrawer`,
`MeasureTool` (defaulted to core with the `MeasurementUnit` plugin
slot).

#### Phase-3 abstraction debt (11 of 17 still couple to LintPDF types)

Verification post-PR #332 surfaced that **11 of the 17 moved
components still import LintPDF-domain symbols** (`useViewerApi`,
`ViewerFinding`) from `../../types`. The Track B Phase-1 ESLint
boundary rule blocks `@lintpdf/*` and `**/lintpdf/**` imports — but
`../../types` is in `src/types.ts`, neither pattern, so the rule did
not fire.

The Phase-1 audit explicitly flagged this work as Phase-2/3 follow-up
("`PageCanvas` accepts `ViewerFinding[]` today. Phase 2 abstracts it
to a generic overlay-item interface so `core/` stays LintPDF-clean.").
Tracking the full coupling surface here so the migration can land
component-by-component without losing accuracy:

**`useViewerApi` consumers (11 files)** — read `apiBase`, `readOnly`,
`currentUserId` from a LintPDF-supplied React context:

`AnnotationCanvas`, `AnnotationThread`, `ColorPickerTool`,
`DensitometerTool`, `LayerCanvas`, `LayerPanel`, `MobileDrawer`,
`PageCanvas`, `PageNavigator`, `SeparationCanvas`, `TACHeatmapOverlay`.

Migration target: each component takes a `services: ViewerServices`
prop (or reads it from a core-namespace context) and replaces
`${apiBase}/pages/...` URL construction with
`services.pageImages.getPageImageUrl(...)`,
`services.annotations.list()`, etc.

**`ViewerFinding[]` consumers (0 files remaining)** — both
`PageNavigator` (PR #334) and `PageCanvas` (this PR) have migrated.
Their public props now take `items: readonly OverlayItem[]` /
`selectedItem: OverlayItem | null` instead of `findings: ViewerFinding[]`
/ `selectedFinding: ViewerFinding`, with `PdfViewer.tsx` calling
`findingsToOverlayItems(findings)` / `findingToOverlayItem(selectedFinding)`
once at the call site.

#### Phase 2 abstraction primitives (in place)

- **`OverlayItem`** — generic, LintPDF-free shape rendered on top of
  the page canvas. Fields: `id`, `page`, optional `bbox` (page-level
  items render via a page-level indicator), `tier`, `color`, `label`,
  `description` (longer text for tooltip body), `code` (short
  identifier for tooltip badge), `data`. Defined in
  `src/core/plugin/types.ts`; exported from
  `@lintpdf/viewer-shared/core`.
- **`findingsToOverlayItems(findings)` / `findingToOverlayItem(finding)`**
  — adapters in `src/lintpdf/sources/finding-overlay.ts`. The single
  bridge that knows the LintPDF severity → tier mapping. Tested in
  `tests/lintpdf/finding-overlay.test.ts` (10 tests / 0 snapshots
  — pure function semantics).
- **`ViewerServices`** — already-defined Protocol in
  `src/core/plugin/services.ts` from Track B Phase 1. Includes the
  `pageImages`, `annotations`, `telemetry`, `i18n`, `tokens` slots
  that the 11 components will eventually read instead of
  `useViewerApi`.

Subsequent PRs do the file-by-file migration. The
`ZoomControls` snapshot from PR #331 is the proven behaviour-locking
pattern; each migrated component lands with an equivalent snapshot
in the same PR.

### LintPDF-flavoured (11) — Phase 2 wraps as plugins in `src/lintpdf/plugins/`

### LintPDF-flavoured (11) — Phase 2 wraps as plugins in `src/lintpdf/plugins/`

`PdfViewer` (58K monolith — Phase 2 thins to a host shell + plugin
slots), `FindingsPanel`, `ViewerToolbar`, `AnnotationLayer`,
`VerdictBar`, `ApprovalChainPanel`, `ComparisonPanel`,
`SeparationPanel`, `ShareDialog`, `UpgradePrompt`, `AuditChip`.

Hardcoded API paths surfaced in audit (Phase 2 replaces with
`services.*` calls):

- `GET /api/lintpdf/viewer/{jobId}` (PdfViewer)
- `GET /api/lintpdf/jobs/{jobId}` (PdfViewer)
- `/api/lintpdf/viewer/compare/{comparison_id}` (PdfViewer / ComparisonPanel)
- `POST/PATCH {apiBase}/annotations` (AnnotationLayer)
- `POST /api/lintpdf/jobs/{jobId}/verdict` (VerdictBar)

### Ambiguous (1) — defaults to core

- `MeasureTool` — measurement workflow. Reserved for `core/` with a
  `MeasurementUnit` plugin slot (see `core/plugin/types.ts`) so
  vendor-specific unit definitions (mm, in, point, pica) plug in
  through the protocol.

## Tile-warming + PDF.js

- `useTileWarming.ts` (6.3K) — already isolated. Phase 2 moves it to
  `core/services/tile-warming.ts`.
- PDF.js is **not directly imported** in viewer-shared today; pages
  render through external image tile URLs. The `PageImageService`
  protocol mirrors the existing `{apiBase}/pages/{pageNum}/tile?dpi=`
  shape.

## Tests

**Zero tests today.** Phase 2 sets up Vitest + React Testing Library
and adds behaviour-locking snapshot tests per component before
moving / refactoring.

## ESLint boundary rule

`packages/viewer-shared/eslint.config.mjs` (NEW) scopes:

- `src/core/**` cannot import from `@lintpdf/*` or `**/lintpdf/**`.
- `src/core/**` cannot hardcode `/api/v1/` or `/api/lintpdf/` paths
  in literal strings — route through `ctx.services.*` instead.

## What Track B delivers

- `src/core/plugin/` — protocol surface (types, context, services,
  registry) + public re-exports.
- `src/core/index.ts` — core public barrel.
- `src/lintpdf/` — type re-exports + `registerLintPDFPlugins()` stub.
- `package.json` `exports` — `./core` and `./lintpdf` subpaths.
- `eslint.config.mjs` — boundary rule scoped to `core/`.
- `docs/viewer-api.md` — plugin authoring guide with worked examples.
- This audit.
- `CLAUDE.md` (NEW) — viewer-shared-specific conventions.

## What Track B explicitly does NOT do

- Move any of the 28 existing components (Phase 2 — file-by-file
  with snapshot tests per component).
- Refactor `PdfViewer.tsx` (Phase 2).
- Replace `/api/lintpdf/*` hardcoded strings (Phase 2).
- Touch `packages/app/components/viewer/index.ts` or
  `packages/mobile/src/routes/ViewRoute.tsx` (Phase 2 — both still
  import from the legacy flat barrel).
- Set up Vitest or write tests for the 28 components (Phase 2).
- Touch the marketing-site `ENABLE_SAAS` posture (PRs #313 / #315 /
  #317 — verified unchanged).
