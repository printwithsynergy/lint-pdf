"use client";

import { useCallback, useState } from "react";
import type { ComparisonState } from "../../types";
import { useViewerApi } from "../../types";

interface ComparisonPanelProps {
  jobId: string;
  comparison: ComparisonState | null;
  onStartComparison: (comparison: ComparisonState) => void;
  comparisonMode: "ab" | "side-by-side" | "overlay";
  onModeChange: (mode: "ab" | "side-by-side" | "overlay") => void;
  currentPage: number;
  onPageChange: (page: number) => void;
}

export function ComparisonPanel({
  jobId,
  comparison,
  onStartComparison,
  comparisonMode,
  onModeChange,
  currentPage,
  onPageChange,
}: ComparisonPanelProps) {
  const { apiBase } = useViewerApi();
  const [compareJobId, setCompareJobId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCompare = useCallback(async () => {
    if (!compareJobId.trim()) return;
    setLoading(true);
    setError("");

    try {
      const resp = await fetch(`${apiBase.replace(/\/viewer\/.*$/, '/viewer/compare')}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_a: jobId,
          job_b: compareJobId.trim(),
          dpi: 150,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        setError(err.detail || "Comparison failed");
        return;
      }

      const data = await resp.json();
      onStartComparison(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  }, [apiBase, jobId, compareJobId, onStartComparison]);

  return (
    <div className="flex h-full flex-col text-slate-200">
      <div className="border-b border-white/[0.06] px-3 py-2">
        <h3 className="text-sm font-semibold text-white">File Comparison</h3>
      </div>

      {/* Job selector */}
      <div className="space-y-2 border-b border-white/[0.06] p-3">
        <div className="text-xs text-slate-400">
          Current: <code className="text-[10px] text-slate-300">{jobId.slice(0, 8)}...</code>
        </div>
        <div className="flex gap-1">
          <input
            type="text"
            value={compareJobId}
            onChange={(e) => setCompareJobId(e.target.value)}
            placeholder="Compare with Job ID..."
            className="flex-1 rounded border border-white/10 bg-slate-800 px-2 py-1 text-xs text-slate-200 placeholder-slate-500"
          />
          <button
            onClick={handleCompare}
            disabled={loading || !compareJobId.trim()}
            className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {loading ? "..." : "Compare"}
          </button>
        </div>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      {/* Comparison results */}
      {comparison && (
        <>
          {/* Mode selector */}
          <div className="flex gap-1 border-b border-white/[0.06] p-2">
            {(["ab", "side-by-side", "overlay"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => onModeChange(mode)}
                className={`rounded px-2 py-1 text-xs ${
                  comparisonMode === mode
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                {mode === "ab"
                  ? "A/B Toggle"
                  : mode === "side-by-side"
                    ? "Side by Side"
                    : "Overlay Diff"}
              </button>
            ))}
          </div>

          {/* Page SSIM scores */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-2 text-xs text-slate-400">
              {comparison.page_count_a} pages (A) vs {comparison.page_count_b} pages (B)
            </div>
            {comparison.pages.map((p) => {
              const score = p.ssim_score;
              const pct = Math.round(score * 100);
              const isActive = p.page_num === currentPage;
              return (
                <button
                  key={p.page_num}
                  onClick={() => onPageChange(p.page_num)}
                  className={`flex w-full items-center justify-between border-b border-white/[0.06] px-3 py-2 text-left text-xs text-slate-200 hover:bg-slate-800 ${
                    isActive ? "bg-slate-800 ring-1 ring-inset ring-blue-500/30" : ""
                  }`}
                >
                  <span>Page {p.page_num}</span>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${
                          pct >= 95
                            ? "bg-green-500"
                            : pct >= 80
                              ? "bg-amber-500"
                              : "bg-red-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span
                      className={`font-mono text-[10px] ${
                        pct >= 95
                          ? "text-green-600"
                          : pct >= 80
                            ? "text-amber-600"
                            : "text-red-600"
                      }`}
                    >
                      {pct}%
                    </span>
                    {p.diff_pixel_count > 0 && (
                      <span className="text-[10px] text-slate-500">
                        {p.diff_pixel_count.toLocaleString()} px
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
