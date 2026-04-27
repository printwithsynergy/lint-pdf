"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { SkeletonDashboard } from "@/components/skeleton";

interface Finding {
  id?: string;
  inspection_id: string;
  severity: string;
  message: string;
  page_num: number | null;
  details: Record<string, unknown> | null;
  source: string;
  category: string | null;
  ai_explanation?: string | null;
  ai_explanation_model?: string | null;
  ai_explanation_at?: string | null;
  effective_decision?: {
    decision_type: string;
    decided_at: string | null;
    decided_by_user_id: string;
  } | null;
}

interface EpmVerdict {
  tier: string;
  rejection_drivers: string[];
  advisories: string[];
  recommends_indichrome: boolean;
  legacy_codes_fired: string[];
  epm_findings_count: number;
}

interface ReportData {
  job_id: string;
  status: string;
  profile_id: string;
  file_name: string;
  file_size: number;
  page_count: number | null;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  color_quality_score: number | null;
  color_quality_grade: string | null;
  summary: {
    total_findings: number;
    error_count: number;
    warning_count: number;
    advisory_count: number;
    passed: boolean;
  } | null;
  findings: Finding[] | null;
  epm_verdict?: EpmVerdict | null;
  decisions_count?: number | null;
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    error: "bg-destructive/10 text-destructive",
    warning: "bg-warning/10 text-warning",
    advisory: "bg-info/10 text-info",
  };
  return (
    <span
      // severity is a finding severity string from a typed Record lookup with fallback.
      // eslint-disable-next-line security/detect-object-injection
      className={`rounded px-1.5 py-0.5 text-xs font-medium ${colors[severity] ?? "bg-muted text-muted-foreground"}`}
    >
      {severity}
    </span>
  );
}

function EpmVerdictCard({ verdict }: { verdict: EpmVerdict }) {
  const tierColors: Record<string, string> = {
    pass: "border-l-success bg-success/5",
    pass_with_advisory: "border-l-info bg-info/5",
    marginal: "border-l-warning bg-warning/5",
    reject: "border-l-destructive bg-destructive/5",
  };
  const tierLabel = (verdict.tier || "")
    .replace(/_/g, " ")
    .toUpperCase();
  return (
    <div
      // eslint-disable-next-line security/detect-object-injection
      className={`mt-4 rounded-lg border-l-4 border bg-card p-4 ${tierColors[verdict.tier] ?? ""}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-full bg-foreground/10 px-3 py-0.5 text-xs font-bold tracking-wide">
          EPM: {tierLabel}
        </span>
        {verdict.recommends_indichrome && (
          <span className="text-xs font-semibold text-primary">
            Consider IndiChrome substrate
          </span>
        )}
        <span className="ml-auto text-xs text-muted-foreground">
          {verdict.epm_findings_count} EPM finding
          {verdict.epm_findings_count === 1 ? "" : "s"}
        </span>
      </div>
      {verdict.rejection_drivers.length > 0 && (
        <div className="mt-2 text-xs">
          <strong>Rejection drivers:</strong>{" "}
          {verdict.rejection_drivers.map((c) => (
            <code key={c} className="ml-1 rounded bg-muted px-1">
              {c}
            </code>
          ))}
        </div>
      )}
      {verdict.advisories.length > 0 && (
        <div className="mt-1 text-xs">
          <strong>Advisories:</strong>{" "}
          {verdict.advisories.map((c) => (
            <code key={c} className="ml-1 rounded bg-muted px-1">
              {c}
            </code>
          ))}
        </div>
      )}
    </div>
  );
}

function ExplainButton({
  jobId,
  finding,
  onExplained,
}: {
  jobId: string;
  finding: Finding;
  onExplained: (text: string, model: string | null) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const onClick = useCallback(async () => {
    if (!finding.id) {
      setErr("Finding has no id — re-run preflight.");
      return;
    }
    setLoading(true);
    setErr(null);
    try {
      const resp = await fetch(
        `/api/lintpdf/jobs/${jobId}/findings/${finding.id}/explain`,
        { method: "POST" },
      );
      if (resp.status === 402) {
        setErr("Cost cap exceeded — raise the cap in Account → Billing.");
        return;
      }
      if (!resp.ok) throw new Error(await resp.text());
      const data = await resp.json();
      onExplained(data.explanation ?? data.text ?? "", data.model ?? null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to explain");
    } finally {
      setLoading(false);
    }
  }, [jobId, finding, onExplained]);

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className="rounded-md border px-2 py-0.5 text-xs hover:bg-muted disabled:opacity-50"
      >
        {loading ? "Explaining…" : "✦ Explain"}
      </button>
      {err && <span className="ml-2 text-xs text-destructive">{err}</span>}
    </div>
  );
}

function FindingRow({
  jobId,
  finding,
}: {
  jobId: string;
  finding: Finding;
}) {
  const [explanation, setExplanation] = useState<string | null>(
    finding.ai_explanation ?? null,
  );
  const [model, setModel] = useState<string | null>(
    finding.ai_explanation_model ?? null,
  );
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={finding.severity} />
          <code className="text-xs text-muted-foreground">
            {finding.inspection_id}
          </code>
          {finding.page_num && (
            <span className="text-xs text-muted-foreground">
              Page {finding.page_num}
            </span>
          )}
          {finding.effective_decision && (
            <span className="rounded bg-info/10 px-1.5 py-0.5 text-xs font-medium text-info">
              {finding.effective_decision.decision_type}
            </span>
          )}
        </div>
        {finding.category && (
          <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
            {finding.category}
          </span>
        )}
      </div>
      <p className="mt-1 text-sm">{finding.message}</p>
      {finding.details && Object.keys(finding.details).length > 0 && (
        <div className="mt-1 text-xs text-muted-foreground">
          {Object.entries(finding.details)
            .map(([k, v]) => `${k}: ${String(v)}`)
            .join(" / ")}
        </div>
      )}
      {explanation ? (
        <div className="mt-2 rounded border-l-2 border-primary bg-primary/5 px-3 py-2 text-sm">
          <div className="text-xs font-semibold uppercase tracking-wide text-primary">
            AI Explain
            {model && (
              <span className="ml-1 text-muted-foreground">({model})</span>
            )}
          </div>
          <p className="mt-1">{explanation}</p>
        </div>
      ) : (
        <ExplainButton
          jobId={jobId}
          finding={finding}
          onExplained={(text, m) => {
            setExplanation(text);
            setModel(m);
          }}
        />
      )}
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchReport = useCallback(async () => {
    try {
      const resp = await fetch(`/api/lintpdf/reports/${jobId}`);
      if (!resp.ok) throw new Error("Failed to load report");
      const data = await resp.json();
      setReport(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  if (loading) {
    return <SkeletonDashboard type="detail" />;
  }

  if (error || !report) {
    return (
      <>
        <h1 className="font-display text-2xl font-bold">Preflight Report</h1>
        <p className="mt-4 text-destructive">{error || "Report not found"}</p>
        <Link
          href="/dashboard/reports"
          className="mt-2 inline-block text-sm text-primary hover:underline"
        >
          Back to reports
        </Link>
      </>
    );
  }

  const errors = report.findings?.filter((f) => f.severity === "error") ?? [];
  const warnings =
    report.findings?.filter((f) => f.severity === "warning") ?? [];
  const advisories =
    report.findings?.filter((f) => f.severity === "advisory") ?? [];

  return (
    <>
      <Link
        href="/dashboard/reports"
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        &larr; Back to reports
      </Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">
            {report.file_name}
          </h1>
          <div className="mt-1 flex flex-wrap gap-3 text-sm text-muted-foreground">
            <span>
              Profile: <code>{report.profile_id}</code>
            </span>
            <span>
              {(report.file_size / 1024 / 1024).toFixed(1)} MB
              {report.page_count ? ` / ${report.page_count} pages` : ""}
            </span>
            {report.duration_ms && <span>{report.duration_ms}ms</span>}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`rounded px-2 py-1 text-sm font-medium ${
              report.summary?.passed
                ? "bg-success/10 text-success"
                : "bg-destructive/10 text-destructive"
            }`}
          >
            {report.summary?.passed ? "PASS" : "FAIL"}
          </span>
          {report.decisions_count != null && report.decisions_count > 0 && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
              {report.decisions_count} decision
              {report.decisions_count === 1 ? "" : "s"}
            </span>
          )}
        </div>
      </div>

      {report.epm_verdict && <EpmVerdictCard verdict={report.epm_verdict} />}

      {report.summary && (
        <div className="mt-6 grid gap-3 sm:grid-cols-4">
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-destructive">
              {report.summary.error_count}
            </div>
            <div className="text-xs text-muted-foreground">Errors</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-warning">
              {report.summary.warning_count}
            </div>
            <div className="text-xs text-muted-foreground">Warnings</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-info">
              {report.summary.advisory_count}
            </div>
            <div className="text-xs text-muted-foreground">Advisories</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div
              className={`text-2xl font-bold ${report.summary.passed ? "text-success" : "text-destructive"}`}
            >
              {report.summary.passed ? "PASS" : "FAIL"}
            </div>
            <div className="text-xs text-muted-foreground">Result</div>
          </div>
        </div>
      )}

      {report.color_quality_score != null && (
        <div className="mt-4 rounded-lg border p-3">
          <span className="text-sm font-medium">Color Quality:</span>{" "}
          <span className="text-lg font-bold">
            {report.color_quality_score.toFixed(1)}
          </span>
          {report.color_quality_grade && (
            <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-sm">
              Grade {report.color_quality_grade}
            </span>
          )}
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <a
          href={`/api/lintpdf/reports/${report.job_id}/html`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
        >
          View HTML Report
        </a>
        <a
          href={`/api/lintpdf/reports/${report.job_id}/download`}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
        >
          Download PDF Report
        </a>
        <Link
          href={`/dashboard/preflight/${report.job_id}`}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
        >
          View Job Details
        </Link>
      </div>

      {report.findings && report.findings.length > 0 && (
        <div className="mt-6 space-y-6">
          {errors.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-destructive">
                Errors ({errors.length})
              </h2>
              <div className="mt-2 space-y-2">
                {errors.map((f, i) => (
                  <FindingRow key={i} jobId={jobId} finding={f} />
                ))}
              </div>
            </div>
          )}
          {warnings.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-warning">
                Warnings ({warnings.length})
              </h2>
              <div className="mt-2 space-y-2">
                {warnings.map((f, i) => (
                  <FindingRow key={i} jobId={jobId} finding={f} />
                ))}
              </div>
            </div>
          )}
          {advisories.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-info">
                Advisories ({advisories.length})
              </h2>
              <div className="mt-2 space-y-2">
                {advisories.map((f, i) => (
                  <FindingRow key={i} jobId={jobId} finding={f} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
