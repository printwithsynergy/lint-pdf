// ESLint config for @lintpdf/viewer-shared.
//
// Scope-specific rule: src/core/** is the future LoupePDF OSS surface.
// Code in that subtree must not import from @lintpdf/* packages or
// from sibling lintpdf/** sources, and must not hardcode LintPDF API
// path strings. Phase 2 migrates the 16 pure-core components into
// core/components/ and this rule guards against accidental LintPDF
// coupling creeping back in.

export default [
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
          ],
        },
      ],
      "no-restricted-syntax": [
        "error",
        {
          // Catches "/api/v1/" or "/api/lintpdf/" hardcoded in core
          // components. Plugins should resolve URLs through
          // ViewerServices instead.
          selector:
            "Literal[value=/\\/api\\/(v1|lintpdf)\\//]",
          message:
            "core/ must not hardcode LintPDF API paths. Route through ctx.services (PageImageService / AnnotationService).",
        },
      ],
    },
  },
];
