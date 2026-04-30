# Viewer plugin API

Phase 1 deliverable for the Track B `core/` vs `lintpdf/` split. After
Phase 3 the contents of `src/core/` ship as **`@thinkneverland/loupe-pdf`**
(MIT) and the contents of `src/lintpdf/` ship as
**`@thinkneverland/loupe-plugin-lintpdf`** (proprietary).

## At a glance

```
@lintpdf/viewer-shared/
  core/         # OSS surface (future LoupePDF)
    plugin/     # protocol surface — types, context, services, registry
    components/ # 16 pure-core components — Phase 2 moves them here
  lintpdf/      # LintPDF plugin pack (future loupe-plugin-lintpdf)
    plugins/    # 11 LintPDF-flavoured components — Phase 2 moves them here
    sources/    # AnnotationSourceProvider impl wrapping /api/lintpdf/*
    types.ts    # Finding-shaped types specific to LintPDF
    register.ts # registerLintPDFPlugins() — wires every plugin in the pack
```

A plugin is a small TypeScript object that mounts into a viewer
**slot**:

```ts
import type { PanelPlugin } from "@lintpdf/viewer-shared/core";

const findingsPanelPlugin: PanelPlugin = {
  id: "lintpdf.findings",
  version: "1.0.0",
  slot: "panel.right",
  title: "Findings",
  order: 10,
  mount(ctx) {
    return <FindingsPanel page={ctx.page} services={ctx.services} />;
  },
};

register(findingsPanelPlugin);
```

## Slot catalogue

| Slot | Plugin shape | Where it renders |
|---|---|---|
| `overlay.canvas` | `OverlayPlugin` | Absolutely-positioned over the page canvas. Use for annotation overlays, finding bboxes, dieline indicators. |
| `panel.right` | `PanelPlugin` | Right-side panel, tabbed if multiple. |
| `panel.left` | `PanelPlugin` | Left-side panel, tabbed if multiple. |
| `panel.bottom` | `PanelPlugin` | Bottom drawer / panel. |
| `toolbar.top` | `ToolbarPlugin` | Top toolbar pill. |
| `toolbar.left` | `ToolbarPlugin` | Left toolbar pill. |
| `toolbar.bottom` | `ToolbarPlugin` | Bottom toolbar pill. |
| `annotation.source` | `AnnotationSourceProvider` | Non-visual; supplies annotation data to the viewer. |
| `dialog.modal` | `DialogPlugin` | Modal dialog launched by another plugin. |

Every plugin shares the manifest fields `id`, `version`, `slot`. The
slot type narrows the rest of the shape via discriminated unions.

## Worked examples

### Custom overlay (CMYK stroke heatmap)

```ts
import type { OverlayPlugin } from "@lintpdf/viewer-shared/core";

const cmykHeatmapPlugin: OverlayPlugin = {
  id: "vendor.cmyk-heatmap",
  version: "1.0.0",
  slot: "overlay.canvas",
  mount(ctx) {
    // ctx.viewport, ctx.zoom, ctx.pan are reactive — re-render is
    // driven by the host viewer. ctx.services.pageImages gives you
    // a URL-bearing handle to the rasterised page if you need pixel
    // data (no fetch — viewer caches per (pageNum, dpi)).
    return <CMYKHeatmapCanvas viewport={ctx.viewport} zoom={ctx.zoom} />;
  },
};
```

### Custom side panel (asset inventory)

```ts
import type { PanelPlugin } from "@lintpdf/viewer-shared/core";

const assetInventoryPlugin: PanelPlugin = {
  id: "vendor.asset-inventory",
  version: "1.0.0",
  slot: "panel.right",
  title: "Assets",
  order: 50,
  mount(ctx) {
    return <AssetInventoryPanel
      pageCount={ctx.document.pageCount}
      i18n={ctx.services.i18n}
    />;
  },
};
```

### Replace the page rasteriser

The viewer pulls page images through `ViewerServices.pageImages`. To
swap the source (e.g., serve cached tiles from a CDN), provide a
custom `ViewerServices` when constructing the host viewer — the
plugin protocol stays the same.

```ts
const services: ViewerServices = {
  pageImages: {
    getPageImageUrl({ pageNum, dpi }) {
      return `https://cdn.example.com/tiles/${jobId}/p${pageNum}-${dpi}.png`;
    },
  },
  layers: noopLayerService,
  separations: noopSeparationService,
  tacHeatmap: noopTACHeatmapService,
  colorSample: noopColorSampleService,
  densitometer: noopDensitometerService,
  annotations: lintpdfAnnotationService,
  reports: noopReportsService,
  telemetry: noopTelemetry,
  i18n: noopI18n,
  tokens: defaultThemeTokens,
};
```

`getPageImageUrl` is **synchronous** (returns `string`) so it slots
straight into `<img src={url}>` without a `useEffect`. Hosts that
need async URL signing pre-resolve into a redirect proxy upstream.

The full `ViewerServices` surface ships these protocols (all wired
in PR sequence #338-#343):

| Service | Methods |
|---|---|
| `pageImages` | `getPageImageUrl` |
| `layers` | `getLayerImageUrl`, `listLayers` |
| `separations` | `getChannelImageUrl` |
| `tacHeatmap` | `getHeatmapImageUrl`, `listRuns` |
| `colorSample` | `sampleAt` (returns `null` on err) |
| `densitometer` | `sampleAt` (throws `Error` on err) |
| `annotations` | `list`, `getForPage`, `saveForPage`, `remove` |
| `reports` | `getHtmlReportUrl`, `getPdfDownloadUrl` |
| `telemetry` | `track` |
| `i18n` | `t` |
| `tokens` | `primary`, `accent`, `bg`, `fg`, `border` |

## OSS-mode no-op stubs

`core/plugin/services` ships `noopTelemetry`, `noopI18n`, and
`defaultThemeTokens`. A LoupePDF (post-Phase-3) host can construct a
`ViewerServices` with these defaults plus a vendor-supplied
`pageImages` and `annotations` impl, with no LintPDF code in the
import graph.

## Phase roadmap

| Phase | Scope |
|---|---|
| **1** *(current)* | `core/plugin/` protocol + `lintpdf/` stub + ESLint boundary rule + Phase-1 docs. No component moves; root barrel unchanged so packages/app and packages/mobile keep working. |
| 2 | Move the 16 pure-core components to `core/components/`. Move the 11 LintPDF-flavoured components to `lintpdf/components/` and wire each as a plugin in `lintpdf/register.ts`. Refactor `PdfViewer.tsx` to thin host + plugin slots. Set up Vitest + behaviour-locking snapshot tests. Replace `/api/lintpdf/*` hardcoded strings with `services.*` calls. |
| 3 | Repo extraction. `core/` becomes `@thinkneverland/loupe-pdf` (MIT, OSS); `lintpdf/` becomes `@thinkneverland/loupe-plugin-lintpdf` (proprietary). |
| 4 | LoupePDF docs site (TypeDoc + worked examples). v1.0 SemVer commitment. |

## Authoring rules

1. **First-party LintPDF panels live in `lintpdf/components/`**;
   they are React components consumed directly, not Plugin objects.
   The `Plugin` protocol (manifest + `mount(ctx)`) is the
   **third-party extension surface** — vendor plugins ship
   anywhere and import only from `@lintpdf/viewer-shared/core`.
   Never inside `core/` for either.
2. **No LintPDF imports inside `core/`**. The
   `eslint.config.mjs` rule fails CI on `@lintpdf/*` and
   `**/lintpdf/**` imports inside the `core/` subtree.
3. **No hardcoded API paths inside `core/`**. The same ESLint rule
   catches `/api/v1/` and `/api/lintpdf/` literals — route through
   `ctx.services.*` instead.
4. **Manifest `id` is `<vendor>.<area>.<feature>`**. LintPDF's pack
   uses the `lintpdf.*` prefix.
5. **Bump `version` on protocol-affecting changes**. Plugin packs
   declare `peerDependencies` against the OSS LoupePDF SemVer; this
   commit's TypeScript types are the source of truth.

## Replacing a first-party LintPDF panel

Third-party plugins can opt-in **replace** a built-in plugin
(LintPDF first-party or any other registered plugin) by setting
`replaces` on their manifest:

```ts
import { register } from "@lintpdf/viewer-shared/core";

register({
  id: "vendor.findings",
  version: "1.0.0",
  slot: "panel.right",
  title: "Vendor Findings",
  replaces: "lintpdf.findings", // ← shadows the LintPDF panel
  mount: (ctx) => <VendorFindingsPanel services={ctx.services} />,
});
```

Semantics:
- The replaced plugin stays registered (still appears in
  `listAll()`), but `getPluginsForSlot()` returns the overrider
  instead.
- Registration order doesn't matter — the override takes effect
  whenever both plugins are present.
- At most one plugin can claim a given `replaces` target. A second
  registration that targets the same id throws.
- The target id does not need to be registered yet. The override
  registers cleanly even before the LintPDF pack loads, and starts
  shadowing as soon as the target appears.
- Unregistering the overrider re-emerges the original in slot
  lookups.
- Cross-slot overrides are allowed (a toolbar widget can replace a
  panel) — the original disappears from its slot regardless.
