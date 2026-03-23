"use client";

import { useCallback, useEffect, useState } from "react";

interface AdminJob {
  job_id: string;
  tenant_id: string;
  tenant_name?: string;
  status: string;
  profile_id: string;
  file_name: string;
  created_at: string;
  summary?: {
    total_findings: number;
    error_count: number;
    passed: boolean;
  };
}

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 50;

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `/api/grounded/admin/jobs?page=${page}&page_size=${pageSize}`,
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

  const totalPages = Math.ceil(total / pageSize);

  return (
    <main className="p-8 max-w-6xl">
      <h1 className="font-display text-2xl font-bold">All Jobs</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {total} total jobs across all tenants
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <p className="mt-4 text-muted-foreground">Loading...</p>
      ) : (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 font-medium">File</th>
                  <th className="pb-2 font-medium">Tenant</th>
                  <th className="pb-2 font-medium">Profile</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Result</th>
                  <th className="pb-2 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id} className="border-b">
                    <td className="py-2 font-medium">{job.file_name}</td>
                    <td className="py-2 text-xs">
                      {job.tenant_name ?? job.tenant_id.slice(0, 8)}
                    </td>
                    <td className="py-2">
                      <code className="text-xs">{job.profile_id}</code>
                    </td>
                    <td className="py-2">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                          job.status === "complete"
                            ? "bg-green-100 text-green-700"
                            : job.status === "failed"
                              ? "bg-red-100 text-red-700"
                              : "bg-yellow-100 text-yellow-700"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="py-2 text-xs">
                      {job.summary
                        ? job.summary.passed
                          ? "Passed"
                          : `${job.summary.error_count} errors`
                        : "--"}
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {new Date(job.created_at).toLocaleDateString()}
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
