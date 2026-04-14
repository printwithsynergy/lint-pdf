"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { Button } from "@thinkneverland/pixie-dust-ui";

interface AdminJob {
  id: string;
  tenant_id: string;
  tenant_name?: string | null;
  status: string;
  profile_id: string;
  file_name: string;
  created_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
  page_count?: number | null;
  error_message?: string | null;
}

interface AdminJobDetail extends AdminJob {
  file_size?: number;
  result_summary?: Record<string, unknown> | null;
  report_token?: string | null;
  report_format?: string | null;
  verdict?: string | null;
  verdict_by?: string | null;
  verdict_at?: string | null;
  verdict_notes?: string | null;
  preflight_source?: string | null;
  external_format?: string | null;
}

const REPORTS_BASE_URL =
  process.env.NEXT_PUBLIC_LINTPDF_REPORTS_BASE_URL ?? "https://reports.lintpdf.com";

type DetailTab = "jobs" | "logs" | "links";

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 50;

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminJobDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailTab, setDetailTab] = useState<DetailTab>("jobs");

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/jobs?page=${page}&page_size=${pageSize}`,
      );
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(
          (data as { error?: string }).error ??
            `Failed to load jobs (${resp.status})`,
        );
      }
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

  const openDetail = useCallback(async (jobId: string) => {
    setSelectedId(jobId);
    setDetail(null);
    setDetailError("");
    setDetailTab("jobs");
    setDetailLoading(true);
    try {
      const resp = await fetch(`/api/lintpdf/admin/jobs/${jobId}`);
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(
          (data as { error?: string }).error ??
            `Failed to load job detail (${resp.status})`,
        );
      }
      const data: AdminJobDetail = await resp.json();
      setDetail(data);
    } catch (e) {
      setDetailError(
        e instanceof Error ? e.message : "Failed to load job detail",
      );
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const closeDetail = useCallback(() => {
    setSelectedId(null);
    setDetail(null);
    setDetailError("");
  }, []);

  const totalPages = Math.ceil(total / pageSize);

  const reportUrl = useMemo(() => {
    if (!detail?.report_token) return null;
    return `${REPORTS_BASE_URL.replace(/\/$/, "")}/${detail.report_token}`;
  }, [detail?.report_token]);

  return (
    <>
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
        <SkeletonDashboard type="table" />
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
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className={`border-b hover:bg-muted/30 ${
                      selectedId === job.id ? "bg-muted/50" : ""
                    }`}
                  >
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
                    <td className="py-2 text-xs text-muted-foreground">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openDetail(job.id)}
                      >
                        View
                      </Button>
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

      {selectedId && (
        <div
          className="fixed inset-0 z-40 bg-black/30"
          role="presentation"
          onClick={closeDetail}
        />
      )}
      {selectedId && (
        <aside
          role="dialog"
          aria-modal="true"
          aria-label="Job detail"
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col border-l bg-background shadow-xl"
        >
          <header className="flex items-center justify-between border-b p-4">
            <div>
              <h2 className="font-display text-lg font-semibold">
                {detail?.file_name ?? "Loading job…"}
              </h2>
              <p className="text-xs text-muted-foreground">
                {detail?.tenant_name ?? detail?.tenant_id ?? selectedId}
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={closeDetail}>
              Close
            </Button>
          </header>

          <nav className="flex gap-1 border-b px-4">
            {(["jobs", "logs", "links"] as DetailTab[]).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setDetailTab(tab)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium capitalize ${
                  detailTab === tab
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>

          <div className="flex-1 overflow-auto p-4 text-sm">
            {detailLoading && (
              <p className="text-muted-foreground">Loading job detail…</p>
            )}
            {detailError && (
              <div className="rounded-md bg-destructive/10 p-3 text-destructive">
                {detailError}
              </div>
            )}
            {detail && detailTab === "jobs" && <JobsTab detail={detail} />}
            {detail && detailTab === "logs" && <LogsTab detail={detail} />}
            {detail && detailTab === "links" && (
              <LinksTab detail={detail} reportUrl={reportUrl} />
            )}
          </div>
        </aside>
      )}
    </>
  );
}

function JobsTab({ detail }: { detail: AdminJobDetail }) {
  const rows: Array<[string, string]> = [
    ["Job ID", detail.id],
    ["Status", detail.status],
    ["Tenant", detail.tenant_name ?? detail.tenant_id],
    ["Profile", detail.profile_id],
    ["File", detail.file_name],
    [
      "Size",
      detail.file_size != null ? `${(detail.file_size / 1024).toFixed(1)} KB` : "—",
    ],
    ["Pages", detail.page_count?.toString() ?? "—"],
    [
      "Duration",
      detail.duration_ms != null ? `${(detail.duration_ms / 1000).toFixed(2)}s` : "—",
    ],
    ["Created", new Date(detail.created_at).toLocaleString()],
    [
      "Completed",
      detail.completed_at ? new Date(detail.completed_at).toLocaleString() : "—",
    ],
    ["Source", detail.preflight_source ?? "engine"],
    ["External format", detail.external_format ?? "—"],
    ["Verdict", detail.verdict ?? "—"],
    ["Verdict by", detail.verdict_by ?? "—"],
    [
      "Verdict at",
      detail.verdict_at ? new Date(detail.verdict_at).toLocaleString() : "—",
    ],
  ];
  return (
    <div className="space-y-4">
      <table className="w-full text-xs">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k} className="border-b last:border-0">
              <th className="py-1.5 pr-2 text-left font-medium text-muted-foreground">
                {k}
              </th>
              <td className="py-1.5 font-mono break-all">{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {detail.verdict_notes && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
            Verdict notes
          </h3>
          <p className="whitespace-pre-wrap">{detail.verdict_notes}</p>
        </section>
      )}
      {detail.result_summary && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
            Summary
          </h3>
          <pre className="overflow-auto rounded-md bg-muted/50 p-3 text-xs">
            {JSON.stringify(detail.result_summary, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

function LogsTab({ detail }: { detail: AdminJobDetail }) {
  if (detail.status === "failed" && detail.error_message) {
    return (
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase text-destructive">
          Error message
        </h3>
        <pre className="overflow-auto whitespace-pre-wrap rounded-md bg-destructive/5 p-3 text-xs text-destructive">
          {detail.error_message}
        </pre>
      </div>
    );
  }
  if (detail.error_message) {
    return (
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
          Warnings
        </h3>
        <pre className="overflow-auto whitespace-pre-wrap rounded-md bg-muted/50 p-3 text-xs">
          {detail.error_message}
        </pre>
      </div>
    );
  }
  return (
    <p className="text-muted-foreground">
      No logs available. Engine captures <code>error_message</code> on
      failure; in-flight Celery logs are not streamed to the dashboard.
    </p>
  );
}

function LinksTab({
  detail,
  reportUrl,
}: {
  detail: AdminJobDetail;
  reportUrl: string | null;
}) {
  return (
    <div className="space-y-3">
      <LinkRow
        label="Report"
        href={reportUrl}
        placeholder="No report token yet (job not complete)"
      />
      <LinkRow
        label="Viewer"
        href={`/dashboard/preflight/${detail.id}`}
        placeholder=""
      />
      <LinkRow
        label="Engine API"
        href={`${(process.env.NEXT_PUBLIC_LINTPDF_API_URL ?? "https://api.lintpdf.com").replace(/\/$/, "")}/api/v1/jobs/${detail.id}`}
        placeholder=""
      />
    </div>
  );
}

function LinkRow({
  label,
  href,
  placeholder,
}: {
  label: string;
  href: string | null;
  placeholder: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border p-3">
      <div>
        <div className="text-xs font-semibold uppercase text-muted-foreground">
          {label}
        </div>
        {href ? (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="break-all text-primary hover:underline"
          >
            {href}
          </a>
        ) : (
          <div className="text-muted-foreground">{placeholder}</div>
        )}
      </div>
    </div>
  );
}
