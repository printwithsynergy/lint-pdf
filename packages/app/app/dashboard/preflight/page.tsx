"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { SkeletonDashboard } from "@/components/skeleton";

interface Profile {
  profile_id: string;
  display_name: string;
}

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

  // Upload state
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState("lintpdf-default");
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    fetch("/api/grounded/profiles")
      .then((r) => (r.ok ? r.json() : { profiles: [] }))
      .then((data) => setProfiles(data.profiles ?? []))
      .catch(() => {});
  }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");
    setUploadSuccess("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("profile_id", selectedProfile);

    try {
      const resp = await fetch("/api/grounded/submit", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error ?? data.detail ?? "Upload failed");
      }
      setUploadSuccess(`Job submitted: ${data.job_id ?? "processing"}`);
      if (fileInputRef.current) fileInputRef.current.value = "";
      // Refresh job list after a short delay
      setTimeout(() => fetchJobs(), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

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

      {/* Upload Form */}
      <form
        onSubmit={handleUpload}
        className="mt-6 rounded-lg border bg-card p-4"
      >
        <h2 className="text-sm font-semibold">Submit PDF for Preflight</h2>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label
              htmlFor="pdf-file"
              className="block text-xs font-medium text-muted-foreground mb-1"
            >
              PDF File
            </label>
            <input
              id="pdf-file"
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              required
              className="block w-full text-sm file:mr-3 file:rounded file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-primary hover:file:bg-primary/20"
            />
          </div>
          <div className="min-w-[180px]">
            <label
              htmlFor="profile"
              className="block text-xs font-medium text-muted-foreground mb-1"
            >
              Profile
            </label>
            <select
              id="profile"
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              className="block w-full rounded border bg-background px-2 py-1.5 text-sm"
            >
              <option value="lintpdf-default">Default</option>
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.display_name}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={uploading}
            className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {uploading ? "Uploading..." : "Run Preflight"}
          </button>
        </div>
        {uploadSuccess && (
          <p className="mt-2 text-sm text-green-600">{uploadSuccess}</p>
        )}
      </form>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : jobs.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          No preflight jobs yet. Upload a PDF above to run your first preflight.
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
