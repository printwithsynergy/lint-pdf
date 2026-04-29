/**
 * `registerLintPDFPlugins` — entry point for the LintPDF plugin pack.
 *
 * Phase 1 stub: the function exists and is callable, but the actual
 * plugins (FindingsPanel, ViewerToolbar, AnnotationLayer, VerdictBar,
 * ApprovalChainPanel, ComparisonPanel, SeparationPanel, ShareDialog,
 * UpgradePrompt, AuditChip — the 11 LintPDF-flavoured components from
 * the Track B audit) are wrapped as plugins in Phase 2. Until then
 * the legacy components are imported directly from
 * `@lintpdf/viewer-shared` like before.
 *
 * Calling this function multiple times is a no-op after the first.
 */

import { register } from "../core/plugin/registry";

let _registered = false;

/**
 * Register every LintPDF-flavoured plugin into the runtime registry.
 *
 * Idempotent. Phase 2 fills the body with `register(...)` calls for
 * each plugin in the pack.
 */
export function registerLintPDFPlugins(): void {
  if (_registered) {
    return;
  }
  _registered = true;
  // Phase 2 inserts:
  //   register(findingsPanelPlugin);
  //   register(viewerToolbarPlugin);
  //   register(annotationLayerPlugin);
  //   register(verdictBarPlugin);
  //   register(approvalChainPanelPlugin);
  //   register(comparisonPanelPlugin);
  //   register(separationPanelPlugin);
  //   register(shareDialogPlugin);
  //   register(upgradePromptPlugin);
  //   register(auditChipPlugin);
  // The `register` import is kept so type-checking catches drift if
  // the registry signature changes between Phase 1 and Phase 2.
  void register;
}

/**
 * Reset the registration latch — **test-only**.
 */
export function _resetLintPDFRegistrationForTesting(): void {
  _registered = false;
}
