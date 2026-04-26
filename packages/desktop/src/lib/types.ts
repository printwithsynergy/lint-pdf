/**
 * How a folder should brand the reports it submits.
 *
 * Maps directly to the `brand` parameter accepted by `POST /api/v1/jobs`:
 *  - `default`   — send nothing (engine uses tenant default).
 *  - `anonymous` — strip branding entirely.
 *  - `lintpdf`   — force LintPDF default branding.
 *  - `profile`   — use a specific BrandProfile (requires `brand_profile_id`).
 */
export type BrandMode = "default" | "anonymous" | "lintpdf" | "profile";

export type ExternalFormat =
  | "pitstop_xml"
  | "callas_json"
  | "callas_xml"
  | "acrobat_xml"
  | "lintpdf_json";

export interface FolderConfig {
  id: string;
  name: string;
  enabled: boolean;
  watch_dir: string;
  profile_id: string;
  pass_dir: string;
  fail_dir: string;
  error_dir: string;
  write_sidecar: boolean;
  stabilization_secs: number;
  poll_interval_secs: number;
  file_extensions: string[];
  brand_mode: BrandMode;
  brand_profile_id: string | null;
  jdf_companion_timeout_secs: number;
  endpoint_id: string | null;
  external_format: ExternalFormat | null;
  approval_template_id: string | null;
  batch_enabled: boolean;
  batch_window_secs: number;
}

export interface BrandProfileSummary {
  id: string;
  name: string;
  is_default: boolean;
}

export interface ShareLinks {
  html?: string;
  pdf?: string;
  json?: string;
  xml?: string;
  annotated_pdf?: string;
}

export interface EndpointSummary {
  id: string;
  slug: string;
  profile_id: string;
  description: string | null;
  is_active: boolean;
}

export interface ApprovalTemplateSummary {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
}

export interface AiInterpretation {
  summary: string;
  interpretations: Array<{
    inspection_id?: string;
    explanation?: string;
    why_it_matters?: string;
    suggestion?: string;
  }>;
}

export interface TenantBranding {
  brandName?: string | null;
  brandLogoUrl?: string | null;
  brandLogoUrlDark?: string | null;
  brandTagline?: string | null;
  primaryColor?: string | null;
  accentColor?: string | null;
  emailButtonColor?: string | null;
  loginBgColor?: string | null;
  loginCardColor?: string | null;
  loginTextColor?: string | null;
  faviconUrl?: string | null;
  loginHeading?: string | null;
  loginSubheading?: string | null;
  // Branding shapes evolve upstream — keep room for fields the desktop
  // app does not yet read so JSON round-trips without loss.
  [key: string]: unknown;
}

export interface TenantLookupResponse {
  tenantId: string;
  name: string;
  slug: string;
  domain: string | null;
  branding: TenantBranding;
}

export interface AppConfig {
  version: number;
  api_key: string;
  base_url: string;
  app_base_url: string;
  tenant_id: string;
  tenant_name: string;
  tenant_branding: TenantBranding | null;
  folders: FolderConfig[];
  notifications_enabled: boolean;
  start_minimized: boolean;
  launch_at_login: boolean;
}

export type JobStatus =
  | "queued"
  | "queued_offline"
  | "queued_retry"
  | "processing"
  | "passed"
  | "failed"
  | "error";

export interface ConnectivityStatus {
  online: boolean;
  /** True when an auth failure (401/403) occurred recently. */
  auth_failure: boolean;
  /** RFC3339 of the last successful /health probe, or null if never. */
  last_success_at: string | null;
  /** RFC3339 of the last attempt (success or failure). */
  last_checked_at: string | null;
  /** Count of queued_offline + queued_retry rows right now. */
  queued_count: number;
}

export interface TestConnectionResult {
  health_ok: boolean;
  auth_ok: boolean;
  latency_ms: number;
  error: string | null;
}

// ── Viewer types ─────────────────────────────────────────────

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

export interface PagesResponse {
  job_id: string;
  page_count: number;
  pages: PageInfo[];
}

export interface SeparationChannel {
  name: string;
  type: string; // "process" | "spot"
}

export interface SeparationsResponse {
  job_id: string;
  channels: SeparationChannel[];
}

export interface LayerInfo {
  name: string;
  ocg_index: number;
  default_on: boolean;
}

export interface LayersResponse {
  job_id: string;
  layers: LayerInfo[];
}

export interface ViewerAnnotation {
  id: string;
  job_id: string;
  page_num: number;
  kind: string;
  geometry: Record<string, unknown>;
  color: string | null;
  text: string | null;
  author_email: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ViewerFinding {
  inspection_id: string;
  severity: "error" | "warning" | "advisory" | string;
  message: string;
  page_num: number | null;
  bbox: number[] | null;
  category: string | null;
  source: string | null;
  object_id: string | null;
  object_type: string | null;
}

export interface ViewerConfig {
  enable_separations: boolean;
  enable_tac_heatmap: boolean;
  enable_annotations: boolean;
  enable_measurement: boolean;
  enable_layers: boolean;
  enable_findings_panel: boolean;
  enable_page_thumbnails: boolean;
  enable_zoom: boolean;
  default_zoom: number | null;
  default_dpi: number | null;
  default_tac_limit: number | null;
  preflight_source: string | null;
  capabilities: Record<string, boolean>;
}

export interface VerdictResponse {
  verdict: string | null;
  auto_passed: boolean | null;
  verdict_by: string | null;
  verdict_at: string | null;
  notes: string | null;
}

export interface TacRun {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  mean_tac: number;
  limit: number;
  exceeds: boolean;
}

export interface TacRunsResponse {
  job_id: string;
  page_num: number;
  dpi: number;
  tac_limit: number;
  runs: TacRun[];
}

export interface DensitometerChannel {
  name: string;
  percent: number;
}

export interface DensitometerResponse {
  x: number;
  y: number;
  dpi: number;
  channels: DensitometerChannel[];
  tac: number;
  tac_limit: number;
  limit_exceeded: boolean;
}

export interface TileResult {
  path: string;
  bytes: number;
  from_cache: boolean;
}

export interface JobSummary {
  passed: boolean;
  error_count: number;
  warning_count: number;
  advisory_count: number;
}

export interface JobResult {
  id: string;
  folder_id: string;
  file_name: string;
  file_path: string;
  status: JobStatus;
  job_id: string | null;
  summary: JobSummary | null;
  routed_to: string | null;
  submitted_at: string;
  completed_at: string | null;
  error_message: string | null;
  share_links: ShareLinks | null;
  jdf_path: string | null;
  batch_group: string | null;
  batch_id: string | null;
  next_retry_at: string | null;
  retry_attempts: number;
}

export interface WatcherStatus {
  folder_id: string;
  active: boolean;
  files_queued: number;
  files_processed: number;
  last_error: string | null;
}

export const DEFAULT_EXTENSIONS = [
  ".pdf",
  ".eps",
  ".ps",
  ".tiff",
  ".tif",
  ".jpg",
  ".jpeg",
  ".png",
  ".ai",
  ".jdf",
  ".xjdf",
];

/// Extensions recognised as pre-existing external preflight reports (PitStop,
/// Callas, Acrobat, LintPDF native). Enabled only when a folder has an
/// `external_format` configured or selects auto-detect.
export const EXTERNAL_REPORT_EXTENSIONS = [".xml", ".json"];

export function newFolderConfig(partial?: Partial<FolderConfig>): FolderConfig {
  return {
    id: crypto.randomUUID(),
    name: "",
    enabled: true,
    watch_dir: "",
    profile_id: "lintpdf-default",
    pass_dir: "",
    fail_dir: "",
    error_dir: "",
    write_sidecar: true,
    stabilization_secs: 2.0,
    poll_interval_secs: 5.0,
    file_extensions: [...DEFAULT_EXTENSIONS],
    brand_mode: "default",
    brand_profile_id: null,
    jdf_companion_timeout_secs: 30.0,
    endpoint_id: null,
    external_format: null,
    approval_template_id: null,
    batch_enabled: false,
    batch_window_secs: 10.0,
    ...partial,
  };
}
