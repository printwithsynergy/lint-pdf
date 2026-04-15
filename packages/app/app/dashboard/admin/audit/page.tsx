"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { Button } from "@thinkneverland/pixie-dust-ui";

// ---------- types ----------

interface AuditJobRow {
  id: string;
  tenant_id: string;
  tenant_name: string | null;
  file_name: string;
  status: string;
  profile_id: string;
  preflight_source: string | null;
  external_format: string | null;
  created_at: string;
  completed_at: string | null;
  page_count: number | null;
  duration_ms: number | null;
  verdict: string | null;
  has_imported_report: boolean;
  report_token_count: number;
  findings_count: number;
}

interface AuditGroup {
  key: string;
  label: string;
  count: number;
  jobs: AuditJobRow[];
}

interface AuditListResponse {
  groups: AuditGroup[];
  total: number;
  page: number;
  page_size: number;
  group_by: string;
}

interface PresignedBlob {
  presigned_url: string;
  expires_at: string;
  size_bytes: number | null;
}

interface ImportedReportDetail {
  id: string;
  format: string;
  parser_version: string;
  raw_size_bytes: number;
  source_metadata: Record<string, unknown> | null;
  parsed_at: string;
  raw_blob_presigned_url: string;
  expires_at: string;
  inline_text: string | null;
}

interface ReportTokenDetail {
  id: string;
  token: string;
  format: string;
  public_url: string;
  expires_at: string | null;
  created_at: string;
  accessed_count: number;
  last_accessed_at: string | null;
  brand_mode: string | null;
  brand_profile_id: string | null;
  allow_annotations: boolean;
}

interface ApprovalSummary {
  chain_id: string;
  template_id: string | null;
  status: string;
  current_step: number;
  steps: Array<{
    index: number;
    status: string;
    approver_email: string | null;
    decided_at: string | null;
    notes: string | null;
  }>;
  created_at: string;
  completed_at: string | null;
}

interface SubmissionContext {
  source: string;
  trial_submission_id: string | null;
  trial_submitter_email: string | null;
  endpoint_slug: string | null;
  request_metadata: Record<string, unknown> | null;
}

interface AuditJobDetail {
  id: string;
  tenant_id: string;
  tenant_name: string | null;
  status: string;
  profile_id: string;
  file_name: string;
  file_key: string;
  file_size: number;
  page_count: number | null;
  duration_ms: number | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  preflight_source: string | null;
  external_format: string | null;
  data_capabilities: Record<string, unknown> | null;
  brand_profile_id_override: string | null;
  unbranded_override: boolean;
  jdf_overrides: Record<string, unknown> | null;
  color_quality_score: number | null;
  verdict: string | null;
  verdict_by: string | null;
  verdict_at: string | null;
  verdict_notes: string | null;
  result_json: Record<string, unknown> | null;
  input_pdf: PresignedBlob | null;
  imported_reports: ImportedReportDetail[];
  report_tokens: ReportTokenDetail[];
  findings_count: number;
  annotations_count: number;
  submission_context: SubmissionContext;
  approvals: ApprovalSummary | null;
}

interface FindingRow {
  id: string;
  inspection_id: string;
  severity: string;
  message: string;
  page_num: number | null;
  category: string | null;
  source: string;
  object_id: string | null;
  object_type: string | null;
  bbox_x0: number | null;
  bbox_y0: number | null;
  bbox_x1: number | null;
  bbox_y1: number | null;
  details: Record<string, unknown> | null;
}

interface FindingsResponse {
  findings: FindingRow[];
  total: number;
  page: number;
  page_size: number;
}

type GroupBy = "tenant" | "source" | "format" | "date";
type DetailTab =
  | "overview"
  | "input"
  | "result"
  | "imported"
  | "findings"
  | "tokens"
  | "submission"
  | "raw";

const STATUS_BADGES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  processing: "bg-blue-100 text-blue-700",
  complete: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const STATUS_OPTIONS = ["", "pending", "processing", "complete", "failed"];
const SOURCE_OPTIONS = ["", "engine", "external", "minimal"];
const FORMAT_OPTIONS = [
  "",
  "pitstop_xml",
  "callas_xml",
  "callas_json",
  "acrobat_xml",
  "lintpdf_json",
];

function formatSize(bytes: number | null | undefined): string {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function CopyButton({
  text,
  label = "Copy",
}: {
  text: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);
  const onClick = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // best effort
    }
  }, [text]);
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded border px-2 py-1 text-xs hover:bg-muted"
    >
      {copied ? "Copied!" : label}
    </button>
  );
}

// ---------- page ----------

export default function AdminAuditPage() {
  const [data, setData] = useState<AuditListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [formatFilter, setFormatFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [q, setQ] = useState("");
  const [groupBy, setGroupBy] = useState<GroupBy>("tenant");

  // Drawer state
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AuditJobDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailTab, setDetailTab] = useState<DetailTab>("overview");

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams();
      qs.set("page", String(page));
      qs.set("page_size", String(pageSize));
      qs.set("group_by", groupBy);
      if (statusFilter) qs.set("status", statusFilter);
      if (sourceFilter) qs.set("preflight_source", sourceFilter);
      if (formatFilter) qs.set("external_format", formatFilter);
      if (dateFrom) qs.set("date_from", dateFrom);
      if (dateTo) qs.set("date_to", dateTo);
      if (q) qs.set("q", q);
      const resp = await fetch(`/api/lintpdf/admin/audit?${qs.toString()}`);
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(
          (body as { error?: string }).error ??
            `Failed to load audit (${resp.status})`,
        );
      }
      const body: AuditListResponse = await resp.json();
      setData(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit");
    } finally {
      setLoading(false);
    }
  }, [
    page,
    groupBy,
    statusFilter,
    sourceFilter,
    formatFilter,
    dateFrom,
    dateTo,
    q,
  ]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const openDetail = useCallback(async (jobId: string) => {
    setSelectedId(jobId);
    setDetail(null);
    setDetailError("");
    setDetailTab("overview");
    setDetailLoading(true);
    try {
      const resp = await fetch(`/api/lintpdf/admin/audit/${jobId}`);
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(
          (body as { error?: string }).error ??
            `Failed to load detail (${resp.status})`,
        );
      }
      const body: AuditJobDetail = await resp.json();
      setDetail(body);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : "Failed to load detail");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const closeDetail = useCallback(() => {
    setSelectedId(null);
    setDetail(null);
    setDetailError("");
  }, []);

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <>
      <h1 className="font-display text-2xl font-bold">Preflight Audit</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Full end-to-end visibility into every tenant&rsquo;s preflight inputs,
        outputs, and share links. Read-only.
      </p>

      {/* Filter bar */}
      <div className="mt-4 space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-muted-foreground">Status:</span>
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s || "all"}
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

        <div className="flex items-center gap-2 flex-wrap text-sm">
          <span className="text-muted-foreground">Source:</span>
          <select
            value={sourceFilter}
            onChange={(e) => {
              setSourceFilter(e.target.value);
              setPage(1);
            }}
            className="rounded border px-2 py-1 text-xs"
          >
            {SOURCE_OPTIONS.map((s) => (
              <option key={s || "all"} value={s}>
                {s || "All"}
              </option>
            ))}
          </select>

          <span className="text-muted-foreground ml-2">Format:</span>
          <select
            value={formatFilter}
            onChange={(e) => {
              setFormatFilter(e.target.value);
              setPage(1);
            }}
            className="rounded border px-2 py-1 text-xs"
          >
            {FORMAT_OPTIONS.map((s) => (
              <option key={s || "all"} value={s}>
                {s || "All"}
              </option>
            ))}
          </select>

          <span className="text-muted-foreground ml-2">From:</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="rounded border px-2 py-1 text-xs"
          />
          <span className="text-muted-foreground">To:</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="rounded border px-2 py-1 text-xs"
          />

          <input
            type="search"
            placeholder="Search file name…"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            className="ml-2 rounded border px-2 py-1 text-xs"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-muted-foreground">Group by:</span>
          {(["tenant", "source", "format", "date"] as GroupBy[]).map((g) => (
            <button
              key={g}
              onClick={() => {
                setGroupBy(g);
                setPage(1);
              }}
              className={`rounded px-2 py-1 text-xs font-medium capitalize transition-colors ${
                groupBy === g
                  ? "bg-foreground text-background"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {g}
            </button>
          ))}
          <span className="ml-auto text-xs text-muted-foreground">
            {total} job{total === 1 ? "" : "s"} match filters
          </span>
        </div>
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
          <div className="mt-6 space-y-4">
            {data?.groups.map((group) => (
              <GroupSection
                key={group.key}
                group={group}
                selectedId={selectedId}
                onOpen={openDetail}
              />
            ))}
            {(!data || data.groups.length === 0) && (
              <p className="text-center text-sm text-muted-foreground py-8">
                No jobs match the current filters.
              </p>
            )}
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
          aria-label="Audit detail"
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col border-l bg-background shadow-xl"
        >
          <header className="flex items-center justify-between border-b p-4">
            <div className="min-w-0">
              <h2 className="font-display text-lg font-semibold truncate">
                {detail?.file_name ?? "Loading…"}
              </h2>
              <p className="text-xs text-muted-foreground truncate">
                {detail?.tenant_name ?? detail?.tenant_id ?? selectedId}
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={closeDetail}>
              Close
            </Button>
          </header>

          <nav className="flex gap-1 border-b px-4 overflow-x-auto">
            {(
              [
                "overview",
                "input",
                "result",
                "imported",
                "findings",
                "tokens",
                "submission",
                "raw",
              ] as DetailTab[]
            ).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setDetailTab(tab)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium capitalize whitespace-nowrap ${
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
              <p className="text-muted-foreground">Loading detail…</p>
            )}
            {detailError && (
              <div className="rounded-md bg-destructive/10 p-3 text-destructive">
                {detailError}
              </div>
            )}
            {detail && detailTab === "overview" && (
              <OverviewTab detail={detail} />
            )}
            {detail && detailTab === "input" && <InputTab detail={detail} />}
            {detail && detailTab === "result" && <ResultTab detail={detail} />}
            {detail && detailTab === "imported" && (
              <ImportedTab detail={detail} />
            )}
            {detail && detailTab === "findings" && (
              <FindingsTab jobId={detail.id} />
            )}
            {detail && detailTab === "tokens" && <TokensTab detail={detail} />}
            {detail && detailTab === "submission" && (
              <SubmissionTab detail={detail} />
            )}
            {detail && detailTab === "raw" && <RawTab detail={detail} />}
          </div>
        </aside>
      )}
    </>
  );
}

// ---------- detail tabs ----------

function MetaRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <tr className="border-b last:border-0">
      <th className="py-1.5 pr-2 text-left font-medium text-muted-foreground whitespace-nowrap">
        {k}
      </th>
      <td className="py-1.5 font-mono break-all">{v}</td>
    </tr>
  );
}

function OverviewTab({ detail }: { detail: AuditJobDetail }) {
  return (
    <div className="space-y-4">
      <table className="w-full text-xs">
        <tbody>
          <MetaRow k="Job ID" v={detail.id} />
          <MetaRow k="Status" v={detail.status} />
          <MetaRow
            k="Tenant"
            v={`${detail.tenant_name ?? "—"} (${detail.tenant_id})`}
          />
          <MetaRow k="Profile" v={detail.profile_id} />
          <MetaRow k="File" v={detail.file_name} />
          <MetaRow k="File key" v={detail.file_key} />
          <MetaRow k="Size" v={formatSize(detail.file_size)} />
          <MetaRow k="Pages" v={detail.page_count ?? "—"} />
          <MetaRow
            k="Duration"
            v={
              detail.duration_ms != null
                ? `${(detail.duration_ms / 1000).toFixed(2)}s`
                : "—"
            }
          />
          <MetaRow k="Created" v={new Date(detail.created_at).toLocaleString()} />
          <MetaRow
            k="Completed"
            v={
              detail.completed_at
                ? new Date(detail.completed_at).toLocaleString()
                : "—"
            }
          />
          <MetaRow k="Source" v={detail.preflight_source ?? "—"} />
          <MetaRow k="External format" v={detail.external_format ?? "—"} />
          <MetaRow
            k="Brand profile override"
            v={detail.brand_profile_id_override ?? "—"}
          />
          <MetaRow
            k="Unbranded override"
            v={detail.unbranded_override ? "true" : "false"}
          />
          <MetaRow
            k="Color quality score"
            v={detail.color_quality_score ?? "—"}
          />
          <MetaRow k="Findings count" v={detail.findings_count} />
          <MetaRow k="Annotations count" v={detail.annotations_count} />
          <MetaRow k="Verdict" v={detail.verdict ?? "—"} />
          <MetaRow k="Verdict by" v={detail.verdict_by ?? "—"} />
          <MetaRow
            k="Verdict at"
            v={
              detail.verdict_at
                ? new Date(detail.verdict_at).toLocaleString()
                : "—"
            }
          />
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
      {detail.error_message && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-destructive">
            Error message
          </h3>
          <pre className="overflow-auto whitespace-pre-wrap rounded-md bg-destructive/5 p-3 text-xs text-destructive">
            {detail.error_message}
          </pre>
        </section>
      )}
      {detail.data_capabilities && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
            Data capabilities
          </h3>
          <pre className="overflow-auto rounded-md bg-muted/50 p-3 text-xs">
            {JSON.stringify(detail.data_capabilities, null, 2)}
          </pre>
        </section>
      )}
      {detail.jdf_overrides && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
            JDF overrides
          </h3>
          <pre className="overflow-auto rounded-md bg-muted/50 p-3 text-xs">
            {JSON.stringify(detail.jdf_overrides, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

function InputTab({ detail }: { detail: AuditJobDetail }) {
  if (!detail.input_pdf) {
    return (
      <p className="text-muted-foreground">
        Input PDF not available. The blob at <code>{detail.file_key}</code> may
        have been deleted or is unreachable.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <table className="w-full text-xs">
        <tbody>
          <MetaRow k="File name" v={detail.file_name} />
          <MetaRow k="File key" v={detail.file_key} />
          <MetaRow k="Size" v={formatSize(detail.file_size)} />
          <MetaRow
            k="URL expires"
            v={new Date(detail.input_pdf.expires_at).toLocaleTimeString()}
          />
        </tbody>
      </table>
      <div className="flex items-center gap-2">
        <a
          href={detail.input_pdf.presigned_url}
          target="_blank"
          rel="noreferrer"
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          Download PDF
        </a>
        <CopyButton text={detail.input_pdf.presigned_url} label="Copy URL" />
      </div>
    </div>
  );
}

function ResultTab({ detail }: { detail: AuditJobDetail }) {
  if (!detail.result_json) {
    return (
      <p className="text-muted-foreground">
        No result JSON recorded for this job.
      </p>
    );
  }
  const text = JSON.stringify(detail.result_json, null, 2);
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <CopyButton text={text} label="Copy JSON" />
        <span className="text-xs text-muted-foreground">
          {text.length.toLocaleString()} chars
        </span>
      </div>
      <pre className="overflow-auto rounded-md bg-muted/50 p-3 text-xs">
        {text}
      </pre>
    </div>
  );
}

function ImportedTab({ detail }: { detail: AuditJobDetail }) {
  if (detail.imported_reports.length === 0) {
    return (
      <p className="text-muted-foreground">
        No imported third-party reports for this job. (This job likely used
        engine-native preflight.)
      </p>
    );
  }
  return (
    <div className="space-y-4">
      {detail.imported_reports.map((ir) => (
        <ImportedReportCard key={ir.id} report={ir} />
      ))}
    </div>
  );
}

function ImportedReportCard({ report }: { report: ImportedReportDetail }) {
  const [current, setCurrent] = useState(report);
  const [refreshing, setRefreshing] = useState(false);
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/audit/imported-reports/${report.id}`,
      );
      if (resp.ok) {
        const body = await resp.json();
        setCurrent((c) => ({
          ...c,
          raw_blob_presigned_url: body.presigned_url,
          expires_at: body.expires_at,
        }));
      }
    } finally {
      setRefreshing(false);
    }
  }, [report.id]);
  return (
    <div className="rounded-md border p-3 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-medium">
          {current.format}
        </span>
        <span className="text-xs text-muted-foreground">
          parser v{current.parser_version} · {formatSize(current.raw_size_bytes)}
        </span>
        <span className="text-xs text-muted-foreground ml-auto">
          parsed {new Date(current.parsed_at).toLocaleString()}
        </span>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <a
          href={current.raw_blob_presigned_url}
          target="_blank"
          rel="noreferrer"
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
        >
          Download raw blob
        </a>
        {current.inline_text && (
          <CopyButton text={current.inline_text} label="Copy raw text" />
        )}
        <CopyButton
          text={current.raw_blob_presigned_url}
          label="Copy URL"
        />
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-50"
        >
          {refreshing ? "…" : "Refresh link"}
        </button>
      </div>
      {current.source_metadata && (
        <details>
          <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">
            Source metadata
          </summary>
          <pre className="mt-2 overflow-auto rounded-md bg-muted/50 p-3 text-xs">
            {JSON.stringify(current.source_metadata, null, 2)}
          </pre>
        </details>
      )}
      {current.inline_text && (
        <details>
          <summary className="cursor-pointer text-xs font-semibold text-muted-foreground">
            Inline text ({current.inline_text.length.toLocaleString()} chars)
          </summary>
          <pre className="mt-2 overflow-auto rounded-md bg-muted/50 p-3 text-xs whitespace-pre-wrap">
            {current.inline_text}
          </pre>
        </details>
      )}
    </div>
  );
}

function FindingsTab({ jobId }: { jobId: string }) {
  const [data, setData] = useState<FindingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 200;

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/audit/${jobId}/findings?page=${page}&page_size=${pageSize}`,
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(
          (body as { error?: string }).error ??
            `Failed to load findings (${resp.status})`,
        );
      }
      const body: FindingsResponse = await resp.json();
      setData(body);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load findings");
    } finally {
      setLoading(false);
    }
  }, [jobId, page]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <p className="text-muted-foreground">Loading findings…</p>;
  if (err)
    return (
      <div className="rounded-md bg-destructive/10 p-3 text-destructive">
        {err}
      </div>
    );
  if (!data || data.total === 0)
    return <p className="text-muted-foreground">No findings.</p>;
  const totalPages = Math.ceil(data.total / pageSize);
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        {data.total} finding{data.total === 1 ? "" : "s"} · page {page} of{" "}
        {totalPages}
      </p>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-1.5 pr-2">Page</th>
            <th className="py-1.5 pr-2">Severity</th>
            <th className="py-1.5 pr-2">Category</th>
            <th className="py-1.5 pr-2">Inspection</th>
            <th className="py-1.5">Message</th>
          </tr>
        </thead>
        <tbody>
          {data.findings.map((f) => (
            <FindingRowItem key={f.id} f={f} />
          ))}
        </tbody>
      </table>
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded border px-2 py-1 text-xs disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="rounded border px-2 py-1 text-xs disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function FindingRowItem({ f }: { f: FindingRow }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr className="border-b align-top">
        <td className="py-1.5 pr-2">{f.page_num ?? "—"}</td>
        <td className="py-1.5 pr-2">
          <span
            className={`rounded px-1.5 py-0.5 font-medium ${
              f.severity === "error"
                ? "bg-red-100 text-red-700"
                : f.severity === "warning"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-muted text-muted-foreground"
            }`}
          >
            {f.severity}
          </span>
        </td>
        <td className="py-1.5 pr-2">{f.category ?? "—"}</td>
        <td className="py-1.5 pr-2 font-mono">{f.inspection_id}</td>
        <td className="py-1.5">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="text-left hover:underline"
          >
            {f.message}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="border-b bg-muted/20">
          <td colSpan={5} className="py-2 px-2">
            <pre className="overflow-auto rounded bg-muted/50 p-2 text-xs">
              {JSON.stringify(
                {
                  id: f.id,
                  source: f.source,
                  object_id: f.object_id,
                  object_type: f.object_type,
                  bbox: [f.bbox_x0, f.bbox_y0, f.bbox_x1, f.bbox_y1],
                  details: f.details,
                },
                null,
                2,
              )}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}

function TokensTab({ detail }: { detail: AuditJobDetail }) {
  if (detail.report_tokens.length === 0) {
    return (
      <p className="text-muted-foreground">
        No report tokens issued for this job yet.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {detail.report_tokens.map((tok) => (
        <div key={tok.id} className="rounded-md border p-3 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-medium uppercase">
              {tok.format}
            </span>
            <span className="text-xs text-muted-foreground">
              {tok.accessed_count} view{tok.accessed_count === 1 ? "" : "s"}
            </span>
            {tok.last_accessed_at && (
              <span className="text-xs text-muted-foreground">
                · last {new Date(tok.last_accessed_at).toLocaleString()}
              </span>
            )}
            {tok.expires_at && (
              <span className="text-xs text-muted-foreground">
                · expires {new Date(tok.expires_at).toLocaleDateString()}
              </span>
            )}
          </div>
          <div className="break-all text-xs text-primary">{tok.public_url}</div>
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={tok.public_url}
              target="_blank"
              rel="noreferrer"
              className="rounded border px-2 py-1 text-xs hover:bg-muted"
            >
              Open
            </a>
            <CopyButton text={tok.public_url} label="Copy URL" />
            {tok.format === "pdf" && (
              <a
                href={tok.public_url}
                download
                className="rounded border px-2 py-1 text-xs hover:bg-muted"
              >
                Download
              </a>
            )}
            <span className="ml-auto text-xs text-muted-foreground">
              brand: {tok.brand_mode ?? "—"}
              {tok.allow_annotations ? " · annotations on" : ""}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function SubmissionTab({ detail }: { detail: AuditJobDetail }) {
  const s = detail.submission_context;
  return (
    <div className="space-y-4">
      <table className="w-full text-xs">
        <tbody>
          <MetaRow k="Source" v={s.source} />
          <MetaRow
            k="Trial submission"
            v={s.trial_submission_id ?? "—"}
          />
          <MetaRow
            k="Trial submitter"
            v={s.trial_submitter_email ?? "—"}
          />
          <MetaRow k="Endpoint slug" v={s.endpoint_slug ?? "—"} />
        </tbody>
      </table>
      {s.request_metadata && (
        <section>
          <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
            Request metadata
          </h3>
          <pre className="overflow-auto rounded-md bg-muted/50 p-3 text-xs">
            {JSON.stringify(s.request_metadata, null, 2)}
          </pre>
        </section>
      )}
      {detail.approvals && (
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
            Approval chain ({detail.approvals.status})
          </h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-1.5 pr-2">#</th>
                <th className="py-1.5 pr-2">Status</th>
                <th className="py-1.5 pr-2">Approver</th>
                <th className="py-1.5 pr-2">Decided</th>
                <th className="py-1.5">Notes</th>
              </tr>
            </thead>
            <tbody>
              {detail.approvals.steps.map((step) => (
                <tr key={step.index} className="border-b">
                  <td className="py-1.5 pr-2">{step.index + 1}</td>
                  <td className="py-1.5 pr-2">{step.status}</td>
                  <td className="py-1.5 pr-2">{step.approver_email ?? "—"}</td>
                  <td className="py-1.5 pr-2">
                    {step.decided_at
                      ? new Date(step.decided_at).toLocaleString()
                      : "—"}
                  </td>
                  <td className="py-1.5">{step.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

function RawTab({ detail }: { detail: AuditJobDetail }) {
  const text = JSON.stringify(detail, null, 2);
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <CopyButton text={text} label="Copy all" />
        <span className="text-xs text-muted-foreground">
          {text.length.toLocaleString()} chars · the ultimate escape hatch
        </span>
      </div>
      <pre className="overflow-auto rounded-md bg-muted/50 p-3 text-xs">
        {text}
      </pre>
    </div>
  );
}

// ---------- group accordion ----------

function GroupSection({
  group,
  selectedId,
  onOpen,
}: {
  group: AuditGroup;
  selectedId: string | null;
  onOpen: (jobId: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-muted/30 transition-colors border-b"
      >
        <span className="font-medium truncate">{group.label}</span>
        <span className="text-xs text-muted-foreground">
          {group.count} job{group.count === 1 ? "" : "s"}
        </span>
        <svg
          className={`ml-auto h-4 w-4 text-muted-foreground transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
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
      {expanded && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="px-3 py-2 font-medium">File</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Source</th>
              <th className="px-3 py-2 font-medium">Format</th>
              <th className="px-3 py-2 font-medium">Findings</th>
              <th className="px-3 py-2 font-medium">Tokens</th>
              <th className="px-3 py-2 font-medium">Created</th>
              <th className="px-3 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {group.jobs.map((job) => (
              <tr
                key={job.id}
                className={`border-b hover:bg-muted/30 ${
                  selectedId === job.id ? "bg-muted/50" : ""
                }`}
              >
                <td className="px-3 py-2 font-medium truncate max-w-xs">
                  {job.file_name}
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                      STATUS_BADGES[job.status] ?? "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {job.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs">
                  {job.preflight_source ?? "—"}
                </td>
                <td className="px-3 py-2 text-xs">
                  {job.external_format ?? "—"}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {job.findings_count}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {job.report_token_count}
                  {job.has_imported_report ? " · imp" : ""}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {new Date(job.created_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-2 text-right">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onOpen(job.id)}
                  >
                    View
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

