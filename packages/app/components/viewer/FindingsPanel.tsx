"use client";

import { useMemo, useState } from "react";
import type { ViewerFinding } from "./types";

interface FindingsPanelProps {
  findings: ViewerFinding[];
  selectedFinding: ViewerFinding | null;
  onSelectFinding: (finding: ViewerFinding) => void;
  currentPage: number;
}

const SEVERITY_BADGE = {
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  warning:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  advisory:
    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
};

export function FindingsPanel({
  findings,
  selectedFinding,
  onSelectFinding,
  currentPage,
}: FindingsPanelProps) {
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [filterScope, setFilterScope] = useState<"all" | "page">("all");

  const filtered = useMemo(() => {
    let items = findings;
    if (filterSeverity !== "all") {
      items = items.filter((f) => f.severity === filterSeverity);
    }
    if (filterScope === "page") {
      items = items.filter((f) => f.page_num === currentPage);
    }
    return items;
  }, [findings, filterSeverity, filterScope, currentPage]);

  const counts = useMemo(() => {
    const c = { error: 0, warning: 0, advisory: 0 };
    for (const f of findings) c[f.severity]++;
    return c;
  }, [findings]);

  return (
    <div className="flex h-full flex-col">
      {/* Summary bar */}
      <div className="flex items-center gap-2 border-b px-3 py-2 text-xs">
        <span className="font-medium text-red-600">{counts.error} errors</span>
        <span className="font-medium text-amber-600">
          {counts.warning} warnings
        </span>
        <span className="font-medium text-blue-600">
          {counts.advisory} advisory
        </span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 border-b px-3 py-1.5">
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="rounded border px-1.5 py-0.5 text-xs"
        >
          <option value="all">All severities</option>
          <option value="error">Errors only</option>
          <option value="warning">Warnings only</option>
          <option value="advisory">Advisory only</option>
        </select>
        <button
          onClick={() =>
            setFilterScope((s) => (s === "all" ? "page" : "all"))
          }
          className={`rounded border px-1.5 py-0.5 text-xs ${
            filterScope === "page" ? "bg-primary text-primary-foreground" : ""
          }`}
        >
          This page
        </button>
      </div>

      {/* Findings list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No findings match the current filter.
          </div>
        ) : (
          filtered.map((f, i) => {
            const isSelected =
              selectedFinding?.inspection_id === f.inspection_id &&
              selectedFinding?.page_num === f.page_num &&
              selectedFinding?.message === f.message;
            return (
              <button
                key={`${f.inspection_id}-${f.page_num}-${i}`}
                onClick={() => onSelectFinding(f)}
                className={`w-full border-b px-3 py-2 text-left transition-colors hover:bg-muted/50 ${
                  isSelected ? "bg-primary/5 ring-1 ring-inset ring-primary/20" : ""
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                      SEVERITY_BADGE[f.severity]
                    }`}
                  >
                    {f.severity}
                  </span>
                  <code className="text-[10px] text-muted-foreground">
                    {f.inspection_id}
                  </code>
                  {f.page_num ? (
                    <span className="ml-auto text-[10px] text-muted-foreground">
                      p.{f.page_num}
                    </span>
                  ) : null}
                </div>
                <p className="mt-0.5 text-xs leading-snug">{f.message}</p>
                {f.bbox && (
                  <span className="mt-0.5 inline-block text-[9px] text-muted-foreground">
                    Has location
                  </span>
                )}
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
