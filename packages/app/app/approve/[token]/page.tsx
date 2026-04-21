"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

interface ChainInfo {
  id: string;
  job_id: string;
  status: string;
  current_step: number;
  total_steps: number;
  current_step_name: string | null;
  completed_steps: Array<{
    step_index: number;
    step_name: string;
    approver_email: string;
    decision: string;
    notes: string | null;
    decided_at: string | null;
  }>;
  file_name: string;
  health_summary: {
    total_findings: number;
    error_count: number;
    warning_count: number;
    advisory_count: number;
    passed: boolean;
    page_count: number;
  };
}

export default function ApprovePage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const [info, setInfo] = useState<ChainInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState<{ ok: true; decision: string } | null>(null);
  const [notes, setNotes] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const fetchInfo = useCallback(async () => {
    try {
      const resp = await fetch(`/api/lintpdf/approvals/info/${token}`);
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(
          data.detail ||
            (resp.status === 404
              ? "This approval link is invalid or has already been used."
              : resp.status === 410
                ? "This approval link has expired."
                : "Unable to load approval details."),
        );
      }
      const data = await resp.json();
      setInfo(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) fetchInfo();
  }, [token, fetchInfo]);

  async function submitDecision(decision: "approved" | "rejected") {
    setSubmitting(true);
    setError("");
    try {
      const resp = await fetch(`/api/lintpdf/approvals/decide/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, notes: notes.trim() || null }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || data.error || "Failed to submit decision");
      }
      setDone({ ok: true, decision });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="flex flex-col items-center gap-3">
          <svg className="h-10 w-10 animate-spin text-muted-foreground" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm text-muted-foreground">Loading approval details…</span>
        </div>
      </div>
    );
  }

  if (error && !info) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-lg">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="mb-2 text-xl font-bold text-slate-900">Unable to load</h1>
          <p className="text-sm text-slate-600">{error}</p>
        </div>
      </div>
    );
  }

  if (done) {
    const isApproved = done.decision === "approved";
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-lg">
          <div
            className={`mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full ${
              isApproved ? "bg-green-100" : "bg-red-100"
            }`}
          >
            {isApproved ? (
              <svg className="h-7 w-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="h-7 w-7 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </div>
          <h1 className="mb-2 text-2xl font-bold text-slate-900">
            {isApproved ? "Approved!" : "Rejected"}
          </h1>
          <p className="text-sm text-slate-600">
            Your decision has been recorded. The chain initiator and any subsequent approvers have been notified.
          </p>
        </div>
      </div>
    );
  }

  if (!info) return null;

  if (info.status !== "pending") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-md rounded-xl bg-white p-8 text-center shadow-lg">
          <h1 className="mb-2 text-xl font-bold text-slate-900">Chain {info.status}</h1>
          <p className="text-sm text-slate-600">
            This approval chain is no longer active (status: <strong>{info.status}</strong>).
          </p>
        </div>
      </div>
    );
  }

  const { health_summary: h } = info;
  const healthScore = Math.max(
    0,
    Math.min(100, Math.round(100 - h.error_count * 10 - h.warning_count * 3 - h.advisory_count * 0.5)),
  );
  const healthColor = healthScore >= 80 ? "#22c55e" : healthScore >= 70 ? "#f59e0b" : "#ef4444";

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="mx-auto max-w-2xl">
        <div className="rounded-xl bg-white p-6 shadow-lg sm:p-8">
          {/* Header */}
          <div className="mb-6 border-b border-slate-200 pb-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Approval Request
            </div>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              {info.current_step_name || `Step ${info.current_step + 1}`}
            </h1>
            <div className="mt-1 text-sm text-slate-600">
              Step {info.current_step + 1} of {info.total_steps} · {info.file_name}
            </div>
          </div>

          {/* Health summary */}
          <div className="mb-6 flex items-center gap-4 rounded-lg bg-background p-4">
            <div
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-[5px]"
              style={{ borderColor: healthColor }}
            >
              <div className="text-center">
                <div className="text-xl font-extrabold leading-none" style={{ color: healthColor }}>
                  {healthScore}
                </div>
                <div className="text-[9px] text-slate-500">/100</div>
              </div>
            </div>
            <div className="flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-bold uppercase text-white ${
                    h.passed ? "bg-green-600" : "bg-red-600"
                  }`}
                >
                  {h.passed ? "Pass" : "Fail"}
                </span>
                <span className="text-xs text-slate-500">{h.page_count} pages</span>
              </div>
              <div className="flex gap-3 text-xs">
                <span className="text-red-600">
                  <strong>{h.error_count}</strong> errors
                </span>
                <span className="text-amber-600">
                  <strong>{h.warning_count}</strong> warnings
                </span>
                <span className="text-blue-600">
                  <strong>{h.advisory_count}</strong> advisory
                </span>
              </div>
            </div>
          </div>

          {/* Completed steps */}
          {info.completed_steps.length > 0 && (
            <div className="mb-6">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Previous Steps
              </div>
              <div className="space-y-1">
                {info.completed_steps.map((s) => (
                  <div
                    key={`${s.step_index}-${s.approver_email}`}
                    className={`flex items-start gap-2 rounded border-l-4 px-3 py-2 text-xs ${
                      s.decision === "approved"
                        ? "border-green-500 bg-green-50"
                        : "border-red-500 bg-red-50"
                    }`}
                  >
                    <span
                      className={`mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase text-white ${
                        s.decision === "approved" ? "bg-green-600" : "bg-red-600"
                      }`}
                    >
                      {s.decision}
                    </span>
                    <div className="flex-1">
                      <div className="font-semibold text-slate-800">{s.step_name}</div>
                      <div className="text-slate-600">{s.approver_email}</div>
                      {s.notes && <div className="mt-1 italic text-slate-500">&ldquo;{s.notes}&rdquo;</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* View full report link */}
          <div className="mb-6">
            <a
              href={`/view/${token}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View the full interactive report
            </a>
          </div>

          {/* Decision buttons */}
          {error && (
            <div className="mb-3 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
              {error}
            </div>
          )}

          {showRejectForm ? (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-slate-700">
                Rejection Notes (required)
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200"
                  placeholder="Explain why this is being rejected..."
                  autoFocus
                />
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowRejectForm(false)}
                  className="flex-1 rounded-md border border-slate-300 bg-white px-6 py-2.5 text-sm font-medium text-slate-700 hover:bg-background"
                >
                  Back
                </button>
                <button
                  onClick={() => submitDecision("rejected")}
                  disabled={submitting || !notes.trim()}
                  className="flex-1 rounded-md bg-red-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-40"
                >
                  {submitting ? "Submitting…" : "Confirm Rejection"}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={() => setShowRejectForm(true)}
                disabled={submitting}
                className="flex-1 rounded-md border-2 border-red-500 bg-white px-6 py-2.5 text-sm font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40"
              >
                Reject
              </button>
              <button
                onClick={() => submitDecision("approved")}
                disabled={submitting}
                className="flex-1 rounded-md bg-green-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-40"
              >
                {submitting ? "Submitting…" : "Approve"}
              </button>
            </div>
          )}

          {/* Optional approval notes */}
          {!showRejectForm && (
            <div className="mt-4">
              <label className="block text-xs font-medium text-slate-600">
                Optional notes
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500"
                  placeholder="Add any notes to include with your decision..."
                />
              </label>
            </div>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-slate-500">
          This link is unique to you. If you did not expect this email, you can ignore it.
        </p>
      </div>
    </div>
  );
}
