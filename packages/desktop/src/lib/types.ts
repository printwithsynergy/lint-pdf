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
}

export interface AppConfig {
  version: number;
  api_key: string;
  base_url: string;
  folders: FolderConfig[];
  notifications_enabled: boolean;
  start_minimized: boolean;
  launch_at_login: boolean;
}

export type JobStatus = "queued" | "processing" | "passed" | "failed" | "error";

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
    ...partial,
  };
}
