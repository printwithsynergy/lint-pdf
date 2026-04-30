/**
 * LintPDF → OverlayItem adapter.
 *
 * Translates LintPDF-domain `ViewerFinding` records into the generic
 * `OverlayItem` interface that core components consume. This is the
 * one place that knows about the LintPDF severity palette + the
 * inspection-id → tier mapping + the message-cleanup heuristics that
 * keep PDF object references from leaking into tooltip text.
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

// LintPDF findings often carry verbose PDF object references in their
// messages (e.g., 'FormXob.6b8351906abc...'). Strip them so tooltips
// stay readable. The original message is still available via
// OverlayItem.data.finding for callers that want the raw text.
function cleanMessage(message: string): string {
  return message
    .replace(/'[A-Za-z]+\.[a-f0-9]{16,}'/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Convert a single `ViewerFinding` to an `OverlayItem`.
 *
 * Returns `null` only when the finding has no `page_num` to render
 * against — bbox-less findings still produce an `OverlayItem` (the
 * renderer can fall back to a page-level indicator).
 */
export function findingToOverlayItem(
  finding: ViewerFinding,
): OverlayItem | null {
  if (!finding.page_num) {
    return null;
  }
  const tier = SEVERITY_TO_TIER[finding.severity] ?? "neutral";
  const cleaned = finding.message ? cleanMessage(finding.message) : "";
  // Stable id: bbox-less findings just use inspection_id+page so two
  // page-level findings with the same inspection_id on the same page
  // dedupe sensibly.
  const idSuffix = finding.bbox
    ? `:${finding.bbox.join(",")}`
    : "";
  return {
    id: `${finding.inspection_id}:${finding.page_num}${idSuffix}`,
    page: finding.page_num,
    ...(finding.bbox ? { bbox: finding.bbox } : {}),
    tier,
    code: finding.inspection_id,
    label: cleaned.slice(0, 80),
    description: cleaned,
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
 * Convert a list of findings, dropping any that have no renderable
 * page number.
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
