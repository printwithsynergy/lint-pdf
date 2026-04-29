/**
 * `@lintpdf/viewer-shared/lintpdf` — LintPDF plugin pack.
 *
 * Phase 1 ships type re-exports and a `registerLintPDFPlugins()` stub.
 * Phase 2 moves the 11 LintPDF-flavoured components from `src/` into
 * `src/lintpdf/plugins/` and wires them into the registry inside
 * `register.ts`.
 *
 * After Phase 3 this directory ships as
 * `@thinkneverland/loupe-plugin-lintpdf` (proprietary).
 */

export type {
  AuditVerdict,
  PreflightSourceMode,
  ViewerFinding,
} from "./types";

export { registerLintPDFPlugins } from "./register";
