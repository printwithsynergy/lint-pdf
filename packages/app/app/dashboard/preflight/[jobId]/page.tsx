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

interface JobDetail {
  job_id: string;
  status: string;
  profile_id: string;
  file_name: string;
  file_size: number;
  page_count: number | null;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  color_quality_score: number | null;
  color_quality_grade: string | null;
  summary: {
    total_findings: number;
    error_count: number;
    warning_count: number;
    advisory_count: number;
    passed: boolean;
    page_count: number;
    file_size_bytes: number;
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

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchJob = useCallback(async () => {
    try {
      const resp = await fetch(`/api/lintpdf/jobs/${jobId}`);
      if (!resp.ok) throw new Error("Failed to load job");
      const data = await resp.json();
      setJob(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load job");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  if (loading) {
    return <SkeletonDashboard type="detail" />;
  }

  if (error || !job) {
    return (
      <main className="p-8">
        <h1 className="font-display text-2xl font-bold">Job Details</h1>
        <p className="mt-4 text-destructive">{error || "Job not found"}</p>
        <Link
          href="/dashboard/preflight"
          className="mt-2 inline-block text-sm text-primary hover:underline"
        >
          Back to jobs
        </Link>
      </main>
    );
  }

  const errors = job.findings?.filter((f) => f.severity === "error") ?? [];
  const warnings = job.findings?.filter((f) => f.severity === "warning") ?? [];
  const advisories =
    job.findings?.filter((f) => f.severity === "advisory") ?? [];

  return (
    <main className="p-8 max-w-5xl">
      <Link
        href="/dashboard/preflight"
        className="text-sm text-muted-foreground hover:text-foreground"
      >
        &larr; Back to jobs
      </Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">{job.file_name}</h1>
          <div className="mt-1 flex flex-wrap gap-3 text-sm text-muted-foreground">
            <span>
              Profile: <code>{job.profile_id}</code>
            </span>
            <span>
              {(job.file_size / 1024 / 1024).toFixed(1)} MB
              {job.page_count ? ` / ${job.page_count} pages` : ""}
            </span>
            {job.duration_ms && <span>{job.duration_ms}ms</span>}
          </div>
        </div>
        <span
          className={`rounded px-2 py-1 text-sm font-medium ${
            job.status === "complete"
              ? "bg-green-100 text-green-700"
              : job.status === "failed"
                ? "bg-red-100 text-red-700"
                : "bg-yellow-100 text-yellow-700"
          }`}
        >
          {job.status}
        </span>
      </div>

      {job.summary && (
        <div className="mt-6 grid gap-3 sm:grid-cols-4">
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-red-600">
              {job.summary.error_count}
            </div>
            <div className="text-xs text-muted-foreground">Errors</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {job.summary.warning_count}
            </div>
            <div className="text-xs text-muted-foreground">Warnings</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-blue-600">
              {job.summary.advisory_count}
            </div>
            <div className="text-xs text-muted-foreground">Advisories</div>
          </div>
          <div className="rounded-lg border p-3 text-center">
            <div
              className={`text-2xl font-bold ${job.summary.passed ? "text-green-600" : "text-red-600"}`}
            >
              {job.summary.passed ? "PASS" : "FAIL"}
            </div>
            <div className="text-xs text-muted-foreground">Result</div>
          </div>
        </div>
      )}

      {job.color_quality_score != null && (
        <div className="mt-4 rounded-lg border p-3">
          <span className="text-sm font-medium">Color Quality:</span>{" "}
          <span className="text-lg font-bold">
            {job.color_quality_score.toFixed(1)}
          </span>
          {job.color_quality_grade && (
            <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-sm">
              Grade {job.color_quality_grade}
            </span>
          )}
        </div>
      )}

      {job.status === "complete" && (
        <div className="mt-4 flex gap-2">
          <Link
            href={`/dashboard/preflight/${job.job_id}/viewer`}
            className="rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Open Viewer
          </Link>
          <a
            href={`/api/lintpdf/reports/${job.job_id}/html`}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
          >
            View HTML Report
          </a>
          <a
            href={`/api/lintpdf/reports/${job.job_id}/download`}
            className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
          >
            Download PDF Report
          </a>
        </div>
      )}

      {job.error_message && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {job.error_message}
        </div>
      )}

      {job.findings && job.findings.length > 0 && (
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
    </main>
  );
}
