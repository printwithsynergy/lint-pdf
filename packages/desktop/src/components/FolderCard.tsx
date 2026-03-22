import {
  FolderOpen,
  Play,
  Square,
  Edit,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import type { FolderConfig, JobResult, WatcherStatus } from "../lib/types";
import * as api from "../lib/tauri";

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
            <span className="text-gray-400">{status.files_queued} queued</span>
          ) : null}
        </div>
      )}

      {!folder.enabled && (
        <p className="mt-2 text-xs text-amber-600">Disabled</p>
      )}
    </div>
  );
}
