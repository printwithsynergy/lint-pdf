"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

interface Job {
  job_id: string;
  status: string;
  profile_id: string;
  file_name: string;
  created_at: string;
  summary: {
    total_findings: number;
    error_count: number;
    warning_count: number;
    passed: boolean;
  } | null;
}

export default function ReportsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchJobs = useCallback(async () => {
    try {
      const resp = await fetch("/api/grounded/jobs?page=1&page_size=50");
      if (!resp.ok) throw new Error("Failed to load jobs");
      const data = await resp.json();
      // Only show completed jobs that have reports
      setJobs((data.jobs ?? []).filter((j: Job) => j.status === "complete"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  if (loading) {
    return (
      <main className="p-8">
        <h1 className="font-display text-2xl font-bold">Reports</h1>
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </main>
    );
  }

  return (
    <main className="p-8 max-w-4xl">
      <h1 className="font-display text-2xl font-bold">Reports</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        View and download preflight reports for completed jobs.
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="mt-6 space-y-2">
        {jobs.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
            No completed jobs with reports yet.
          </div>
        ) : (
          jobs.map((job) => (
            <div
              key={job.job_id}
              className="flex items-center justify-between rounded-lg border p-3"
            >
              <div>
                <Link
                  href={`/dashboard/preflight/${job.job_id}`}
                  className="font-medium hover:underline"
                >
                  {job.file_name}
                </Link>
                <div className="mt-0.5 flex gap-2 text-xs text-muted-foreground">
                  <span>{job.profile_id}</span>
                  <span>{new Date(job.created_at).toLocaleDateString()}</span>
                  {job.summary && (
                    <span
                      className={
                        job.summary.passed ? "text-green-600" : "text-red-600"
                      }
                    >
                      {job.summary.passed
                        ? "Passed"
                        : `${job.summary.error_count} errors`}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-1">
                <a
                  href={`/api/grounded/reports/${job.job_id}/html`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded border px-2 py-1 text-xs hover:bg-muted"
                >
                  View HTML
                </a>
                <a
                  href={`/api/grounded/reports/${job.job_id}/download`}
                  className="rounded border px-2 py-1 text-xs hover:bg-muted"
                >
                  Download PDF
                </a>
              </div>
            </div>
          ))
        )}
      </div>
    </main>
  );
}
