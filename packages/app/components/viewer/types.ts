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

/** Default LintPDF logo as an embedded SVG data URI — used when no tenant
 *  branding override is configured. */
const LINTPDF_DEFAULT_LOGO =
  "data:image/svg+xml;base64," +
  "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB3aWR0aD0iMTAy" +
  "NCIgaGVpZ2h0PSIxMDI0IiB2aWV3Qm94PSIwIDAgMTAyNCAxMDI0IiBmaWxsPSJub25lIiB4" +
  "bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDx0aXRsZT5MaW50UERGLXN0" +
  "eWxlIGJyYWNrZXQgbG9nbzwvdGl0bGU+CiAgPGRlc2M+VmVjdG9yIHJlY3JlYXRpb24gb2Yg" +
  "dGhlIHVwbG9hZGVkIGZsYXQgYnJhY2tldCBsb2dvLjwvZGVzYz4KICA8IS0tIEJhY2tncm91" +
  "bmQgLS0+CiAgPHJlY3QgeD0iMTgiIHk9IjE4IiB3aWR0aD0iOTg4IiBoZWlnaHQ9Ijk4OCIg" +
  "cng9IjE2NSIgZmlsbD0iIzQwODdGNyIvPgogIDwhLS0gQ2VudGVyIGNvbnRlbnQgYXJlYSAt" +
  "LT4KICA8IS0tIEJyYWNrZXRzIC0tPgogIDxwYXRoIGQ9Ik0yMTAgMjcwCiAgICAgICAgICAg" +
  "QzIxMCAyMzYgMjM2IDIxMCAyNzAgMjEwCiAgICAgICAgICAgSDM1OAogICAgICAgICAgIEMz" +
  "ODAgMjEwIDM5OCAyMjggMzk4IDI1MAogICAgICAgICAgIEMzOTggMjcyIDM4MCAyOTAgMzU4" +
  "IDI5MAogICAgICAgICAgIEgyNjYKICAgICAgICAgICBWNzM0CiAgICAgICAgICAgSDM1OAogICAg" +
  "ICAgICAgIEMzODAgNzM0IDM5OCA3NTIgMzk4IDc3NAogICAgICAgICAgIEMzOTggNzk2IDM4" +
  "MCA4MTQgMzU4IDgxNAogICAgICAgICAgIEgyNzAKICAgICAgICAgICBDMjM2IDgxNCAyMTAg" +
  "Nzg4IDIxMCA3NTQKICAgICAgICAgICBWMjcwWiIKICAgICAgICBmaWxsPSIjRjJGMkYyIi8+" +
  "CiAgPHBhdGggZD0iTTgxNCAyNzAKICAgICAgICAgICBDODE0IDIzNiA3ODggMjEwIDc1NCAy" +
  "MTAKICAgICAgICAgICBINjY2CiAgICAgICAgICAgQzY0NCAyMTAgNjI2IDIyOCA2MjYgMjUw" +
  "CiAgICAgICAgICAgQzYyNiAyNzIgNjQ0IDI5MCA2NjYgMjkwCiAgICAgICAgICAgSDc1OAog" +
  "ICAgICAgICAgIFY3MzQKICAgICAgICAgICBINjY2CiAgICAgICAgICAgQzY0NCA3MzQgNjI2" +
  "IDc1MiA2MjYgNzc0CiAgICAgICAgICAgQzYyNiA3OTYgNjQ0IDgxNCA2NjYgODE0CiAgICAg" +
  "ICAgICAgSDc1NAogICAgICAgICAgIEM3ODggODE0IDgxNCA3ODggODE0IDc1NAogICAgICAg" +
  "ICAgIFYyNzBaIgogICAgICAgIGZpbGw9IiNGMkYyRjIiLz4KICA8IS0tIFRleHQgbGluZXMg" +
  "LS0+CiAgPHJlY3QgeD0iMzQ3IiB5PSIzNTYiIHdpZHRoPSIzMzAiIGhlaWdodD0iMzYiIHJ4" +
  "PSIxOCIgZmlsbD0iIzkzQzVGRCIvPgogIDxyZWN0IHg9IjM5MiIgeT0iNDU1IiB3aWR0aD0i" +
  "MjQwIiBoZWlnaHQ9IjM2IiByeD0iMTgiIGZpbGw9IiM5M0M1RkQiLz4KICA8cmVjdCB4PSIz" +
  "NjYiIHk9IjU1NCIgd2lkdGg9IjI5NCIgaGVpZ2h0PSIzNiIgcng9IjE4IiBmaWxsPSIjOTND" +
  "NUZEIi8+Cjwvc3ZnPgo=";

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
  brand_name: "LintPDF",
  brand_logo_url: LINTPDF_DEFAULT_LOGO,
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
    layers: true,
    fonts: true,
    images: true,
    thumbnails: true,
    metadata: true,
  },
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
