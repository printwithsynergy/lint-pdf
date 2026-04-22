"use client";

import type { AuditVerdict } from "./types";

/**
 * AI accuracy-audit chip shown next to each finding row.
 *
 * Renders nothing when the tenant isn't entitled to ``ai_audit`` (or
 * the job was submitted before the feature shipped) — the server
 * passes `null` for every row in that case, so the caller's
 * ``verdict == null`` guard already filters most of the tree.
 *
 * Status icons intentionally small (12 px) so the chip is a
 * peripheral cue, not a visual shout. Tooltip surfaces the full
 * AI rationale on hover / focus for accessibility.
 */
export function AuditChip({
  verdict,
}: {
  verdict: AuditVerdict | null | undefined;
}): React.ReactNode {
  if (!verdict) return null;

  const { status, rationale } = verdict;
  const label =
    status === "confirmed"
      ? "AI confirms this finding"
      : status === "disputed"
        ? `AI disputes: ${rationale ?? "no rationale"}`
        : status === "needs_context"
          ? `AI needs context: ${rationale ?? "add a JDF sidecar or brand profile"}`
          : "AI audit failed";

  const bg =
    status === "confirmed"
      ? "bg-emerald-500/20 text-emerald-300"
      : status === "disputed"
        ? "bg-amber-500/25 text-amber-200"
        : status === "needs_context"
          ? "bg-slate-500/25 text-slate-300"
          : "bg-red-500/20 text-red-300";

  return (
    <span
      className={`inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${bg}`}
      title={label}
      aria-label={label}
      role="img"
    >
      {status === "confirmed" && (
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {status === "disputed" && (
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path d="M12 9v2m0 4h.01M4.93 19h14.14a2 2 0 001.74-3L13.74 5a2 2 0 00-3.48 0L3.19 16a2 2 0 001.74 3z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {status === "needs_context" && (
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path d="M13 16h-1v-4h-1m1-4h.01" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="12" cy="12" r="9" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )}
      {status === "error" && (
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" />
        </svg>
      )}
    </span>
  );
}
