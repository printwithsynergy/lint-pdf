import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle,
  FileText,
  Loader,
  XCircle,
} from "lucide-react";
import type { CapturedTenant } from "../lib/types";
import {
  type ApprovalChainInfo,
  type ApprovalDecision,
  ApprovalError,
  fetchApprovalInfo,
  submitApprovalDecision,
} from "../lib/approvals";

interface ApproveRouteProps {
  tenant: CapturedTenant;
}

/**
 * Mobile approval landing screen. Loads the chain summary from
 * `GET /api/lintpdf/approvals/info/{token}`, lets the approver
 * Approve or Reject (with optional notes), and POSTs the decision
 * to `/api/lintpdf/approvals/decide/{token}`.
 *
 * Token-only auth — the URL access_token IS the credential, no
 * session cookie needed. Same contract the desktop and web `/approve`
 * pages use.
 */
export function ApproveRoute({ tenant }: ApproveRouteProps) {
  const { token } = useParams<{ token: string }>();
  const [info, setInfo] = useState<ApprovalChainInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<ApprovalDecision | null>(null);
  const [done, setDone] = useState<{ decision: ApprovalDecision } | null>(null);
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [notes, setNotes] = useState("");

  const refresh = useCallback(async () => {
    if (!token) {
      setLoadError("Missing approval token in URL.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setLoadError(null);
    try {
      const data = await fetchApprovalInfo(token);
      setInfo(data);
    } catch (err) {
      setLoadError(
        err instanceof ApprovalError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Unable to load approval details.",
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleDecide(decision: ApprovalDecision) {
    if (!token) return;
    if (decision === "rejected" && !showRejectForm) {
      setShowRejectForm(true);
      return;
    }

    setSubmitting(decision);
    setSubmitError(null);
    try {
      await submitApprovalDecision(token, decision, notes);
      setDone({ decision });
    } catch (err) {
      setSubmitError(
        err instanceof ApprovalError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to submit decision",
      );
    } finally {
      setSubmitting(null);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center px-4 py-12 text-center text-sm text-gray-500">
        <Loader className="mb-2 h-5 w-5 animate-spin" />
        Loading approval details…
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center px-4 py-12 text-center">
        <XCircle className="mb-3 h-10 w-10 text-red-500" />
        <h1 className="text-lg font-semibold text-gray-900">
          Can't open this approval
        </h1>
        <p className="mt-2 text-sm text-gray-600">{loadError}</p>
      </div>
    );
  }

  if (done && info) {
    return (
      <div className="mx-auto flex min-h-full max-w-md flex-col items-center justify-center px-4 py-12 text-center">
        <CheckCircle className="mb-3 h-12 w-12 text-green-500" />
        <h1 className="text-lg font-semibold text-gray-900">
          {done.decision === "approved" ? "Approved" : "Rejected"}
        </h1>
        <p className="mt-2 text-sm text-gray-600">
          Your decision on{" "}
          <span className="font-medium">{info.file_name}</span> has been
          recorded for {tenant.name}.
        </p>
      </div>
    );
  }

  if (!info) return null;

  const verdictGood = info.health_summary.passed;
  const errorCount = info.health_summary.error_count;
  const warningCount = info.health_summary.warning_count;

  return (
    <div className="mx-auto max-w-md px-4 py-5">
      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <div className="flex items-start gap-3">
          <FileText className="mt-1 h-5 w-5 flex-shrink-0 text-brand-600" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-gray-900">
              {info.file_name || "Untitled"}
            </p>
            <p className="text-xs text-gray-500">
              Step {info.current_step + 1} of {info.total_steps}
              {info.current_step_name ? ` · ${info.current_step_name}` : ""}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <Stat
            label="Pages"
            value={info.health_summary.page_count}
            tone="neutral"
          />
          <Stat
            label="Errors"
            value={errorCount}
            tone={errorCount > 0 ? "bad" : "good"}
          />
          <Stat
            label="Warnings"
            value={warningCount}
            tone={warningCount > 0 ? "warn" : "good"}
          />
        </div>

        <div
          className={`mt-3 flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${
            verdictGood
              ? "bg-green-50 text-green-700"
              : "bg-amber-50 text-amber-700"
          }`}
        >
          {verdictGood ? (
            <CheckCircle className="h-4 w-4" />
          ) : (
            <AlertTriangle className="h-4 w-4" />
          )}
          {verdictGood
            ? "Preflight passed"
            : `Preflight has ${errorCount} error${errorCount === 1 ? "" : "s"}`}
        </div>
      </div>

      {info.completed_steps.length > 0 && (
        <div className="mt-4 rounded-2xl bg-white p-4 shadow-sm">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Earlier decisions
          </h2>
          <ul className="space-y-2">
            {info.completed_steps.map((s) => (
              <li
                key={`${s.step_index}-${s.approver_email}`}
                className="flex items-start gap-2 text-xs"
              >
                {s.decision === "approved" ? (
                  <CheckCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-green-500" />
                ) : (
                  <XCircle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-red-500" />
                )}
                <div className="min-w-0">
                  <p className="truncate text-gray-900">
                    {s.step_name} · {s.approver_email}
                  </p>
                  {s.notes && (
                    <p className="mt-0.5 text-gray-500">"{s.notes}"</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 rounded-2xl bg-white p-4 shadow-sm">
        {showRejectForm && (
          <div className="mb-3">
            <label className="mb-1 block text-xs font-medium text-gray-700">
              Rejection reason{" "}
              <span className="font-normal text-gray-400">(optional)</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Tell the previous approver what to fix…"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
            />
          </div>
        )}

        {submitError && (
          <div className="mb-3 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void handleDecide("rejected")}
            disabled={submitting !== null}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-red-200 bg-white px-4 py-3 text-sm font-medium text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting === "rejected" ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            {showRejectForm ? "Confirm reject" : "Reject"}
          </button>
          <button
            type="button"
            onClick={() => void handleDecide("approved")}
            disabled={submitting !== null}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-3 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting === "approved" ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle className="h-4 w-4" />
            )}
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "good" | "warn" | "bad" | "neutral";
}) {
  const toneClass =
    tone === "bad"
      ? "bg-red-50 text-red-700"
      : tone === "warn"
        ? "bg-amber-50 text-amber-700"
        : tone === "good"
          ? "bg-green-50 text-green-700"
          : "bg-gray-50 text-gray-700";
  return (
    <div className={`rounded-lg px-2 py-2 ${toneClass}`}>
      <p className="text-base font-semibold leading-tight">{value}</p>
      <p className="mt-0.5 text-[10px] uppercase tracking-wide opacity-70">
        {label}
      </p>
    </div>
  );
}
