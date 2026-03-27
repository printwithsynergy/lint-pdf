"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { SkeletonDashboard } from "@/components/skeleton";
import {
  Badge,
  EmptyState,
  useToast,
  ConfirmDialog,
  Button,
  FileUpload,
  Select,
  FormField,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Alert,
  AlertDescription,
} from "@thinkneverland/pixie-dust-ui";

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
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Preflight Jobs</h1>
        <p className="text-sm text-muted-foreground">{total} total jobs</p>
      </div>

      {/* Upload Form */}
      <Card>
        <CardHeader>
          <CardTitle>Submit PDF for Preflight</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpload}>
            <div className="flex flex-wrap items-end gap-3">
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
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
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
          <Card className="mt-6">
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>File</TableHead>
                    <TableHead>Profile</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Findings</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.job_id}>
                      <TableCell>
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
                      </TableCell>
                      <TableCell>
                        <code className="text-xs">{job.profile_id}</code>
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANT[job.status] ?? "outline"}>
                          {job.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {job.summary ? (
                          <div className="flex gap-2 text-xs">
                            {job.summary.error_count > 0 && (
                              <Badge variant="destructive">
                                {job.summary.error_count}E
                              </Badge>
                            )}
                            {job.summary.warning_count > 0 && (
                              <Badge variant="warning">
                                {job.summary.warning_count}W
                              </Badge>
                            )}
                            {job.summary.advisory_count > 0 && (
                              <Badge variant="secondary">
                                {job.summary.advisory_count}A
                              </Badge>
                            )}
                            {job.summary.passed && (
                              <Badge variant="success">Passed</Badge>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            --
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(job.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
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
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

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
    </>
  );
}
