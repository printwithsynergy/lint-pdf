// ESLint config for @lintpdf/viewer-shared.
//
// Scope-specific rule: src/core/** is the future LoupePDF OSS surface.
// Code in that subtree must not import from @lintpdf/* packages or
// from sibling lintpdf/** sources, must not import from the LintPDF-
// flavoured src/types.ts, and must not hardcode LintPDF API path
// strings. The viewer-shared package was structurally cleaned of all
// these violations across PRs #327-#347; this config makes the rule
// enforced (was previously documentation-only).
//
// Deliberately minimal ruleset — only the four boundary checks plus
// the TypeScript parser. We don't enable the full
// @typescript-eslint recommended preset because it would surface a
// pile of pre-existing style nits unrelated to the boundary; that's a
// separate cleanup workstream if anyone wants to take it on.

import pluginReactHooks from "eslint-plugin-react-hooks";
import pluginSecurity from "eslint-plugin-security";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "node_modules/**",
      "dist/**",
      "coverage/**",
      "tests/**/__snapshots__/**",
    ],
  },
  // Base TypeScript parsing for every TS / TSX file. The security
  // plugin is registered so that pre-existing
  // `// eslint-disable-next-line security/detect-object-injection`
  // comments inside src/ don't raise "rule not found" errors. We
  // also silence "unused disable directive" reports for two
  // reasons: (1) some disables target rules that aren't loaded in
  // this minimal config (e.g. react-hooks/exhaustive-deps); the
  // unused-disable-checker would error rather than skip them; (2)
  // when broader rules ARE enabled later, those disables become
  // meaningful again — keeping them in source is intentional.
  {
    files: ["src/**/*.{ts,tsx}", "tests/**/*.{ts,tsx}"],
    plugins: {
      security: pluginSecurity,
      "react-hooks": pluginReactHooks,
    },
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    linterOptions: {
      reportUnusedDisableDirectives: "off",
    },
  },
  // The boundary rule applies only inside src/core/.
  {
    files: ["src/core/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@lintpdf/*"],
              message:
                "core/ is OSS surface (future LoupePDF); no @lintpdf/* imports here. Move LintPDF-flavoured logic to src/lintpdf/.",
            },
            {
              group: ["**/lintpdf/**"],
              message:
                "core/ cannot import from sibling lintpdf/ subpackage. Cross the boundary the other way (lintpdf depends on core), never both ways.",
            },
            {
              group: ["../../types", "../../../types"],
              message:
                "core/ cannot import from src/types.ts (LintPDF-flavoured). Use core/types (generic shapes), core/host (React context), or core/plugin/types (OverlayItem etc.) instead.",
            },
          ],
        },
      ],
      "no-restricted-syntax": [
        "error",
        {
          // Catches "/api/v1/" or "/api/lintpdf/" hardcoded in core
          // components. Plugins should resolve URLs through
          // ViewerServices instead.
          selector: "Literal[value=/\\/api\\/(v1|lintpdf)\\//]",
          message:
            "core/ must not hardcode LintPDF API paths. Route through ctx.services (PageImageService / AnnotationService).",
        },
      ],
    },
  },
);
