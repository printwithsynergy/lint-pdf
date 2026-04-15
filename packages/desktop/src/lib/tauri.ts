import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type {
  AppConfig,
  BrandProfileSummary,
  FolderConfig,
  JobResult,
  ShareLinks,
  WatcherStatus,
} from "./types";

// Config commands
export async function getConfig(): Promise<AppConfig> {
  return invoke("get_config");
}

export async function saveConfig(config: AppConfig): Promise<void> {
  return invoke("save_config", { config });
}

export async function addFolder(folder: FolderConfig): Promise<void> {
  return invoke("add_folder", { folder });
}

export async function removeFolder(folderId: string): Promise<void> {
  return invoke("remove_folder", { folderId });
}

export async function updateFolder(folder: FolderConfig): Promise<void> {
  return invoke("update_folder", { folder });
}

// Watcher commands
export async function startWatching(folderId: string): Promise<void> {
  return invoke("start_watching", { folderId });
}

export async function stopWatching(folderId: string): Promise<void> {
  return invoke("stop_watching", { folderId });
}

export async function startAll(): Promise<void> {
  return invoke("start_all");
}

export async function stopAll(): Promise<void> {
  return invoke("stop_all");
}

export async function getWatcherStatuses(): Promise<WatcherStatus[]> {
  return invoke("get_watcher_statuses");
}

// Job history commands
export async function getRecentJobs(limit: number): Promise<JobResult[]> {
  return invoke("get_recent_jobs", { limit });
}

export async function clearHistory(): Promise<void> {
  return invoke("clear_history");
}

// Engine API helpers
export async function listBrandProfiles(): Promise<BrandProfileSummary[]> {
  return invoke("list_brand_profiles");
}

export async function mintShareLink(
  localId: string,
  apiJobId: string,
  formats: Array<"html" | "pdf" | "json" | "xml">,
): Promise<ShareLinks> {
  return invoke("mint_share_link", {
    localId,
    apiJobId,
    formats,
  });
}

// Directory picker
export async function pickDirectory(): Promise<string | null> {
  const { open } = await import("@tauri-apps/plugin-dialog");
  const selected = await open({ directory: true, multiple: false });
  return selected as string | null;
}

// Event listeners
export function onJobUpdate(
  callback: (job: JobResult) => void,
): Promise<UnlistenFn> {
  return listen<JobResult>("job-update", (event) => callback(event.payload));
}

export function onWatcherStatus(
  callback: (status: WatcherStatus) => void,
): Promise<UnlistenFn> {
  return listen<WatcherStatus>("watcher-status", (event) =>
    callback(event.payload),
  );
}
