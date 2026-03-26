"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { SkeletonDashboard } from "@/components/skeleton";
import { Badge } from "@thinkneverland/pixie-dust-ui";
import { EmptyState } from "@thinkneverland/pixie-dust-ui";
import { useToast } from "@thinkneverland/pixie-dust-ui";
import { ConfirmDialog } from "@thinkneverland/pixie-dust-ui";
import { Button, FileUpload, Select, FormField } from "@thinkneverland/pixie-dust-ui";

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

const STATUS_VARIANT: Record<string, "warning" | "default" | "success" | "destructive"> = {
  pending: "warning",
  processing: "default",
  complete: "success",
  failed: "destructive",
};

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
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  // Confirm dialog state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);

  const { toast } = useToast();

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `/api/lintpdf/jobs?page=${page}&page_size=${pageSize}`,
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
    fetch("/api/lintpdf/profiles")
      .then((r) => (r.ok ? r.json() : { profiles: [] }))
      .then((data) => setProfiles(data.profiles ?? []))
      .catch(() => {});
  }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!uploadFile) return;

    setUploading(true);

    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("profile_id", selectedProfile);

    try {
      const resp = await fetch("/api/lintpdf/submit", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error ?? data.detail ?? "Upload failed");
      }
      toast(`Job submitted: ${data.job_id ?? "processing"}`, "success");
      setUploadFile(null);
      // Refresh job list after a short delay
      setTimeout(() => fetchJobs(), 1500);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Upload failed", "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(jobId: string) {
    try {
      await fetch(`/api/lintpdf/jobs/${jobId}`, { method: "DELETE" });
      await fetchJobs();
    } catch {
      toast("Failed to delete job", "error");
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
            <FormField label="PDF File" htmlFor="pdf-file">
              <FileUpload
                accept=".pdf"
                acceptedTypes={["application/pdf"]}
                maxSize={100 * 1024 * 1024}
                value={uploadFile}
                onChange={setUploadFile}
                helpText="Drag and drop a PDF or click to browse"
              />
            </FormField>
          </div>
          <div className="min-w-[180px]">
            <FormField label="Profile" htmlFor="profile">
              <Select
                id="profile"
                value={selectedProfile}
                onChange={(e) => setSelectedProfile(e.target.value)}
              >
                <option value="lintpdf-default">Default</option>
                {profiles.map((p) => (
                  <option key={p.profile_id} value={p.profile_id}>
                    {p.display_name}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <Button
            type="submit"
            loading={uploading}
            disabled={!uploadFile}
          >
            Run Preflight
          </Button>
        </div>
      </form>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : jobs.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            icon="FileText"
            title="No preflight jobs yet"
            description="Upload a PDF above to run your first preflight."
          />
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
                      <Badge variant={STATUS_VARIANT[job.status] ?? "outline"}>
                        {job.status}
                      </Badge>
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
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => window.location.href = `/dashboard/preflight/${job.job_id}`}
                        >
                          View
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setConfirmTarget(job.job_id);
                            setConfirmOpen(true);
                          }}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => {
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        onConfirm={async () => {
          if (confirmTarget) await handleDelete(confirmTarget);
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        title="Delete job?"
        description="This action cannot be undone. The job and its results will be permanently removed."
        variant="destructive"
        confirmLabel="Delete"
      />
    </main>
  );
}
