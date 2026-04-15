import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Loader,
  CloudOff,
  RotateCw,
} from "lucide-react";
import type { FolderConfig, JobResult } from "../lib/types";

interface ResultsTableProps {
  jobs: JobResult[];
  folders: FolderConfig[];
  selectedJob: JobResult | null;
  onSelect: (job: JobResult) => void;
}

function StatusIcon({ status }: { status: JobResult["status"] }) {
  switch (status) {
    case "passed":
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-600" />;
    case "error":
      return <AlertTriangle className="h-4 w-4 text-amber-600" />;
    case "processing":
      return <Loader className="h-4 w-4 text-blue-600 animate-spin" />;
    case "queued_offline":
      return <CloudOff className="h-4 w-4 text-gray-500" />;
    case "queued_retry":
      return <RotateCw className="h-4 w-4 text-amber-500" />;
    case "queued":
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
}

function statusLabel(status: JobResult["status"]): string {
  switch (status) {
    case "queued_offline":
      return "Waiting for connection";
    case "queued_retry":
      return "Retrying";
    default:
      return status.charAt(0).toUpperCase() + status.slice(1);
  }
}

function retryHint(job: JobResult): string | null {
  if (job.status !== "queued_retry" || !job.next_retry_at) return null;
  const secs = Math.max(
    0,
    Math.round((new Date(job.next_retry_at).getTime() - Date.now()) / 1000),
  );
  if (secs <= 0) return "retrying now";
  if (secs < 60) return `retry in ${secs}s`;
  const mins = Math.floor(secs / 60);
  return `retry in ${mins}m`;
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function ResultsTable({
  jobs,
  folders,
  selectedJob,
  onSelect,
}: ResultsTableProps) {
  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        <Clock className="h-8 w-8 mb-2" />
        <p className="text-sm">No results yet</p>
        <p className="text-xs mt-1">
          Start watching a folder to see results here
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">File</th>
            <th className="px-3 py-2">Folder</th>
            <th className="px-3 py-2 text-center">Errors</th>
            <th className="px-3 py-2 text-center">Warnings</th>
            <th className="px-3 py-2 text-center">Advisory</th>
            <th className="px-3 py-2 text-right">Time</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const folder = folders.find((f) => f.id === job.folder_id);
            const isSelected = selectedJob?.id === job.id;
            return (
              <tr
                key={job.id}
                onClick={() => onSelect(job)}
                className={`border-b border-gray-100 cursor-pointer transition-colors ${
                  isSelected ? "bg-brand-50" : "hover:bg-gray-50"
                } ${
                  job.status === "failed"
                    ? "bg-red-50/30"
                    : job.status === "error"
                      ? "bg-amber-50/30"
                      : job.status === "queued_offline" ||
                          job.status === "queued_retry"
                        ? "bg-gray-50/40"
                        : ""
                }`}
              >
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <StatusIcon status={job.status} />
                    <div className="flex flex-col">
                      <span className="text-xs">{statusLabel(job.status)}</span>
                      {retryHint(job) && (
                        <span className="text-[10px] text-amber-600">
                          {retryHint(job)}
                        </span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-3 py-2 font-mono text-xs truncate max-w-[200px]">
                  {job.file_name}
                </td>
                <td className="px-3 py-2 text-xs text-gray-500">
                  {folder?.name || "Unknown"}
                </td>
                <td className="px-3 py-2 text-center text-xs">
                  {job.summary ? (
                    <span
                      className={
                        job.summary.error_count > 0
                          ? "text-red-600 font-medium"
                          : "text-gray-400"
                      }
                    >
                      {job.summary.error_count}
                    </span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center text-xs">
                  {job.summary ? (
                    <span
                      className={
                        job.summary.warning_count > 0
                          ? "text-amber-600 font-medium"
                          : "text-gray-400"
                      }
                    >
                      {job.summary.warning_count}
                    </span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center text-xs">
                  {job.summary ? (
                    <span
                      className={
                        job.summary.advisory_count > 0
                          ? "text-blue-600"
                          : "text-gray-400"
                      }
                    >
                      {job.summary.advisory_count}
                    </span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-xs text-gray-400">
                  {timeAgo(job.submitted_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
