import { CheckCircle, XCircle, AlertTriangle, FileText, X } from "lucide-react";
import type { JobResult } from "../lib/types";

interface ResultDetailProps {
  job: JobResult;
  onClose: () => void;
}

export function ResultDetail({ job, onClose }: ResultDetailProps) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-gray-400" />
          <div>
            <h3 className="text-sm font-semibold font-mono">{job.file_name}</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Job ID: {job.job_id || "N/A"}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="label">Status</span>
          <div className="flex items-center gap-1.5">
            {job.status === "passed" && (
              <CheckCircle className="h-4 w-4 text-green-600" />
            )}
            {job.status === "failed" && (
              <XCircle className="h-4 w-4 text-red-600" />
            )}
            {job.status === "error" && (
              <AlertTriangle className="h-4 w-4 text-amber-600" />
            )}
            <span className="capitalize">{job.status}</span>
          </div>
        </div>
        <div>
          <span className="label">Submitted</span>
          <p className="text-xs">
            {job.submitted_at
              ? new Date(job.submitted_at).toLocaleString()
              : "—"}
          </p>
        </div>
        {job.completed_at && (
          <div>
            <span className="label">Completed</span>
            <p className="text-xs">
              {new Date(job.completed_at).toLocaleString()}
            </p>
          </div>
        )}
        {job.routed_to && (
          <div>
            <span className="label">Routed to</span>
            <p className="text-xs font-mono truncate">{job.routed_to}</p>
          </div>
        )}
      </div>

      {job.summary && (
        <div className="mt-4 border-t border-gray-100 pt-3">
          <span className="label">Findings</span>
          <div className="flex items-center gap-6 mt-1">
            <div className="text-center">
              <p
                className={`text-lg font-bold ${job.summary.error_count > 0 ? "text-red-600" : "text-gray-300"}`}
              >
                {job.summary.error_count}
              </p>
              <p className="text-xs text-gray-500">Error</p>
            </div>
            <div className="text-center">
              <p
                className={`text-lg font-bold ${job.summary.warning_count > 0 ? "text-amber-600" : "text-gray-300"}`}
              >
                {job.summary.warning_count}
              </p>
              <p className="text-xs text-gray-500">Warning</p>
            </div>
            <div className="text-center">
              <p
                className={`text-lg font-bold ${job.summary.advisory_count > 0 ? "text-blue-600" : "text-gray-300"}`}
              >
                {job.summary.advisory_count}
              </p>
              <p className="text-xs text-gray-500">Advisory</p>
            </div>
          </div>
        </div>
      )}

      {job.error_message && (
        <div className="mt-4 rounded-lg bg-red-50 p-3 text-xs text-red-700">
          <p className="font-medium">Error</p>
          <p className="mt-1">{job.error_message}</p>
        </div>
      )}
    </div>
  );
}
