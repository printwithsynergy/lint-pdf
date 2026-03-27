"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { SkeletonDashboard } from "@/components/skeleton";

interface Finding {
  inspection_id: string;
  severity: string;
  message: string;
  page_num: number | null;
  details: Record<string, unknown> | null;
  source: string;
  category: string | null;
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
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    error: "bg-red-100 text-red-700",
    warning: "bg-yellow-100 text-yellow-700",
    advisory: "bg-blue-100 text-blue-700",
  };
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-xs font-medium ${colors[severity] ?? "bg-gray-100 text-gray-700"}`}
    >
      {severity}
    </span>
  );
}

function FindingRow({ finding }: { finding: Finding }) {
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
        <span
          className={`rounded px-2 py-1 text-sm font-medium ${
            report.summary?.passed
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {report.summary?.passed ? "PASS" : "FAIL"}
        </span>
      </div>

      {report.summary && (
        <div className="mt-6 grid gap-3 sm:grid-cols-4">
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-red-600">
              {report.summary.error_count}
            </div>
            <div className="text-xs text-muted-foreground">Errors</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {report.summary.warning_count}
            </div>
            <div className="text-xs text-muted-foreground">Warnings</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-blue-600">
              {report.summary.advisory_count}
            </div>
            <div className="text-xs text-muted-foreground">Advisories</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div
              className={`text-2xl font-bold ${report.summary.passed ? "text-green-600" : "text-red-600"}`}
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
              <h2 className="text-lg font-semibold text-red-600">
                Errors ({errors.length})
              </h2>
              <div className="mt-2 space-y-2">
                {errors.map((f, i) => (
                  <FindingRow key={i} finding={f} />
                ))}
              </div>
            </div>
          )}
          {warnings.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-yellow-600">
                Warnings ({warnings.length})
              </h2>
              <div className="mt-2 space-y-2">
                {warnings.map((f, i) => (
                  <FindingRow key={i} finding={f} />
                ))}
              </div>
            </div>
          )}
          {advisories.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-blue-600">
                Advisories ({advisories.length})
              </h2>
              <div className="mt-2 space-y-2">
                {advisories.map((f, i) => (
                  <FindingRow key={i} finding={f} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
