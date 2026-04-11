"use client";

import { useCallback, useEffect, useState } from "react";
import type { VerdictState, ViewerConfig } from "./types";
import { useViewerApi } from "./types";

interface VerdictBarProps {
  jobId: string;
  config: ViewerConfig;
}

export function VerdictBar({ jobId, config }: VerdictBarProps) {
  const { apiBase, readOnly } = useViewerApi();
  const [verdict, setVerdict] = useState<VerdictState | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFailForm, setShowFailForm] = useState(false);
  const [failNotes, setFailNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchVerdict = useCallback(async () => {
    try {
      const resp = await fetch(`${apiBase}/verdict`);
      if (resp.ok) {
        setVerdict(await resp.json());
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchVerdict();
  }, [fetchVerdict]);

  const submitVerdict = useCallback(
    async (v: "pass" | "fail", notes?: string) => {
      setSubmitting(true);
      try {
        const resp = await fetch(`${apiBase}/verdict`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ verdict: v, notes: notes || null }),
        });
        if (resp.ok) {
          setVerdict(await resp.json());
          setShowFailForm(false);
          setFailNotes("");
        }
      } catch {
        // ignore
      } finally {
        setSubmitting(false);
      }
    },
    [apiBase],
  );

  if (config.verdict_mode === "disabled" || loading) return null;

  const isAuto = config.verdict_mode === "auto";
  const passed = verdict?.auto_passed;
  const manualVerdict = verdict?.verdict;

  // Determine display verdict
  const displayVerdict = isAuto ? (passed ? "pass" : "fail") : manualVerdict;
  const isPending = !isAuto && !manualVerdict;

  return (
    <div
      className={`flex flex-col gap-2 border-b px-4 py-2 text-sm sm:flex-row sm:items-center sm:justify-between ${
        displayVerdict === "pass"
          ? "border-green-200 bg-green-50 dark:bg-green-950/20"
          : displayVerdict === "fail"
            ? "border-red-200 bg-red-50 dark:bg-red-950/20"
            : "border-amber-200 bg-amber-50 dark:bg-amber-950/20"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        {/* Verdict badge */}
        <span
          className={`rounded px-3 py-1 text-xs font-bold uppercase ${
            displayVerdict === "pass"
              ? "bg-green-100 text-green-800"
              : displayVerdict === "fail"
                ? "bg-red-100 text-red-800"
                : "bg-amber-100 text-amber-800"
          }`}
        >
          {displayVerdict === "pass"
            ? "PASS"
            : displayVerdict === "fail"
              ? "FAIL"
              : "PENDING REVIEW"}
        </span>

        {isAuto && (
          <span className="text-xs text-muted-foreground">
            Auto verdict from preflight results
          </span>
        )}

        {manualVerdict && verdict?.verdict_by && (
          <span className="text-xs text-muted-foreground">
            by {verdict.verdict_by}
            {verdict.verdict_at &&
              ` on ${new Date(verdict.verdict_at).toLocaleDateString()}`}
          </span>
        )}

        {verdict?.notes && (
          <span className="text-xs italic text-muted-foreground">
            &ldquo;{verdict.notes}&rdquo;
          </span>
        )}
      </div>

      {/* Manual verdict controls */}
      {!isAuto && !readOnly && (
        <div className="flex flex-wrap items-center gap-2">
          {showFailForm ? (
            <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
              <input
                type="text"
                value={failNotes}
                onChange={(e) => setFailNotes(e.target.value)}
                placeholder="Failure notes (required)..."
                className="w-full rounded border px-2 py-1 text-xs sm:w-60"
              />
              <button
                onClick={() => submitVerdict("fail", failNotes)}
                disabled={submitting || !failNotes.trim()}
                className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-40"
              >
                Confirm Fail
              </button>
              <button
                onClick={() => setShowFailForm(false)}
                className="rounded border px-2 py-1 text-xs hover:bg-muted"
              >
                Cancel
              </button>
            </div>
          ) : (
            <>
              <button
                onClick={() => submitVerdict("pass")}
                disabled={submitting}
                className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-40"
              >
                Mark Pass
              </button>
              <button
                onClick={() => setShowFailForm(true)}
                disabled={submitting}
                className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-40"
              >
                Mark Fail
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
