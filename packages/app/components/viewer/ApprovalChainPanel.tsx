"use client";

import { useCallback, useEffect, useState } from "react";
import { useViewerApi } from "./types";

interface ChainStep {
  name: string;
  approvers: Array<{ email: string; name?: string; role?: string }>;
  require_all: boolean;
  webhook_url?: string | null;
  timeout_hours?: number | null;
  on_timeout?: string;
}

interface StepHistory {
  step_index: number;
  step_name: string;
  approver_email: string;
  decision: string;
  notes: string | null;
  decided_at: string | null;
}

interface Chain {
  id: string;
  status: string;
  current_step: number;
  steps: ChainStep[];
  step_history: StepHistory[];
  created_at: string;
  completed_at: string | null;
}

export function ApprovalChainPanel({ onRefresh }: { onRefresh?: () => void }) {
  const { apiBase } = useViewerApi();
  const [chain, setChain] = useState<Chain | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchChain = useCallback(async () => {
    try {
      // apiBase for public viewer is /api/lintpdf/viewer/public/{token}
      const resp = await fetch(`${apiBase}/approval-chain`);
      if (resp.ok) {
        const data = await resp.json();
        setChain(data);
      } else {
        setChain(null);
      }
    } catch {
      setChain(null);
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchChain();
  }, [fetchChain]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-6 text-slate-200">
        <svg className="h-6 w-6 animate-spin text-slate-400" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span className="text-xs text-slate-500">Loading chain</span>
      </div>
    );
  }

  if (!chain) {
    return (
      <div className="p-4 text-sm text-slate-400">
        No approval chain attached to this job.
      </div>
    );
  }

  const statusColor =
    chain.status === "approved"
      ? "#22c55e"
      : chain.status === "rejected" || chain.status === "cancelled"
        ? "#ef4444"
        : "#f59e0b";

  // Group history by step_index for display
  const historyByStep: Record<number, StepHistory[]> = {};
  for (const h of chain.step_history) {
    if (!historyByStep[h.step_index]) historyByStep[h.step_index] = [];
    historyByStep[h.step_index]!.push(h);
  }

  return (
    <div className="flex flex-col gap-3 p-3 text-slate-200">
      {/* Overall status */}
      <div className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-800/50 p-3">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Chain Status
          </div>
          <div
            className="text-lg font-bold uppercase"
            style={{ color: statusColor }}
          >
            {chain.status}
          </div>
        </div>
        <div className="text-right text-xs text-slate-400">
          <div>Step {Math.min(chain.current_step + 1, chain.steps.length)} of {chain.steps.length}</div>
          {chain.completed_at && (
            <div className="text-[10px] text-slate-500">
              {new Date(chain.completed_at).toLocaleDateString()}
            </div>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-2">
        {chain.steps.map((step, i) => {
          const isDone = i < chain.current_step || chain.status !== "pending";
          const isCurrent = i === chain.current_step && chain.status === "pending";
          const history = historyByStep[i] || [];

          const stepColor =
            isDone && history.some((h) => h.decision === "rejected")
              ? "#ef4444"
              : isDone
                ? "#22c55e"
                : isCurrent
                  ? "#3b82f6"
                  : "#64748b";

          return (
            <div
              key={i}
              className={`rounded-lg border p-3 ${
                isCurrent
                  ? "border-blue-500/50 bg-blue-500/10"
                  : "border-slate-700 bg-slate-800/30"
              }`}
            >
              <div className="mb-1 flex items-center gap-2">
                <span
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                  style={{ backgroundColor: stepColor }}
                >
                  {i + 1}
                </span>
                <span className="flex-1 text-sm font-semibold text-white">{step.name}</span>
                {isCurrent && (
                  <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-bold uppercase text-blue-300">
                    Pending
                  </span>
                )}
              </div>

              {/* Approvers list */}
              <div className="mb-1 text-xs text-slate-400">
                {step.approvers.map((a) => a.email).join(", ")}
                {step.require_all && (
                  <span className="ml-2 rounded bg-slate-700 px-1.5 py-0.5 text-[9px] text-slate-400">
                    ALL required
                  </span>
                )}
              </div>

              {/* History entries for this step */}
              {history.map((h, hi) => (
                <div
                  key={hi}
                  className={`mt-2 rounded border-l-2 pl-2 text-xs ${
                    h.decision === "approved"
                      ? "border-green-500"
                      : h.decision === "rejected"
                        ? "border-red-500"
                        : "border-slate-600"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase text-white ${
                        h.decision === "approved"
                          ? "bg-green-600"
                          : h.decision === "rejected"
                            ? "bg-red-600"
                            : "bg-slate-600"
                      }`}
                    >
                      {h.decision}
                    </span>
                    <span className="text-slate-300">{h.approver_email}</span>
                    {h.decided_at && (
                      <span className="ml-auto text-[10px] text-slate-500">
                        {new Date(h.decided_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  {h.notes && (
                    <div className="mt-1 italic text-slate-400">"{h.notes}"</div>
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
