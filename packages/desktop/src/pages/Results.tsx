import { useState } from "react";
import { Trash2 } from "lucide-react";
import type { FolderConfig, JobResult } from "../lib/types";
import { ResultsTable } from "../components/ResultsTable";
import { ResultDetail } from "../components/ResultDetail";

interface ResultsProps {
  jobs: JobResult[];
  folders: FolderConfig[];
  onClear: () => Promise<void>;
}

export function Results({ jobs, folders, onClear }: ResultsProps) {
  const [selectedJob, setSelectedJob] = useState<JobResult | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const filteredJobs =
    filter === "all"
      ? jobs
      : jobs.filter((j) => {
          if (filter === "issues")
            return j.status === "failed" || j.status === "error";
          return j.status === filter;
        });

  const passCount = jobs.filter((j) => j.status === "passed").length;
  const failCount = jobs.filter((j) => j.status === "failed").length;
  const errorCount = jobs.filter((j) => j.status === "error").length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Results</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {jobs.length} total · {passCount} passed · {failCount} failed ·{" "}
            {errorCount} errors
          </p>
        </div>
        {jobs.length > 0 && (
          <button onClick={onClear} className="btn-secondary text-xs">
            <Trash2 className="h-3.5 w-3.5" /> Clear
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-4">
        {[
          { key: "all", label: "All" },
          { key: "passed", label: "Passed" },
          { key: "failed", label: "Failed" },
          { key: "error", label: "Errors" },
          { key: "issues", label: "Issues" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === tab.key
                ? "bg-brand-100 text-brand-700"
                : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex flex-1 gap-4 min-h-0">
        <div className="flex-1 card overflow-hidden">
          <ResultsTable
            jobs={filteredJobs}
            folders={folders}
            selectedJob={selectedJob}
            onSelect={setSelectedJob}
          />
        </div>

        {selectedJob && (
          <div className="w-80 shrink-0 overflow-y-auto">
            <ResultDetail
              job={selectedJob}
              onClose={() => setSelectedJob(null)}
              onJobUpdate={setSelectedJob}
            />
          </div>
        )}
      </div>
    </div>
  );
}
