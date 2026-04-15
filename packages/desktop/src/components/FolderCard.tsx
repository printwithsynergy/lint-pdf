import { useEffect, useRef, useState } from "react";
import {
  FolderOpen,
  Play,
  Square,
  Edit,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import type {
  BrandMode,
  BrandProfileSummary,
  FolderConfig,
  JobResult,
  WatcherStatus,
} from "../lib/types";
import * as api from "../lib/tauri";

let brandProfileCache: {
  profiles: BrandProfileSummary[];
  fetchedAt: number;
} | null = null;
const BRAND_CACHE_TTL_MS = 60_000;

async function getBrandProfilesCached(): Promise<BrandProfileSummary[]> {
  const now = Date.now();
  if (brandProfileCache && now - brandProfileCache.fetchedAt < BRAND_CACHE_TTL_MS) {
    return brandProfileCache.profiles;
  }
  const profiles = await api.listBrandProfiles();
  brandProfileCache = { profiles, fetchedAt: now };
  return profiles;
}

interface FolderCardProps {
  folder: FolderConfig;
  status: WatcherStatus | undefined;
  jobs: JobResult[];
  onEdit: () => void;
  onRefreshStatuses: () => void;
}

export function FolderCard({
  folder,
  status,
  jobs,
  onEdit,
  onRefreshStatuses,
}: FolderCardProps) {
  const isActive = status?.active ?? false;
  const folderJobs = jobs.filter((j) => j.folder_id === folder.id);
  const passCount = folderJobs.filter((j) => j.status === "passed").length;
  const failCount = folderJobs.filter((j) => j.status === "failed").length;
  const errorCount = folderJobs.filter((j) => j.status === "error").length;

  const [brandProfiles, setBrandProfiles] = useState<BrandProfileSummary[]>([]);
  const loadedRef = useRef(false);

  async function ensureBrandProfilesLoaded() {
    if (loadedRef.current) return;
    loadedRef.current = true;
    try {
      const profiles = await getBrandProfilesCached();
      setBrandProfiles(profiles);
    } catch {
      // Silent — the compact dropdown shows the raw "profile:<id>" label as
      // a fallback; full editing is available in the folder editor.
    }
  }

  useEffect(() => {
    if (folder.brand_mode === "profile") {
      void ensureBrandProfilesLoaded();
    }
  }, [folder.brand_mode]);

  function brandLabelForCurrent(): string {
    if (folder.brand_mode !== "profile") return "";
    const match = brandProfiles.find((p) => p.id === folder.brand_profile_id);
    if (match) return `BrandProfile: ${match.name}`;
    if (folder.brand_profile_id) return "BrandProfile: (unknown)";
    return "BrandProfile: (none set)";
  }

  async function onBrandChange(next: BrandMode) {
    if (next === "profile") {
      await ensureBrandProfilesLoaded();
    }
    await api.updateFolder({
      ...folder,
      brand_mode: next,
      // Clear profile_id when switching away from "profile" mode so we don't
      // silently resend a stale UUID next time.
      brand_profile_id:
        next === "profile" ? folder.brand_profile_id : null,
    });
    onRefreshStatuses();
  }

  async function onBrandProfileChange(id: string) {
    await api.updateFolder({
      ...folder,
      brand_mode: "profile",
      brand_profile_id: id || null,
    });
    onRefreshStatuses();
  }

  async function toggleWatch() {
    if (isActive) {
      await api.stopWatching(folder.id);
    } else {
      await api.startWatching(folder.id);
    }
    onRefreshStatuses();
  }

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div
            className={`mt-0.5 rounded-lg p-2 ${
              isActive
                ? "bg-green-50 text-green-600"
                : "bg-gray-100 text-gray-400"
            }`}
          >
            <FolderOpen className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {folder.name || "Unnamed Folder"}
            </h3>
            <p className="mt-0.5 text-xs text-gray-500 font-mono truncate max-w-xs">
              {folder.watch_dir || "No directory set"}
            </p>
            <p className="mt-1 text-xs text-gray-400">
              Profile: {folder.profile_id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={toggleWatch}
            disabled={!folder.enabled || !folder.watch_dir}
            className={`rounded-lg p-1.5 transition-colors ${
              isActive
                ? "text-red-500 hover:bg-red-50"
                : "text-green-600 hover:bg-green-50"
            } disabled:opacity-30 disabled:cursor-not-allowed`}
            title={isActive ? "Stop watching" : "Start watching"}
          >
            {isActive ? (
              <Square className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4" />
            )}
          </button>
          <button
            onClick={onEdit}
            className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
            title="Edit folder"
          >
            <Edit className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Stats row */}
      {folderJobs.length > 0 && (
        <div className="mt-3 flex items-center gap-4 border-t border-gray-100 pt-3 text-xs">
          <span className="flex items-center gap-1 text-green-600">
            <CheckCircle className="h-3.5 w-3.5" />
            {passCount} passed
          </span>
          <span className="flex items-center gap-1 text-red-600">
            <XCircle className="h-3.5 w-3.5" />
            {failCount} failed
          </span>
          {errorCount > 0 && (
            <span className="flex items-center gap-1 text-amber-600">
              <AlertTriangle className="h-3.5 w-3.5" />
              {errorCount} errors
            </span>
          )}
          {status?.files_queued ? (
            // Files still stabilizing in the watcher — distinct from
            // the outbox's "queued" count shown in the connectivity
            // pill. Label as "pending" so the two counters don't
            // blur together.
            <span className="text-gray-400">
              {status.files_queued} pending
            </span>
          ) : null}
        </div>
      )}

      {/* Brand row */}
      <div className="mt-3 flex items-center gap-2 border-t border-gray-100 pt-3">
        <label className="text-xs text-gray-500">Brand</label>
        <select
          className="text-xs rounded border border-gray-200 bg-white px-2 py-1"
          value={folder.brand_mode}
          onChange={(e) => void onBrandChange(e.target.value as BrandMode)}
        >
          <option value="default">Use tenant default</option>
          <option value="anonymous">Anonymous</option>
          <option value="lintpdf">LintPDF</option>
          <option value="profile">BrandProfile…</option>
        </select>
        {folder.brand_mode === "profile" && (
          <select
            className="text-xs rounded border border-gray-200 bg-white px-2 py-1 max-w-[160px] truncate"
            value={folder.brand_profile_id ?? ""}
            onChange={(e) => void onBrandProfileChange(e.target.value)}
            title={brandLabelForCurrent()}
          >
            <option value="">Select…</option>
            {brandProfiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {!folder.enabled && (
        <p className="mt-2 text-xs text-amber-600">Disabled</p>
      )}
    </div>
  );
}
