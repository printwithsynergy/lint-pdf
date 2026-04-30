/**
 * LintPDF → OverlayItem adapter.
 *
 * Translates LintPDF-domain `ViewerFinding` records into the generic
 * `OverlayItem` interface that core components consume. This is the
 * one place that knows about the LintPDF severity palette + the
 * inspection-id → label mapping.
 *
 * Phase 2 / 3 follow-ups will migrate `PageCanvas` and `PageNavigator`
 * to take `OverlayItem[]` instead of `ViewerFinding[]`. Until that
 * migration lands, this adapter is dead-code-but-useful: callers can
 * already opt into the new shape, and once the components flip, the
 * existing callers all funnel through this one helper.
 */

import type { OverlayItem } from "../../core/plugin/types";
import type { ViewerFinding } from "../../types";

const SEVERITY_TO_TIER: Record<
  ViewerFinding["severity"],
  NonNullable<OverlayItem["tier"]>
> = {
  error: "error",
  warning: "warning",
  advisory: "advisory",
  // Defensive default: an unknown severity reads as neutral so the
  // renderer at least picks a fallback colour from the host palette.
};

/**
 * Convert a single `ViewerFinding` to an `OverlayItem`.
 *
 * Returns `null` when the finding has no bbox + page combo to render.
 * Callers should `.filter(Boolean)` (or use `findingsToOverlayItems`).
 */
export function findingToOverlayItem(
  finding: ViewerFinding,
): OverlayItem | null {
  if (!finding.bbox || !finding.page_num) {
    return null;
  }
  const tier = SEVERITY_TO_TIER[finding.severity] ?? "neutral";
  return {
    id: `${finding.inspection_id}:${finding.page_num}:${finding.bbox.join(",")}`,
    page: finding.page_num,
    bbox: finding.bbox,
    tier,
    label: finding.message?.slice(0, 80),
    data: {
      inspection_id: finding.inspection_id,
      severity: finding.severity,
      // Carry the original record so click handlers can still reach
      // LintPDF-specific fields without round-trip lookups.
      finding,
    },
  };
}

/**
 * Convert a list of findings, dropping any that don't have a renderable
 * page+bbox.
 */
export function findingsToOverlayItems(
  findings: readonly ViewerFinding[],
): OverlayItem[] {
  const items: OverlayItem[] = [];
  for (const f of findings) {
    const item = findingToOverlayItem(f);
    if (item !== null) items.push(item);
  }
  return items;
}
