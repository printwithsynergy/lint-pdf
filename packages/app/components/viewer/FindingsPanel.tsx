"use client";

import { useMemo, useState } from "react";
import type { ViewerFinding } from "./types";

interface FindingsPanelProps {
  findings: ViewerFinding[];
  selectedFinding: ViewerFinding | null;
  onSelectFinding: (finding: ViewerFinding) => void;
  currentPage: number;
}

type SeverityTab = "all" | "error" | "warning" | "advisory";

const SEVERITY_DOT: Record<string, string> = {
  error: "bg-red-500",
  warning: "bg-amber-500",
  advisory: "bg-blue-500",
};

const SEVERITY_BORDER: Record<string, string> = {
  error: "border-l-red-500",
  warning: "border-l-amber-500",
  advisory: "border-l-blue-500",
};

const SEVERITY_SELECTED_BG: Record<string, string> = {
  error: "bg-red-500/10",
  warning: "bg-amber-500/10",
  advisory: "bg-blue-500/10",
};

export function FindingsPanel({
  findings,
  selectedFinding,
  onSelectFinding,
  currentPage,
}: FindingsPanelProps) {
  const [activeTab, setActiveTab] = useState<SeverityTab>("all");
  const [filterScope, setFilterScope] = useState<"all" | "page">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const counts = useMemo(() => {
    const c = { all: 0, error: 0, warning: 0, advisory: 0 };
    for (const f of findings) {
      c[f.severity]++;
      c.all++;
    }
    return c;
  }, [findings]);

  const filtered = useMemo(() => {
    let items = findings;
    if (activeTab !== "all") {
      items = items.filter((f) => f.severity === activeTab);
    }
    if (filterScope === "page") {
      items = items.filter((f) => f.page_num === currentPage);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter(
        (f) =>
          f.message.toLowerCase().includes(q) ||
          f.inspection_id.toLowerCase().includes(q),
      );
    }
    return items;
  }, [findings, activeTab, filterScope, currentPage, searchQuery]);

  const tabs: { key: SeverityTab; label: string; color: string }[] = [
    { key: "all", label: "All", color: "text-slate-300" },
    { key: "error", label: "Errors", color: "text-red-400" },
    { key: "warning", label: "Warnings", color: "text-amber-400" },
    { key: "advisory", label: "Advisory", color: "text-blue-400" },
  ];

  return (
    <div className="flex h-full flex-col bg-slate-900 text-slate-200">
      {/* Search box */}
      <div className="shrink-0 border-b border-slate-700 px-3 py-2">
        <div className="relative">
          <svg
            className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="text"
            placeholder="Search findings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-slate-700 bg-slate-800 py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500"
          />
        </div>
      </div>

      {/* Severity filter tabs */}
      <div className="flex shrink-0 border-b border-slate-700">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex flex-1 items-center justify-center gap-1.5 px-2 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? `${tab.color} border-b-2 ${
                    tab.key === "all"
                      ? "border-slate-300"
                      : tab.key === "error"
                        ? "border-red-400"
                        : tab.key === "warning"
                          ? "border-amber-400"
                          : "border-blue-400"
                  }`
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
            <span
              className={`rounded-full px-1.5 py-0.5 text-[10px] leading-none ${
                activeTab === tab.key
                  ? "bg-slate-700 text-slate-200"
                  : "bg-slate-800 text-slate-500"
              }`}
            >
              {counts[tab.key]}
            </span>
          </button>
        ))}
      </div>

      {/* Page scope toggle */}
      <div className="flex shrink-0 items-center gap-2 border-b border-slate-700 px-3 py-1.5">
        <button
          onClick={() => setFilterScope((s) => (s === "all" ? "page" : "all"))}
          className={`rounded border px-2 py-0.5 text-[11px] transition-colors ${
            filterScope === "page"
              ? "border-blue-500 bg-blue-500/20 text-blue-400"
              : "border-slate-700 text-slate-400 hover:border-slate-500"
          }`}
        >
          Page {currentPage} only
        </button>
        <span className="text-[11px] text-slate-500">
          {filtered.length} finding{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Findings list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-4 text-center text-sm text-slate-500">
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
                className={`w-full border-b border-slate-800 px-3 py-2.5 text-left transition-colors hover:bg-slate-800/80 ${
                  isSelected
                    ? `border-l-[3px] ${SEVERITY_BORDER[f.severity]} ${SEVERITY_SELECTED_BG[f.severity]}`
                    : "border-l-[3px] border-l-transparent"
                }`}
              >
                <div className="flex items-center gap-2">
                  {/* Severity dot */}
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[f.severity]}`}
                  />
                  {/* Check ID */}
                  <code className="text-[10px] font-mono text-slate-500">
                    {f.inspection_id}
                  </code>
                  {/* Page badge */}
                  {f.page_num ? (
                    <span className="ml-auto shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-400">
                      p.{f.page_num}
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-snug text-slate-300">
                  {f.message}
                </p>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
