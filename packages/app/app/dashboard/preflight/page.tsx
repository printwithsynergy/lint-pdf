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
  const [uploadDataUrl, setUploadDataUrl] = useState<string | null>(null);

  // New: preflight source + imported report + branding override
  const [preflightSource, setPreflightSource] = useState<
    "engine" | "external" | "minimal"
  >("engine");
  const [externalFormat, setExternalFormat] = useState<string>("auto");
  const [externalReportDataUrl, setExternalReportDataUrl] = useState<
    string | null
  >(null);
  const [externalReportName] = useState<string>("external-report.xml");
  const [anonymize, setAnonymize] = useState<boolean>(false);
  const [tenantAnonymousDefault, setTenantAnonymousDefault] = useState<boolean>(
    false,
  );
  const [customMappings, setCustomMappings] = useState<
    { id: string; name: string; format: string }[]
  >([]);
  const [selectedMappingId, setSelectedMappingId] = useState<string>("");

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
      if (!resp.ok) {
        // Preserve the engine/proxy error detail so operators can tell
        // "missing API key" from "engine unreachable" without server logs.
        let detail = "";
        try {
          const errBody = (await resp.json()) as { error?: unknown };
          if (errBody && typeof errBody.error === "string") {
            detail = errBody.error;
          } else if (errBody?.error) {
            detail = JSON.stringify(errBody.error);
          }
        } catch {
          try {
            detail = await resp.text();
          } catch {
            detail = "";
          }
        }
        const suffix = detail ? `: ${detail}` : "";
        throw new Error(`Failed to load jobs (${resp.status})${suffix}`);
      }
      const data = await resp.json();
      setJobs(data.jobs ?? []);
      setTotal(data.total ?? 0);
      setError("");
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

  // Tenant-defined custom import mappings. Only shown when the user picks
  // "Import External Results" so the default flow stays uncluttered.
  useEffect(() => {
    fetch("/api/lintpdf/import-mappings")
      .then((r) => (r.ok ? r.json() : { mappings: [] }))
      .then((data) => {
        const active = (data.mappings ?? []).filter(
          (m: { is_active?: boolean }) => m.is_active !== false,
        );
        setCustomMappings(active);
      })
      .catch(() => {});
  }, []);

  // Load the tenant's default output branding so the Anonymize toggle
  // starts pre-checked when the tenant has opted into "broker" mode.
  useEffect(() => {
    fetch("/api/lintpdf/branding/defaults")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && typeof data === "object") {
          const anon = Boolean(
            data.unbranded_by_default ?? data.mode === "anonymous",
          );
          setTenantAnonymousDefault(anon);
          setAnonymize(anon);
        }
      })
      .catch(() => {});
  }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!uploadDataUrl) return;
    if (preflightSource === "external" && !externalReportDataUrl) {
      toast(
        "Upload the third-party preflight report or switch off Import External Results.",
        "error",
      );
      return;
    }

    setUploading(true);

    try {
      // Convert data URL back to a Blob for FormData upload
      const res = await fetch(uploadDataUrl);
      const blob = await res.blob();

      const formData = new FormData();
      formData.append("file", blob, "upload.pdf");
      formData.append("profile_id", selectedProfile);
      formData.append("preflight_source", preflightSource);

      if (preflightSource === "external" && externalReportDataUrl) {
        const extRes = await fetch(externalReportDataUrl);
        const extBlob = await extRes.blob();
        formData.append("external_report", extBlob, externalReportName);
        if (selectedMappingId) {
          // Custom mapping takes precedence over built-in parser selection;
          // the engine ignores ``external_format`` when mapping_id is set.
          formData.append("mapping_id", selectedMappingId);
        } else if (externalFormat && externalFormat !== "auto") {
          formData.append("external_format", externalFormat);
        }
      }

      if (anonymize) {
        formData.append("brand", "anonymous");
      }

      const resp = await fetch("/api/lintpdf/submit", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error ?? data.detail ?? "Upload failed");
      }
      toast(`Job submitted: ${data.job_id ?? "processing"}`, "success");
      setUploadDataUrl(null);
      setExternalReportDataUrl(null);
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
            {/* Source mode selector */}
            <div
              role="tablist"
              aria-label="Preflight source"
              className="mb-4 inline-flex rounded-md border border-border p-0.5"
            >
              {(
                [
                  ["engine", "Run Preflight"],
                  ["external", "Import External Results"],
                  ["minimal", "Viewer Only"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={preflightSource === value}
                  onClick={() => setPreflightSource(value)}
                  className={`px-3 py-1.5 text-sm rounded ${
                    preflightSource === value
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="flex flex-wrap items-end gap-3">
              <div className="flex-1 min-w-[200px]">
                <FormField label="PDF File" htmlFor="pdf-file">
                  <FileUpload
                    accept=".pdf"
                    acceptedTypes={["application/pdf"]}
                    maxSize={100 * 1024 * 1024}
                    value={uploadDataUrl}
                    onChange={setUploadDataUrl}
                    helpText="Drag and drop a PDF or click to browse"
                  />
                </FormField>
              </div>
              {preflightSource === "engine" && (
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
              )}
              <Button
                type="submit"
                loading={uploading}
                disabled={
                  !uploadDataUrl ||
                  (preflightSource === "external" && !externalReportDataUrl)
                }
              >
                {preflightSource === "engine"
                  ? "Run Preflight"
                  : preflightSource === "external"
                  ? "Import Results"
                  : "Open Viewer"}
              </Button>
            </div>

            {preflightSource === "external" && (
              <div className="mt-4 flex flex-wrap items-end gap-3 border-t pt-4">
                <div className="flex-1 min-w-[220px]">
                  <FormField
                    label="Preflight Report (PitStop / callas / Acrobat / LintPDF JSON)"
                    htmlFor="external-report"
                  >
                    <FileUpload
                      accept=".xml,.json,application/xml,application/json,text/xml"
                      maxSize={50 * 1024 * 1024}
                      value={externalReportDataUrl}
                      onChange={(v) => {
                        setExternalReportDataUrl(v);
                      }}
                      helpText="Upload the raw report your existing tool produced"
                    />
                  </FormField>
                </div>
                <div className="min-w-[200px]">
                  <FormField label="Format" htmlFor="external-format">
                    <Select
                      id="external-format"
                      value={externalFormat}
                      onChange={(e) => setExternalFormat(e.target.value)}
                      disabled={Boolean(selectedMappingId)}
                    >
                      <option value="auto">Auto-detect</option>
                      <option value="pitstop_xml">Enfocus PitStop (XML)</option>
                      <option value="callas_json">callas pdfToolbox (JSON)</option>
                      <option value="callas_xml">callas pdfToolbox (XML)</option>
                      <option value="acrobat_xml">Acrobat Preflight (XML)</option>
                      <option value="lintpdf_json">LintPDF native (JSON)</option>
                    </Select>
                  </FormField>
                </div>
                {customMappings.length > 0 && (
                  <div className="min-w-[220px]">
                    <FormField
                      label="Use custom mapping"
                      htmlFor="mapping-id"
                    >
                      <Select
                        id="mapping-id"
                        value={selectedMappingId}
                        onChange={(e) => setSelectedMappingId(e.target.value)}
                      >
                        <option value="">— None (use built-in parser)</option>
                        {customMappings.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name} ({m.format})
                          </option>
                        ))}
                      </Select>
                    </FormField>
                  </div>
                )}
              </div>
            )}
            {preflightSource === "external" && customMappings.length === 0 && (
              <div className="mt-2 text-xs text-muted-foreground">
                Need a proprietary format we don’t ship? Define one at{" "}
                <Link
                  href="/dashboard/account/import-mappings"
                  className="underline"
                >
                  Custom import mappings
                </Link>
                .
              </div>
            )}

            {preflightSource === "minimal" && (
              <Alert className="mt-4" variant="default">
                <AlertDescription>
                  Viewer-only mode skips analyzers entirely. You&apos;ll get the
                  interactive viewer with page navigation, download, and
                  metadata. Tools like separations or TAC can be loaded on
                  demand inside the viewer.
                </AlertDescription>
              </Alert>
            )}

            {/* Anonymize output */}
            <div className="mt-4 flex items-start gap-2 border-t pt-4">
              <input
                id="anonymize"
                type="checkbox"
                className="mt-1"
                checked={anonymize}
                onChange={(e) => setAnonymize(e.target.checked)}
              />
              <label htmlFor="anonymize" className="text-sm">
                <span className="font-medium">Anonymize output</span> — hide
                all branding and strip identifying PDF metadata.
                <span
                  className="block text-xs text-muted-foreground mt-0.5"
                  title="Strips your brand, LintPDF's brand, and identifying PDF metadata. Use when sending reports to distributors who shouldn't know you generated them."
                >
                  Use when sending reports to distributors who shouldn&apos;t
                  know you generated them.
                  {tenantAnonymousDefault && (
                    <span className="ml-1 text-muted-foreground">
                      (Tenant default)
                    </span>
                  )}
                </span>
              </label>
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
