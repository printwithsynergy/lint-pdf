/** Shared types for the PDF viewer components. */

// ViewerHostContext / useViewerHost moved to src/core/host/ in Phase 2
// so src/core/** no longer needs to import from ../../types. The
// legacy `useViewerApi` / `ViewerApiContext` / `ViewerApiContextValue`
// names are re-exported below for back-compat — both the legacy and
// the new names point at the *same* React context object, so a
// `<ViewerApiContext.Provider>` mounted from outside `core/` is
// readable via `useViewerHost()` from inside `core/`.
export {
  ViewerHostContext as ViewerApiContext,
  useViewerHost as useViewerApi,
} from "./core/host";
export type { ViewerHostContextValue as ViewerApiContextValue } from "./core/host";

// PageBox / PageInfo / DielineResult / LayerInfo / ColorSample /
// DensitometerSample / DensitometerChannel / ViewerConfig /
// ViewerCapabilityKey / PreflightSourceMode / DEFAULT_VIEWER_CONFIG /
// DEFAULT_DPI / THUMBNAIL_DPI / SEVERITY_COLORS moved into
// src/core/types/ in Phase 2 so src/core/** doesn't import from
// ../../types. Re-exported below for back-compat — both names point
// at the *same* TypeScript declarations, so the move is invisible
// to downstream consumers.
export type {
  PageBox,
  PageInfo,
  DielineResult,
  LayerInfo,
  ColorSample,
  DensitometerChannel,
  DensitometerSample,
  ViewerCapabilityKey,
  PreflightSourceMode,
  ViewerConfig,
} from "./core/types";
export {
  DEFAULT_VIEWER_CONFIG,
  DEFAULT_DPI,
  THUMBNAIL_DPI,
  SEVERITY_COLORS,
} from "./core/types";

/**
 * AI accuracy-audit verdict attached to a finding when the tenant
 * has ``ai_audit_enabled`` (Scale + Enterprise plans) and the job's
 * preflight included the customer Modal audit pass. `null` (or the
 * whole `audit` field absent) means the finding was never audited
 * — the viewer renders no chip.
 */
export interface AuditVerdict {
  status: "confirmed" | "disputed" | "needs_context" | "error";
  rationale: string | null;
  model: string | null;
  at: string | null;
}

export interface ViewerFinding {
  inspection_id: string;
  severity: "error" | "warning" | "advisory";
  message: string;
  page_num: number | null;
  details: Record<string, unknown>;
  bbox: [number, number, number, number] | null;
  object_id: string | null;
  object_type: string | null;
  source: string;
  category: string | null;
  audit?: AuditVerdict | null;
}

/** WS-D art size derived from the dieline centerline. */
export interface ArtSizeMM {
  width_mm: number;
  height_mm: number;
}

/** WS-D per-swatch legend/art classification. */
export interface SwatchClassification {
  spot_name: string;
  bbox: [number, number, number, number];
  kind: "legend" | "art" | "unknown";
  source: "position" | "vision" | "position_only";
  confidence: number;
}

/** WS-C recovered OCR text block for outlined PDFs. */
export interface OCRTextBlock {
  text: string;
  bbox: [number, number, number, number];
  confidence: number;
}

export interface OCRPage {
  page_num: number;
  blocks: OCRTextBlock[];
}

export interface ViewerState {
  currentPage: number;
  zoom: number;
  selectedFinding: ViewerFinding | null;
  severityFilter: Set<string>;
}

export interface VerdictState {
  verdict: "pass" | "fail" | null;
  auto_passed: boolean | null;
  verdict_by: string | null;
  verdict_at: string | null;
  notes: string | null;
}

export interface ComparisonPageSummary {
  page_num: number;
  ssim_score: number;
  diff_pixel_count: number;
  total_pixels: number;
}

export interface ComparisonState {
  comparison_id: string;
  page_count_a: number;
  page_count_b: number;
  pages: ComparisonPageSummary[];
}

/**
 * Capabilities the viewer can request a one-off analyzer run for via
 * ``POST /api/lintpdf/viewer/{jobId}/capabilities/{capability}``. Kept
 * in sync with the engine's ``_FILLABLE_CAPABILITIES`` set.
 */
import type { ViewerCapabilityKey } from "./core/types";

export const FILLABLE_CAPABILITIES: readonly ViewerCapabilityKey[] = [
  "separations",
  "tac",
  "fonts",
  "images",
] as const;
