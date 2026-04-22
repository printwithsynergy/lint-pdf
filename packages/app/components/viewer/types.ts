/** Shared types for the PDF viewer components. */

import { createContext, useContext } from "react";

/**
 * Context that provides the API base URL and read-only mode to all
 * viewer child components. In authenticated mode the base is
 * `/api/lintpdf/viewer/{jobId}`. In public-token mode it becomes
 * `/api/lintpdf/viewer/public/{token}` and `readOnly` is true (no
 * annotation writing, verdict setting, or comparison initiation).
 */
export interface ViewerApiContextValue {
  /** Base path for viewer API calls (no trailing slash). */
  apiBase: string;
  /** Base path for job-level API calls (findings, reports). */
  jobApiBase: string;
  /** When true, hide write-only UI (annotations, verdict, comparison). */
  readOnly: boolean;
}

export const ViewerApiContext = createContext<ViewerApiContextValue>({
  apiBase: "",
  jobApiBase: "",
  readOnly: false,
});

export function useViewerApi(): ViewerApiContextValue {
  return useContext(ViewerApiContext);
}

export interface PageBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface PageInfo {
  page_num: number;
  width_pts: number;
  height_pts: number;
  media_box: PageBox;
  crop_box: PageBox | null;
  trim_box: PageBox | null;
  bleed_box: PageBox | null;
  rotation: number;
}

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

export interface ViewerState {
  currentPage: number;
  zoom: number;
  selectedFinding: ViewerFinding | null;
  severityFilter: Set<string>;
}

/**
 * Capabilities keys the viewer reads from ``ViewerConfig.capabilities``.
 * Kept as a union so TS surfaces typos, but the server may add new keys
 * — the viewer treats unknown keys as present-but-unknown.
 */
export type ViewerCapabilityKey =
  | "findings"
  | "separations"
  | "tac"
  | "tac_runs"
  | "tiles_warmed"
  | "layers"
  | "fonts"
  | "images"
  | "thumbnails"
  | "metadata";

export type PreflightSourceMode = "engine" | "external" | "minimal";

export interface ViewerConfig {
  enable_separations: boolean;
  enable_tac_heatmap: boolean;
  enable_annotations: boolean;
  /** Public share-link only: whether anonymous visitors may create annotations.
   *  On the authenticated dashboard this is always implicitly true. */
  allow_annotations?: boolean;
  enable_measurement: boolean;
  enable_comparison: boolean;
  enable_layers: boolean;
  enable_findings_panel: boolean;
  enable_page_thumbnails: boolean;
  enable_zoom: boolean;
  enable_download: boolean;
  enable_html_report_link: boolean;
  verdict_mode: "auto" | "manual" | "disabled";
  default_zoom: number;
  default_dpi: number;
  default_tac_limit: number;
  viewer_logo_url: string | null;
  viewer_accent_color: string | null;
  toolbar_position: "top" | "bottom";
  dark_mode: boolean;
  /** Resolved branding — null fields when ``anonymous`` is true. */
  brand_name: string | null;
  brand_logo_url: string | null;
  brand_primary_color: string | null;
  brand_accent_color: string | null;
  /** True when the viewer must hide all tenant + LintPDF chrome. */
  anonymous: boolean;
  tenant_name: string | null;
  support_email: string | null;
  /** How findings were produced for this job. */
  preflight_source: PreflightSourceMode;
  /** Per-capability availability map (true = backed by data). */
  capabilities: Partial<Record<ViewerCapabilityKey, boolean>>;
  /** Plan-gate: false means the tenant may not invoke on-demand
   *  capability fill-in (Viewer tier). The UI must hide Load buttons and
   *  render an ``UpgradePrompt`` instead. */
  capability_fillin_enabled: boolean;
  /** Plan-gate: false means the viewer must hide the annotation toolbar
   *  and disable annotation write paths. */
  annotations_enabled: boolean;
  /** Plan-gate: empty means report downloads are not available (Viewer
   *  tier). The share-link is the only output. */
  allowed_report_formats: string[];
  tile_cdn_base: string | null;
}

export interface LayerInfo {
  name: string;
  ocg_index: number;
  default_on: boolean;
}

export interface ColorSample {
  x: number;
  y: number;
  rgb: [number, number, number];
  hex: string;
  tac: number | null;
}

export interface DensitometerChannel {
  name: string;
  percent: number;
}

export interface DensitometerSample {
  x: number;
  y: number;
  dpi: number;
  channels: DensitometerChannel[];
  tac: number;
  tac_limit: number;
  limit_exceeded: boolean;
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

export const SEVERITY_COLORS = {
  error: { fill: "rgba(239, 68, 68, 0.15)", stroke: "#ef4444" },
  warning: { fill: "rgba(245, 158, 11, 0.15)", stroke: "#f59e0b" },
  advisory: { fill: "rgba(59, 130, 246, 0.15)", stroke: "#3b82f6" },
} as const;

export const DEFAULT_DPI = 150;
export const THUMBNAIL_DPI = 72;

export const DEFAULT_VIEWER_CONFIG: ViewerConfig = {
  enable_separations: true,
  enable_tac_heatmap: true,
  enable_annotations: true,
  enable_measurement: true,
  enable_comparison: true,
  enable_layers: true,
  enable_findings_panel: true,
  enable_page_thumbnails: true,
  enable_zoom: true,
  enable_download: true,
  enable_html_report_link: true,
  verdict_mode: "auto",
  default_zoom: 100,
  default_dpi: 150,
  default_tac_limit: 300,
  viewer_logo_url: null,
  viewer_accent_color: null,
  toolbar_position: "top",
  dark_mode: false,
  // Leave brand_name / brand_logo_url null in the default config so consumers
  // fall back to tenant branding or hostFallbackClient() — preventing "LintPDF"
  // from leaking onto custom-domain viewer pages.
  brand_name: null,
  brand_logo_url: null,
  brand_primary_color: "#1a3a7a",
  brand_accent_color: "#2563eb",
  anonymous: false,
  tenant_name: null,
  support_email: null,
  preflight_source: "engine",
  capabilities: {
    findings: true,
    separations: true,
    tac: true,
    tac_runs: true,
    tiles_warmed: false,
    layers: true,
    fonts: true,
    images: true,
    thumbnails: true,
    metadata: true,
  },
  capability_fillin_enabled: true,
  annotations_enabled: true,
  allowed_report_formats: ["json", "html", "pdf", "xml"],
  tile_cdn_base: null,
};

/**
 * Capabilities the viewer can request a one-off analyzer run for via
 * ``POST /api/lintpdf/viewer/{jobId}/capabilities/{capability}``. Kept
 * in sync with the engine's ``_FILLABLE_CAPABILITIES`` set.
 */
export const FILLABLE_CAPABILITIES: readonly ViewerCapabilityKey[] = [
  "separations",
  "tac",
  "fonts",
  "images",
] as const;
