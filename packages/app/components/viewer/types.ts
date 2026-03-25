/** Shared types for the PDF viewer components. */

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

export const SEVERITY_COLORS = {
  error: { fill: "rgba(239, 68, 68, 0.15)", stroke: "#ef4444" },
  warning: { fill: "rgba(245, 158, 11, 0.15)", stroke: "#f59e0b" },
  advisory: { fill: "rgba(59, 130, 246, 0.15)", stroke: "#3b82f6" },
} as const;

export const DEFAULT_DPI = 150;
export const THUMBNAIL_DPI = 72;
