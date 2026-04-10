"use client";

import { useCallback, useState } from "react";
import type { ComparisonState } from "./types";

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
  const [compareJobId, setCompareJobId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCompare = useCallback(async () => {
    if (!compareJobId.trim()) return;
    setLoading(true);
    setError("");

    try {
      const resp = await fetch("/api/lintpdf/viewer/compare", {
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
  }, [jobId, compareJobId, onStartComparison]);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-3 py-2">
        <h3 className="text-sm font-semibold">File Comparison</h3>
      </div>

      {/* Job selector */}
      <div className="space-y-2 border-b p-3">
        <div className="text-xs text-muted-foreground">
          Current: <code className="text-[10px]">{jobId.slice(0, 8)}...</code>
        </div>
        <div className="flex gap-1">
          <input
            type="text"
            value={compareJobId}
            onChange={(e) => setCompareJobId(e.target.value)}
            placeholder="Compare with Job ID..."
            className="flex-1 rounded border px-2 py-1 text-xs"
          />
          <button
            onClick={handleCompare}
            disabled={loading || !compareJobId.trim()}
            className="rounded bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
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
          <div className="flex gap-1 border-b p-2">
            {(["ab", "side-by-side", "overlay"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => onModeChange(mode)}
                className={`rounded px-2 py-1 text-xs ${
                  comparisonMode === mode
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
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
            <div className="p-2 text-xs text-muted-foreground">
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
                  className={`flex w-full items-center justify-between border-b px-3 py-2 text-left text-xs hover:bg-muted/50 ${
                    isActive ? "bg-primary/5 ring-1 ring-inset ring-primary/20" : ""
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
                      <span className="text-[10px] text-muted-foreground">
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
