import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type {
  AiInterpretation,
  AppConfig,
  ApprovalTemplateSummary,
  BrandProfileSummary,
  ConnectivityStatus,
  DensitometerResponse,
  EndpointSummary,
  FolderConfig,
  JobResult,
  LayersResponse,
  PagesResponse,
  SeparationsResponse,
  ShareLinks,
  TacRunsResponse,
  TestConnectionResult,
  TileResult,
  VerdictResponse,
  ViewerAnnotation,
  ViewerConfig,
  ViewerFinding,
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
  formats: Array<"html" | "pdf" | "json" | "xml" | "annotated_pdf">,
): Promise<ShareLinks> {
  return invoke("mint_share_link", {
    localId,
    apiJobId,
    formats,
  });
}

export async function listEndpoints(): Promise<EndpointSummary[]> {
  return invoke("list_endpoints");
}

export async function listApprovalTemplates(): Promise<
  ApprovalTemplateSummary[]
> {
  return invoke("list_approval_templates");
}

export async function getAiInterpretation(
  apiJobId: string,
): Promise<AiInterpretation> {
  return invoke("get_ai_interpretation", { apiJobId });
}

// Connectivity
export async function getConnectivityStatus(): Promise<ConnectivityStatus> {
  return invoke("get_connectivity_status");
}

export async function forceConnectivityCheck(): Promise<void> {
  return invoke("force_connectivity_check");
}

export function onConnectivityChange(
  callback: (status: ConnectivityStatus) => void,
): Promise<UnlistenFn> {
  return listen<ConnectivityStatus>("connectivity-change", (event) =>
    callback(event.payload),
  );
}

// Viewer
export async function openViewerWindow(
  url: string,
  title: string,
): Promise<void> {
  return invoke("open_viewer_window", { url, title });
}

// Test connection — used by the Settings page before the user commits
// their API key / base URL.
export async function testConnection(
  baseUrl: string,
  apiKey: string,
): Promise<TestConnectionResult> {
  return invoke("test_connection", { baseUrl, apiKey });
}

// Retry a row that went to terminal `error`. The row flips back to
// `queued_retry` and the drainer picks it up on the next tick.
export async function retryJob(localId: string): Promise<void> {
  return invoke("retry_job", { localId });
}

// ── Native viewer ────────────────────────────────────────────

export async function viewerPages(jobId: string): Promise<PagesResponse> {
  return invoke("viewer_pages", { jobId });
}

export async function viewerSeparations(
  jobId: string,
): Promise<SeparationsResponse> {
  return invoke("viewer_separations", { jobId });
}

export async function viewerLayers(jobId: string): Promise<LayersResponse> {
  return invoke("viewer_layers", { jobId });
}

export async function viewerAnnotations(
  jobId: string,
): Promise<ViewerAnnotation[]> {
  return invoke("viewer_annotations", { jobId });
}

export async function viewerConfig(jobId: string): Promise<ViewerConfig> {
  return invoke("viewer_config", { jobId });
}

export async function viewerVerdict(jobId: string): Promise<VerdictResponse> {
  return invoke("viewer_verdict", { jobId });
}

export async function viewerFindings(
  jobId: string,
): Promise<ViewerFinding[]> {
  return invoke("viewer_findings", { jobId });
}

/**
 * OCG (layer) toggle mask. ``on`` forces visibility; ``off`` forces
 * hiding. Empty arrays mean "use PDF defaults" — and also mean the
 * engine/tile-cache key matches the pre-Phase-5 layout, so warmed
 * tiles still hit.
 */
export interface OcgMask {
  on: number[];
  off: number[];
}

export async function viewerTile(
  jobId: string,
  pageNum: number,
  dpi?: number,
  ocg?: OcgMask,
): Promise<TileResult> {
  return invoke("viewer_tile", {
    jobId,
    pageNum,
    dpi,
    ocgOn: ocg?.on ?? null,
    ocgOff: ocg?.off ?? null,
  });
}

export async function viewerChannelTile(
  jobId: string,
  pageNum: number,
  channel: string,
  dpi?: number,
  ocg?: OcgMask,
): Promise<TileResult> {
  return invoke("viewer_channel_tile", {
    jobId,
    pageNum,
    channel,
    dpi,
    ocgOn: ocg?.on ?? null,
    ocgOff: ocg?.off ?? null,
  });
}

export async function viewerTacHeatmap(
  jobId: string,
  pageNum: number,
  dpi?: number,
  tacLimit?: number,
  ocg?: OcgMask,
): Promise<TileResult> {
  return invoke("viewer_tac_heatmap", {
    jobId,
    pageNum,
    dpi,
    tacLimit,
    ocgOn: ocg?.on ?? null,
    ocgOff: ocg?.off ?? null,
  });
}

export async function viewerTacRuns(
  jobId: string,
  pageNum: number,
  dpi: number,
  tacLimit: number,
): Promise<TacRunsResponse> {
  return invoke("viewer_tac_runs", { jobId, pageNum, dpi, tacLimit });
}

export async function viewerDensitometer(
  jobId: string,
  pageNum: number,
  x: number,
  y: number,
  dpi?: number,
  tacLimit?: number,
): Promise<DensitometerResponse> {
  return invoke("viewer_densitometer", {
    jobId,
    pageNum,
    x,
    y,
    dpi,
    tacLimit,
  });
}

export async function viewerClearTileCache(jobId: string): Promise<void> {
  return invoke("viewer_clear_tile_cache", { jobId });
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
