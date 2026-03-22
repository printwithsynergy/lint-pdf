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
  aground_count: number;
  squall_count: number;
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
];

export function newFolderConfig(partial?: Partial<FolderConfig>): FolderConfig {
  return {
    id: crypto.randomUUID(),
    name: "",
    enabled: true,
    watch_dir: "",
    profile_id: "grounded-default",
    pass_dir: "",
    fail_dir: "",
    error_dir: "",
    write_sidecar: true,
    stabilization_secs: 2.0,
    poll_interval_secs: 5.0,
    file_extensions: [...DEFAULT_EXTENSIONS],
    ...partial,
  };
}
