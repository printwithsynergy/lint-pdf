"use client";

import { useMemo, useState } from "react";
import { AuditChip } from "./AuditChip";
import type { PreflightSourceMode, ViewerFinding } from "../../types";
import { UpgradePrompt } from "./UpgradePrompt";

interface FindingsPanelProps {
  findings: ViewerFinding[];
  selectedFinding: ViewerFinding | null;
  onSelectFinding: (finding: ViewerFinding) => void;
  currentPage: number;
  /**
   * Source the findings were produced from. Controls empty-state copy so
   * imported reports don't claim "no findings were produced" when the real
   * meaning is "the third-party tool reported nothing".
   */
  preflightSource?: PreflightSourceMode;
  /** Human-readable label for the import source, e.g. "Enfocus PitStop". */
  externalSourceLabel?: string | null;
  /** Plan gate — when false, render an UpgradePrompt instead of the
   *  generic "load a tool" copy. Viewer tier sets this false. */
  capabilityFillinEnabled?: boolean;
  /** Plan name, surfaced in the UpgradePrompt when present. */
  currentPlan?: string;
  /**
   * Optional controlled state for the severity filter. When both
   * ``activeTab`` and ``onActiveTabChange`` are provided the component
   * drives its filter from props so the parent (e.g. the share-viewer
   * header chip row in WS-18) can set the tab externally. Omitting
   * either falls back to the internal ``useState`` path so
   * pre-existing callers keep working unchanged.
   */
  activeTab?: SeverityTab;
  onActiveTabChange?: (tab: SeverityTab) => void;
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
  preflightSource,
  externalSourceLabel,
  capabilityFillinEnabled = true,
  currentPlan,
  activeTab: controlledActiveTab,
  onActiveTabChange,
}: FindingsPanelProps) {
  const [internalActiveTab, setInternalActiveTab] = useState<SeverityTab>("all");
  const isControlled =
    controlledActiveTab !== undefined && onActiveTabChange !== undefined;
  const activeTab = isControlled ? controlledActiveTab : internalActiveTab;
  const setActiveTab = (tab: SeverityTab) => {
    if (isControlled) {
      onActiveTabChange(tab);
    } else {
      setInternalActiveTab(tab);
    }
  };
  const [filterScope, setFilterScope] = useState<"all" | "page">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Deduplicate: group by (inspection_id, page_num) and merge
  const deduped = useMemo(() => {
    const groups = new Map<string, ViewerFinding & { _count?: number }>();
    for (const f of findings) {
      const key = `${f.inspection_id}|${f.page_num ?? "doc"}`;
      if (!groups.has(key)) {
        groups.set(key, { ...f, _count: 1 });
      } else {
        groups.get(key)!._count! += 1;
      }
    }
    return Array.from(groups.values()).map((f) => {
      if (f._count && f._count > 1) {
        return { ...f, message: `${f.message} (+${f._count - 1} similar)` };
      }
      return f;
    });
  }, [findings]);

  const counts = useMemo(() => {
    const c = { all: 0, error: 0, warning: 0, advisory: 0 };
    for (const f of deduped) {
      c[f.severity]++;
      c.all++;
    }
    return c;
  }, [deduped]);

  const filtered = useMemo(() => {
    let items = deduped;
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
  }, [deduped, activeTab, filterScope, currentPage, searchQuery]);

  const tabs: { key: SeverityTab; label: string; color: string }[] = [
    { key: "all", label: "All", color: "text-slate-300" },
    { key: "error", label: "Errors", color: "text-red-400" },
    { key: "warning", label: "Warnings", color: "text-amber-400" },
    { key: "advisory", label: "Advisory", color: "text-blue-400" },
  ];

  return (
    <div className="flex h-full flex-col bg-slate-900 text-slate-200">
      {/* Search box */}
      <div className="shrink-0 border-b border-white/[0.06] px-3 py-2">
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
            className="w-full rounded-md border border-white/10 bg-slate-800 py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-white/20 focus:ring-1 focus:ring-white/20"
          />
        </div>
      </div>

      {/* Severity filter tabs */}
      <div className="flex shrink-0 border-b border-white/[0.06]">
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

      {/* Page scope toggle — segmented control */}
      <div className="flex shrink-0 items-center gap-2 border-b border-white/[0.06] px-3 py-1.5">
        <div className="inline-flex rounded-md bg-slate-800/50 p-0.5">
          <button
            onClick={() => setFilterScope("all")}
            className={`rounded px-2.5 py-1 text-[11px] font-medium transition-colors ${
              filterScope === "all"
                ? "bg-slate-700 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            All pages
          </button>
          <button
            onClick={() => setFilterScope("page")}
            className={`rounded px-2.5 py-1 text-[11px] font-medium transition-colors ${
              filterScope === "page"
                ? "bg-slate-700 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Page {currentPage} only
          </button>
        </div>
        <span className="text-[11px] text-slate-500">
          {filtered.length} finding{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Findings list - split into document and page sections */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          deduped.length === 0 &&
          preflightSource === "minimal" &&
          !capabilityFillinEnabled ? (
            <div className="p-4">
              <UpgradePrompt
                gate="capability_fillin"
                currentPlan={currentPlan}
                requiredPlan="starter"
              />
            </div>
          ) : (
            <div className="p-4 text-center text-sm text-slate-500">
              {deduped.length === 0 && preflightSource === "external"
                ? externalSourceLabel
                  ? `No findings reported by ${externalSourceLabel}.`
                  : "No findings reported by the imported preflight tool."
                : deduped.length === 0 && preflightSource === "minimal"
                  ? "Viewer-only mode — no preflight was run. Load a tool above to analyze this PDF."
                  : deduped.length === 0
                    ? "This document is clean — no findings were produced."
                    : "No findings match the current filter."}
            </div>
          )
        ) : (
          <>
            {(() => {
              const docFindings = filtered.filter((f) => !f.page_num && !f.bbox);
              const pageFindings = filtered.filter((f) => f.page_num || f.bbox);
              return (
                <>
                  {docFindings.length > 0 && (
                    <>
                      <div className="flex items-center justify-between bg-slate-800/50 px-3 py-1.5">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                          Document &amp; Compliance ({docFindings.length})
                        </span>
                      </div>
                      {docFindings.map((f, i) => (
                        <div
                          key={`doc-${f.inspection_id}-${i}`}
                          className="flex w-full items-center gap-2 px-3 py-1.5 text-left"
                        >
                          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${SEVERITY_DOT[f.severity]}`} />
                          <code className="shrink-0 text-[10px] font-mono text-slate-500">{f.inspection_id}</code>
                          <span className="flex-1 truncate text-[11px] text-slate-400">{f.message}</span>
                        </div>
                      ))}
                    </>
                  )}

                  {/* Page Issues */}
                  {pageFindings.length > 0 && (
                    <>
                      {docFindings.length > 0 && (
                        <div className="flex items-center justify-between bg-slate-800/50 px-3 py-1.5">
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                            Page Issues ({pageFindings.length})
                          </span>
                        </div>
                      )}
                      {pageFindings.map((f, i) => {
                        const isSelected =
                          selectedFinding?.inspection_id === f.inspection_id &&
                          selectedFinding?.page_num === f.page_num &&
                          selectedFinding?.message === f.message;
                        return (
                          <button
                            key={`page-${f.inspection_id}-${f.page_num}-${i}`}
                            onClick={() => onSelectFinding(f)}
                            className={`w-full px-3 py-2.5 text-left transition-colors hover:bg-slate-800/80 ${
                              isSelected
                                ? `border-l-[3px] ${SEVERITY_BORDER[f.severity]} ${SEVERITY_SELECTED_BG[f.severity]}`
                                : "border-l-[3px] border-l-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className={`h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[f.severity]}`} />
                              <AuditChip verdict={f.audit ?? null} />
                              <code className="text-[10px] font-mono text-slate-500">{f.inspection_id}</code>
                              {f.page_num ? (
                                <span className="ml-auto shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-400">
                                  p.{f.page_num}
                                </span>
                              ) : null}
                            </div>
                            <p className="mt-1 line-clamp-2 text-xs leading-snug text-slate-300">{f.message}</p>
                          </button>
                        );
                      })}
                    </>
                  )}
                </>
              );
            })()}
          </>
        )}
      </div>
    </div>
  );
}
