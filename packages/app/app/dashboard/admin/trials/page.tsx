"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface TrialFileInfo {
  id: string;
  file_name: string;
  file_size: number;
  scan_clean: boolean;
  job_id: string | null;
  job_status: string | null;
}

interface TrialSubmission {
  id: string;
  name: string;
  email: string;
  company: string | null;
  phone: string | null;
  file_count: number;
  status: string;
  admin_notes: string | null;
  files?: TrialFileInfo[];
  created_at: string;
}

const STATUS_BADGES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  processing: "bg-blue-100 text-blue-700",
  complete: "bg-green-100 text-green-700",
  contacted: "bg-purple-100 text-purple-700",
};

export default function AdminTrialsPage() {
  const [submissions, setSubmissions] = useState<TrialSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const pageSize = 50;

  const fetchSubmissions = useCallback(async () => {
    setLoading(true);
    try {
      const qs = `page=${page}&page_size=${pageSize}${statusFilter ? `&status=${statusFilter}` : ""}`;
      const resp = await fetch(`/api/lintpdf/admin/trials?${qs}`);
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(
          (data as { error?: string }).error ??
            `Failed to load trials (${resp.status})`,
        );
      }
      const data = await resp.json();
      setSubmissions(data.submissions ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load trials");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchSubmissions();
  }, [fetchSubmissions]);

  const fetchDetail = useCallback(async (id: string) => {
    try {
      const resp = await fetch(`/api/lintpdf/admin/trials/${id}`);
      if (!resp.ok) return;
      const data = await resp.json();
      setSubmissions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, ...data } : s)),
      );
    } catch {
      // best effort
    }
  }, []);

  const toggleExpand = useCallback(
    (id: string) => {
      if (expanded === id) {
        setExpanded(null);
      } else {
        setExpanded(id);
        // Fetch detail with files
        const sub = submissions.find((s) => s.id === id);
        if (!sub?.files) {
          fetchDetail(id);
        }
      }
    },
    [expanded, submissions, fetchDetail],
  );

  const handleDownload = useCallback(
    async (submissionId: string, fileId: string) => {
      setActionLoading(`dl-${fileId}`);
      try {
        const resp = await fetch(
          `/api/lintpdf/admin/trials/${submissionId}/files/${fileId}/download`,
        );
        if (!resp.ok) throw new Error("Download failed");
        const data = await resp.json();
        window.open(data.url, "_blank");
      } catch {
        alert("Download failed");
      } finally {
        setActionLoading(null);
      }
    },
    [],
  );

  const handlePreflight = useCallback(
    async (submissionId: string, fileId: string) => {
      setActionLoading(`pf-${fileId}`);
      try {
        const resp = await fetch(
          `/api/lintpdf/admin/trials/${submissionId}/files/${fileId}/preflight`,
          { method: "POST" },
        );
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          throw new Error(
            (data as { detail?: string }).detail ?? "Preflight failed",
          );
        }
        // Refresh detail
        await fetchDetail(submissionId);
        await fetchSubmissions();
      } catch (e) {
        alert(e instanceof Error ? e.message : "Preflight failed");
      } finally {
        setActionLoading(null);
      }
    },
    [fetchDetail, fetchSubmissions],
  );

  const handleSendReport = useCallback(
    async (submissionId: string) => {
      setActionLoading(`report-${submissionId}`);
      try {
        const resp = await fetch(
          `/api/lintpdf/admin/trials/${submissionId}/send-report`,
          { method: "POST" },
        );
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          throw new Error(
            (data as { detail?: string }).detail ?? "Send report failed",
          );
        }
        await fetchSubmissions();
      } catch (e) {
        alert(e instanceof Error ? e.message : "Send report failed");
      } finally {
        setActionLoading(null);
      }
    },
    [fetchSubmissions],
  );

  const handleStatusUpdate = useCallback(
    async (submissionId: string, newStatus: string) => {
      try {
        const resp = await fetch(`/api/lintpdf/admin/trials/${submissionId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        });
        if (!resp.ok) throw new Error("Update failed");
        await fetchSubmissions();
      } catch {
        alert("Failed to update status");
      }
    },
    [fetchSubmissions],
  );

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <>
      <h1 className="font-display text-2xl font-bold">Trial Submissions</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {total} total submissions — review, preflight, and follow up with
        prospects
      </p>

      {/* Filters */}
      <div className="mt-4 flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Filter:</span>
        {["", "pending", "processing", "complete", "contacted"].map((s) => (
          <button
            key={s}
            onClick={() => {
              setStatusFilter(s);
              setPage(1);
            }}
            className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
              statusFilter === s
                ? "bg-foreground text-background"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : (
        <>
          <div className="mt-6 space-y-3">
            {submissions.map((sub) => (
              <div
                key={sub.id}
                className="rounded-lg border bg-card overflow-hidden"
              >
                {/* Summary row */}
                <button
                  type="button"
                  onClick={() => toggleExpand(sub.id)}
                  className="w-full flex items-center gap-4 p-4 text-left hover:bg-muted/30 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{sub.name}</span>
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_BADGES[sub.status] ?? "bg-gray-100 text-gray-700"}`}
                      >
                        {sub.status}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {sub.email}
                      {sub.company ? ` · ${sub.company}` : ""}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground shrink-0">
                    {sub.file_count} file{sub.file_count !== 1 ? "s" : ""}
                  </div>
                  <div className="text-xs text-muted-foreground shrink-0">
                    {new Date(sub.created_at).toLocaleDateString()}
                  </div>
                  <svg
                    className={`h-4 w-4 text-muted-foreground transition-transform ${expanded === sub.id ? "rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* Expanded detail */}
                {expanded === sub.id && (
                  <div className="border-t bg-muted/10 p-4">
                    {sub.phone && (
                      <p className="text-sm text-muted-foreground mb-3">
                        Phone: {sub.phone}
                      </p>
                    )}

                    {/* Files */}
                    {sub.files ? (
                      <div className="space-y-2">
                        {sub.files.map((f) => (
                          <div
                            key={f.id}
                            className="flex items-center gap-3 rounded border bg-background p-3"
                          >
                            <div className="flex-1 min-w-0">
                              <span className="text-sm font-medium truncate block">
                                {f.file_name}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {formatSize(f.file_size)}
                                {f.job_status
                                  ? ` · Preflight: ${f.job_status}`
                                  : ""}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              <button
                                onClick={() => handleDownload(sub.id, f.id)}
                                disabled={actionLoading === `dl-${f.id}`}
                                className="rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                              >
                                {actionLoading === `dl-${f.id}`
                                  ? "..."
                                  : "Download"}
                              </button>
                              <button
                                onClick={() => handlePreflight(sub.id, f.id)}
                                disabled={
                                  actionLoading === `pf-${f.id}` ||
                                  f.job_status === "pending" ||
                                  f.job_status === "processing"
                                }
                                className="rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
                              >
                                {actionLoading === `pf-${f.id}`
                                  ? "Queuing..."
                                  : f.job_status === "pending" ||
                                      f.job_status === "processing"
                                    ? "Running..."
                                    : f.job_status === "complete"
                                      ? "Re-run Preflight"
                                      : "Run Preflight"}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        Loading files...
                      </p>
                    )}

                    {/* Actions */}
                    <div className="mt-4 flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => handleSendReport(sub.id)}
                        disabled={
                          actionLoading === `report-${sub.id}` ||
                          !sub.files?.some((f) => f.job_status === "complete")
                        }
                        className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        {actionLoading === `report-${sub.id}`
                          ? "Sending..."
                          : "Send Report Email"}
                      </button>
                      {sub.status !== "contacted" && (
                        <button
                          onClick={() =>
                            handleStatusUpdate(sub.id, "contacted")
                          }
                          className="rounded border px-3 py-1.5 text-xs font-medium hover:bg-muted"
                        >
                          Mark Contacted
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {submissions.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">
                No trial submissions yet.
              </p>
            )}
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
    </>
  );
}
