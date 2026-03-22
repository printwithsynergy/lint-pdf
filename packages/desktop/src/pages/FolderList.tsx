import { Plus, Play, Square } from "lucide-react";
import type {
  AppConfig,
  FolderConfig,
  JobResult,
  WatcherStatus,
} from "../lib/types";
import { newFolderConfig } from "../lib/types";
import { FolderCard } from "../components/FolderCard";
import * as api from "../lib/tauri";

interface FolderListProps {
  config: AppConfig;
  statuses: WatcherStatus[];
  jobs: JobResult[];
  onEdit: (folder: FolderConfig) => void;
  onAdd: (folder: FolderConfig) => void;
  onRefresh: () => void;
  onRefreshStatuses: () => void;
}

export function FolderList({
  config,
  statuses,
  jobs,
  onEdit,
  onAdd,
  onRefreshStatuses,
}: FolderListProps) {
  const anyActive = statuses.some((s) => s.active);

  async function handleStartAll() {
    await api.startAll();
    onRefreshStatuses();
  }

  async function handleStopAll() {
    await api.stopAll();
    onRefreshStatuses();
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Hot Folders</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Configure directories to watch for files to preflight
          </p>
        </div>
        <div className="flex items-center gap-2">
          {config.folders.length > 0 && (
            <button
              onClick={anyActive ? handleStopAll : handleStartAll}
              className="btn-secondary text-xs"
            >
              {anyActive ? (
                <>
                  <Square className="h-3.5 w-3.5" /> Stop All
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" /> Start All
                </>
              )}
            </button>
          )}
          <button
            onClick={() => onAdd(newFolderConfig())}
            className="btn-primary text-xs"
          >
            <Plus className="h-3.5 w-3.5" /> Add Folder
          </button>
        </div>
      </div>

      {config.folders.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-xl bg-gray-100 p-4 mb-4">
            <Plus className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-900">No hot folders</h3>
          <p className="text-xs text-gray-500 mt-1 max-w-xs">
            Add a folder to start watching for files. Each folder can have its
            own preflight profile and output directories.
          </p>
          <button
            onClick={() => onAdd(newFolderConfig())}
            className="btn-primary mt-4 text-xs"
          >
            <Plus className="h-3.5 w-3.5" /> Add Your First Folder
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {config.folders.map((folder) => (
            <FolderCard
              key={folder.id}
              folder={folder}
              status={statuses.find((s) => s.folder_id === folder.id)}
              jobs={jobs}
              onEdit={() => onEdit(folder)}
              onRefreshStatuses={onRefreshStatuses}
            />
          ))}
        </div>
      )}
    </div>
  );
}
