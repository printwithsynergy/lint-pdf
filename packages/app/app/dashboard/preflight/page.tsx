"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { SkeletonDashboard } from "@/components/skeleton";

interface Job {
  job_id: string;
  status: string;
  profile_id: string;
  file_name: string;
  file_size: number;
  page_count: number | null;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  summary: {
    total_findings: number;
    error_count: number;
    warning_count: number;
    advisory_count: number;
    passed: boolean;
  } | null;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    processing: "bg-blue-100 text-blue-700",
    complete: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}
    >
      {status}
    </span>
  );
}

export default function PreflightPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const pageSize = 20;

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `/api/grounded/jobs?page=${page}&page_size=${pageSize}`,
      );
      if (!resp.ok) throw new Error("Failed to load jobs");
      const data = await resp.json();
      setJobs(data.jobs ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  async function handleDelete(jobId: string) {
    if (!confirm("Delete this job?")) return;
    try {
      await fetch(`/api/grounded/jobs/${jobId}`, { method: "DELETE" });
      await fetchJobs();
    } catch {
      setError("Failed to delete job");
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <main className="p-8 max-w-5xl">
      <h1 className="font-display text-2xl font-bold">Preflight Jobs</h1>
      <p className="mt-1 text-sm text-muted-foreground">{total} total jobs</p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : jobs.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          No preflight jobs yet. Submit a PDF via the API to get started.
        </div>
      ) : (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 font-medium">File</th>
                  <th className="pb-2 font-medium">Profile</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Findings</th>
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id} className="border-b">
                    <td className="py-2">
                      <Link
                        href={`/dashboard/preflight/${job.job_id}`}
                        className="font-medium hover:underline"
                      >
                        {job.file_name}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {(job.file_size / 1024 / 1024).toFixed(1)} MB
                        {job.page_count ? ` / ${job.page_count} pages` : ""}
                      </div>
                    </td>
                    <td className="py-2">
                      <code className="text-xs">{job.profile_id}</code>
                    </td>
                    <td className="py-2">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="py-2">
                      {job.summary ? (
                        <div className="flex gap-2 text-xs">
                          {job.summary.error_count > 0 && (
                            <span className="text-red-600">
                              {job.summary.error_count}E
                            </span>
                          )}
                          {job.summary.warning_count > 0 && (
                            <span className="text-yellow-600">
                              {job.summary.warning_count}W
                            </span>
                          )}
                          {job.summary.advisory_count > 0 && (
                            <span className="text-blue-600">
                              {job.summary.advisory_count}A
                            </span>
                          )}
                          {job.summary.passed && (
                            <span className="text-green-600">Passed</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          --
                        </span>
                      )}
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2">
                      <div className="flex gap-1">
                        <Link
                          href={`/dashboard/preflight/${job.job_id}`}
                          className="rounded border px-2 py-1 text-xs hover:bg-muted"
                        >
                          View
                        </Link>
                        <button
                          onClick={() => handleDelete(job.job_id)}
                          className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded border px-3 py-1 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded border px-3 py-1 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
