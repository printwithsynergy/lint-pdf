# viewer-shared — Agent Notes

## Two namespaces, two destinations

`packages/viewer-shared/` ships two subpackages today, both inside the
same workspace:

- **`src/core/`** — future `@thinkneverland/loupe-pdf` (MIT, OSS).
  PDF viewer primitives, plugin protocol, no LintPDF concepts.
- **`src/lintpdf/`** — future `@thinkneverland/loupe-plugin-lintpdf`
  (proprietary). LintPDF-flavoured panels, overlays, and the
  `registerLintPDFPlugins()` entry point.

Phase 1 introduced the directories and the protocol while keeping
existing components at the legacy `src/` flat layout. Phase 2 (in
progress) has completed the structural moves and the services
abstraction:

- 17 pure-core components moved to `src/core/components/` (PR #332).
- 10 LintPDF-flavoured components moved to `src/lintpdf/plugins/`
  (PR #344).
- All host-supplied data flows through `ViewerServices` (PRs
  #338-#343); zero components inside `core/components/` build URLs
  from `apiBase`.

Still in flight for Phase 2:
- Wrap the 10 moved LintPDF components as `Plugin` objects (manifest
  + `mount(ctx)`) and populate `registerLintPDFPlugins()`.
- Refactor `PdfViewer.tsx` (still a 1244-line orchestrator) into a
  thin host shell that drives the plugin slots.
- Wire actual ESLint enforcement (`@typescript-eslint/parser` +
  `lint` script + CI). Today the boundary rule in
  `eslint.config.mjs` is documentation-only because the package
  has no `lint` script.

## Boundary rule

`src/core/**` is the OSS surface. The ESLint config in
`eslint.config.mjs` enforces:

- No `@lintpdf/*` imports.
- No imports from sibling `**/lintpdf/**`.
- No hardcoded `/api/v1/` or `/api/lintpdf/` strings — go through
  `ctx.services.*`.

If you find yourself fighting the rule, you're trying to put a
LintPDF concept in `core/`. Move it to `lintpdf/` instead.

## Plugin authoring conventions

- **Plugins are TypeScript objects**, not React components. The
  manifest carries metadata; `mount()` returns the React node.
- **Stable id format**: `<vendor>.<area>.<feature>` (e.g.,
  `lintpdf.findings`, `vendor.cmyk-heatmap`). Don't include slot
  names in the id — slot is captured separately.
- **Bump `version` on protocol-affecting changes** so plugin pack
  consumers can pin against a SemVer range.
- **Use the slot's `order` field** to control panel/toolbar
  ordering. Lower renders first. LintPDF plugin pack uses the
  10-100 range; reserve 0–9 and 101+ for vendor packs that need to
  bracket the LintPDF defaults.

## API stability

`@public` JSDoc tags mark every exported symbol in `src/core/`.
After Phase 3 those become the published LoupePDF surface. **No
breaking changes to a `@public` symbol without a major version
bump** — third-party plugin packs depend on the shape.

`src/lintpdf/` exports are not `@public` because they're proprietary.
But behave the same way internally — refactors must not silently
break LintPDF plugin consumers.

## Theme + i18n via services

Plugins **never** hardcode hex colours or English copy. Read theme
tokens from `ctx.services.tokens` and translatable strings from
`ctx.services.i18n.t(...)`. The OSS no-op `noopI18n` returns the key
unchanged, which is the correct fallback for English-only hosts.

## Functionality preservation

When you move or refactor a component:

1. Capture screenshots at the consumer routes (`/dashboard/jobs/...`
   in packages/app, the mobile companion's viewer route) **before**
   the move. Manual + Playwright if available.
2. Move with `git mv` so blame survives.
3. Re-screenshot after. Diff = empty.
4. Add a Vitest + React Testing Library snapshot test for the moved
   component (Phase 2 sets up the harness).

## Phase roadmap

- **1** — protocol + scaffolding + boundary rule + docs. *(complete)*
- **2** — move components, wire plugins, replace `/api/lintpdf/*`
  hardcoding with `ctx.services.*`, set up Vitest, refactor
  `PdfViewer.tsx`. *(structural moves + services abstraction
  complete; plugin-wrapping + PdfViewer refactor still pending)*
- **3** — extract `thinkneverland/loupe-pdf` + `loupe-plugin-lintpdf`
  repos.
- **4** — LoupePDF docs site, v1.0 SemVer.

## Working-agreements pointers

The project-root `CLAUDE.md` "Working Agreements" applies in full:
no `--no-verify`, no `--no-gpg-sign`, no `--accept-data-loss`. If a
hook fails on a hunk you don't own, fix the underlying issue or
unstage the hunk; never bypass.
