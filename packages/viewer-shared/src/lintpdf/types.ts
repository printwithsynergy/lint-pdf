/**
 * `@lintpdf/viewer-shared/lintpdf` — LintPDF-specific types.
 *
 * Phase 1 re-exports the existing types from the legacy `src/types.ts`
 * barrel under a stable `lintpdf/` subpath so plugins authored against
 * Phase 2's split layout can already import from here. Phase 2 inlines
 * the type defs into this directory and `src/types.ts` becomes a thin
 * shim.
 *
 * After Phase 3 this directory ships as
 * `@thinkneverland/loupe-plugin-lintpdf` (proprietary).
 */

export type {
  AuditVerdict,
  PreflightSourceMode,
  ViewerFinding,
} from "../types";
