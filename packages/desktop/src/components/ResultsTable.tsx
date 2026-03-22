import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Loader,
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
    case "queued":
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
}

function statusLabel(status: JobResult["status"]): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
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
        <p className="text-xs mt-1">Start watching a folder to see results here</p>
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
            <th className="px-3 py-2 text-center">Aground</th>
            <th className="px-3 py-2 text-center">Squall</th>
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
                  isSelected
                    ? "bg-brand-50"
                    : "hover:bg-gray-50"
                } ${
                  job.status === "failed"
                    ? "bg-red-50/30"
                    : job.status === "error"
                      ? "bg-amber-50/30"
                      : ""
                }`}
              >
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <StatusIcon status={job.status} />
                    <span className="text-xs">{statusLabel(job.status)}</span>
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
                    <span className={job.summary.aground_count > 0 ? "text-red-600 font-medium" : "text-gray-400"}>
                      {job.summary.aground_count}
                    </span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center text-xs">
                  {job.summary ? (
                    <span className={job.summary.squall_count > 0 ? "text-amber-600 font-medium" : "text-gray-400"}>
                      {job.summary.squall_count}
                    </span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-center text-xs">
                  {job.summary ? (
                    <span className={job.summary.advisory_count > 0 ? "text-blue-600" : "text-gray-400"}>
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
