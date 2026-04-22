"use client";

import { useState } from "react";
import { ZoomControls } from "./ZoomControls";
import type { ViewerCapabilityKey, ViewerConfig } from "./types";
import { DEFAULT_VIEWER_CONFIG, FILLABLE_CAPABILITIES, useViewerApi } from "./types";

type ViewerMode = "normal" | "separation" | "layers" | "annotation" | "comparison" | "health" | "chain";
type MeasureMode = "none" | "color_picker" | "densitometer" | "ruler";

interface ViewerToolbarProps {
  currentPage: number;
  pageCount: number;
  zoom: number;
  onPageChange: (page: number) => void;
  onZoomChange: (zoom: number) => void;
  jobId: string;
  fileName?: string;
  config?: ViewerConfig;
  viewerMode?: ViewerMode;
  onToggleMode?: (mode: ViewerMode) => void;
  measureMode?: MeasureMode;
  onToggleMeasure?: (mode: MeasureMode) => void;
  /** Active markup tool: rect / circle / arrow / freehand / note, or null when no draw tool is selected. */
  markupKind?: "rect" | "circle" | "arrow" | "freehand" | "note" | null;
  onToggleMarkup?: (kind: "rect" | "circle" | "arrow" | "freehand" | "note" | null) => void;
  markupColor?: string;
  onChangeMarkupColor?: (color: string) => void;
  /** When writes aren't permitted (anon share link without allow_annotations / read-only role), hide drawing tools. */
  canAnnotate?: boolean;
  showTacHeatmap?: boolean;
  onToggleTacHeatmap?: () => void;
  showBoxOverlay?: boolean;
  onToggleBoxOverlay?: () => void;
  onOpenShare?: () => void;
  hasChain?: boolean;
  /**
   * Called when the user kicks off a capability-fill request. The parent
   * component uses this to start polling /config + /findings so the tool
   * flips from "Load …" to live once Celery completes.
   */
  onCapabilityFillStarted?: (capability: ViewerCapabilityKey) => void;
  /** Toggle the findings sidebar (desktop overlay drawer). Undefined hides the button. */
  onToggleSidebar?: () => void;
  /** Current open/closed state of the sidebar; drives the button's aria-pressed + active styling. */
  sidebarOpen?: boolean;
  // Legacy props for backward compat
  separationMode?: boolean;
  onToggleSeparationMode?: () => void;
  annotationMode?: boolean;
  onToggleAnnotationMode?: () => void;
}

/** Compact icon-only tool button with tooltip */
function ToolButton({
  label,
  icon,
  active,
  onClick,
  activeClass = "bg-white/20 text-white",
  disabled = false,
  loading = false,
  loadLabel,
}: {
  label: string;
  icon: string;
  active: boolean;
  onClick: () => void;
  activeClass?: string;
  disabled?: boolean;
  loading?: boolean;
  loadLabel?: string;
}) {
  const title = loadLabel ?? label;
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`relative rounded p-1.5 text-sm transition-colors ${
        active
          ? activeClass
          : "text-slate-300 hover:bg-white/10 hover:text-white disabled:opacity-40 disabled:hover:bg-transparent"
      }`}
      title={title}
    >
      {icon}
      {loading && (
        <span
          aria-label="Loading"
          className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400"
        />
      )}
    </button>
  );
}

/** Hook: trigger the on-demand capability-fill endpoint and track in-flight state. */
function useCapabilityFill(
  apiBase: string,
  onFillStarted?: (capability: ViewerCapabilityKey) => void,
) {
  const [inflight, setInflight] = useState<Record<string, boolean>>({});

  async function fill(capability: ViewerCapabilityKey): Promise<void> {
    // capability is a compile-time union key of the inflight Record.
    // eslint-disable-next-line security/detect-object-injection
    if (inflight[capability]) return;
    setInflight((prev) => ({ ...prev, [capability]: true }));
    try {
      const resp = await fetch(
        `${apiBase.replace(/\/$/, "")}/capabilities/${encodeURIComponent(capability)}`,
        { method: "POST" },
      );
      if (resp.ok || resp.status === 202) {
        onFillStarted?.(capability);
      }
      // Capability refresh happens when the parent re-fetches /config
      // after the Celery task writes the data. The toolbar just kicks
      // off the request — polling is the parent's concern.
    } finally {
      setInflight((prev) => {
        const next = { ...prev };
        // capability is a compile-time union key.
        // eslint-disable-next-line security/detect-object-injection
        delete next[capability];
        return next;
      });
    }
  }

  return { inflight, fill };
}

function Divider() {
  return <span className="mx-1 h-5 w-px bg-white/20" />;
}

export function ViewerToolbar({
  currentPage,
  pageCount,
  zoom,
  onPageChange,
  onZoomChange,
  jobId,
  fileName,
  config = DEFAULT_VIEWER_CONFIG,
  viewerMode = "normal",
  onToggleMode,
  measureMode = "none",
  onToggleMeasure,
  markupKind = null,
  onToggleMarkup,
  markupColor = "#dc2626",
  onChangeMarkupColor,
  canAnnotate = false,
  showTacHeatmap = false,
  onToggleTacHeatmap,
  showBoxOverlay = false,
  onToggleBoxOverlay,
  onOpenShare,
  hasChain,
  onCapabilityFillStarted,
  onToggleSidebar,
  sidebarOpen = false,
}: ViewerToolbarProps) {
  const { apiBase, readOnly } = useViewerApi();
  const { inflight, fill } = useCapabilityFill(apiBase, onCapabilityFillStarted);

  const bgColor = config.anonymous
    ? "#1e293b"
    : config.brand_primary_color || "#1e293b";

  const caps = config.capabilities || {};
  const capAvailable = (key: ViewerCapabilityKey): boolean =>
    // key is a compile-time ViewerCapabilityKey union.
    // eslint-disable-next-line security/detect-object-injection
    caps[key] !== false; // undefined means "assume present" (engine jobs)
  // Public / read-only viewers never see the "Load" affordance — kicking
  // off analyzer runs is reserved to authenticated users on their own jobs.
  // Tenants whose plan forbids fill-in (Viewer tier) also see no Load buttons.
  const capFillable = (key: ViewerCapabilityKey): boolean =>
    !readOnly &&
    config.capability_fillin_enabled !== false &&
    FILLABLE_CAPABILITIES.includes(key);

  return (
    <div
      className="flex items-center gap-2 overflow-x-auto px-3 py-1.5 text-white scrollbar-none"
      style={{ backgroundColor: bgColor, WebkitOverflowScrolling: "touch" }}
    >
      {/* Findings drawer toggle. Desktop's answer to mobile's
          hamburger — the drawer itself is hidden by default so the
          PDF fills the viewport on first paint; clicking slides the
          findings panel in as an overlay. Only rendered when the
          parent wires a handler, so the mobile top bar (which has
          its own hamburger) isn't double-stamped. */}
      {onToggleSidebar && (
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? "Close findings panel" : "Open findings panel"}
          aria-pressed={sidebarOpen}
          className={`shrink-0 rounded p-1.5 transition-colors ${
            sidebarOpen ? "bg-white/20 text-white" : "text-slate-300 hover:bg-white/10 hover:text-white"
          }`}
          title="Toggle findings panel"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
          </svg>
        </button>
      )}

      {/* Logo — suppressed entirely in anonymous mode so the viewer
          frame leaks no broker OR LintPDF identity. */}
      {!config.anonymous &&
        (config.viewer_logo_url || config.brand_logo_url) && (
          <img
            src={config.viewer_logo_url ?? config.brand_logo_url ?? undefined}
            alt={config.brand_name ?? "Brand"}
            className="h-6 w-auto shrink-0"
          />
        )}
      {config.anonymous && (
        <span className="text-xs font-medium text-slate-200 shrink-0">
          Preflight Report
        </span>
      )}

      {/* File name */}
      {fileName && (
        <span className="max-w-[200px] truncate text-xs font-medium text-slate-200">
          {fileName}
        </span>
      )}

      <Divider />

      {/* Page navigation */}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
          className="rounded p-1 text-sm text-slate-300 hover:bg-white/10 hover:text-white disabled:opacity-40"
          title="Previous page"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <span className="text-xs text-slate-200">
          <input
            type="number"
            min={1}
            max={pageCount}
            value={currentPage}
            onChange={(e) => {
              const p = Number(e.target.value);
              if (p >= 1 && p <= pageCount) onPageChange(p);
            }}
            className="w-10 rounded border border-white/20 bg-white/10 px-1 py-0.5 text-center text-xs text-white outline-none focus:border-white/40"
          />
          <span className="ml-1 text-slate-400">/ {pageCount}</span>
        </span>
        <button
          onClick={() => onPageChange(Math.min(pageCount, currentPage + 1))}
          disabled={currentPage >= pageCount}
          className="rounded p-1 text-sm text-slate-300 hover:bg-white/10 hover:text-white disabled:opacity-40"
          title="Next page"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Zoom */}
      {config.enable_zoom && (
        <>
          <Divider />
          <ZoomControls zoom={zoom} onZoomChange={onZoomChange} compact dark />
        </>
      )}

      <Divider />

      {/* Tool buttons (icon-only with tooltips) */}
      <div className="flex items-center gap-0.5">
        {onToggleMode && (
          <ToolButton
            label="Health Report"
            icon="Health"
            active={viewerMode === "health"}
            onClick={() => onToggleMode("health")}
          />
        )}

        {hasChain && onToggleMode && (
          <ToolButton
            label="Approval Chain"
            icon="Chain"
            active={viewerMode === "chain"}
            onClick={() => onToggleMode("chain")}
          />
        )}

        {config.enable_separations && onToggleMode && (
          capAvailable("separations") ? (
            <ToolButton
              label="Separations"
              icon="CMYK"
              active={viewerMode === "separation"}
              onClick={() => onToggleMode("separation")}
            />
          ) : capFillable("separations") ? (
            <ToolButton
              label="Load Separations"
              loadLabel="Load separations data (runs spot-color analyzer)"
              icon="CMYK+"
              active={false}
              loading={Boolean(inflight["separations"])}
              onClick={() => void fill("separations")}
            />
          ) : null
        )}

        {config.enable_layers && onToggleMode && capAvailable("layers") && (
          <ToolButton
            label="Layers"
            icon="Layers"
            active={viewerMode === "layers"}
            onClick={() => onToggleMode("layers")}
          />
        )}

        {config.enable_tac_heatmap && onToggleTacHeatmap && (
          capAvailable("tac") ? (
            <ToolButton
              label="TAC Heatmap"
              icon="TAC"
              active={showTacHeatmap}
              onClick={onToggleTacHeatmap}
            />
          ) : capFillable("tac") ? (
            <ToolButton
              label="Load TAC Heatmap"
              loadLabel="Load total-area-coverage data (runs ink-coverage analyzer)"
              icon="TAC+"
              active={false}
              loading={Boolean(inflight["tac"])}
              onClick={() => void fill("tac")}
            />
          ) : null
        )}

        {onToggleBoxOverlay && (
          <ToolButton
            label="Trim/Bleed Boxes"
            icon="Boxes"
            active={showBoxOverlay}
            onClick={onToggleBoxOverlay}
          />
        )}

        {/* Measurement tools */}
        {config.enable_measurement && onToggleMeasure && (
          <>
            <Divider />
            <ToolButton
              label="Color Picker"
              icon={"\u{1F9EA}"}
              active={measureMode === "color_picker"}
              onClick={() => onToggleMeasure("color_picker")}
            />
            <ToolButton
              label="Densitometer (C/M/Y/K + TAC)"
              icon={"\u{1F39A}"}
              active={measureMode === "densitometer"}
              onClick={() => onToggleMeasure("densitometer")}
            />
            <ToolButton
              label="Ruler"
              icon={"\u2194"}
              active={measureMode === "ruler"}
              onClick={() => onToggleMeasure("ruler")}
            />
          </>
        )}

        {/* Mark Up — drawing + sticky-note tools (live on main toolbar so
            reviewers can circle issues and leave notes inline). */}
        {canAnnotate && onToggleMarkup && (
          <>
            <Divider />
            <ToolButton
              label="Draw Rectangle"
              icon={"\u25AD"}
              active={markupKind === "rect"}
              onClick={() => onToggleMarkup(markupKind === "rect" ? null : "rect")}
            />
            <ToolButton
              label="Draw Circle"
              icon={"\u25EF"}
              active={markupKind === "circle"}
              onClick={() => onToggleMarkup(markupKind === "circle" ? null : "circle")}
            />
            <ToolButton
              label="Draw Arrow"
              icon={"\u27A4"}
              active={markupKind === "arrow"}
              onClick={() => onToggleMarkup(markupKind === "arrow" ? null : "arrow")}
            />
            <ToolButton
              label="Freehand Pencil"
              icon={"\u270F"}
              active={markupKind === "freehand"}
              onClick={() => onToggleMarkup(markupKind === "freehand" ? null : "freehand")}
            />
            <ToolButton
              label="Sticky Note"
              icon={"\u{1F4CC}"}
              active={markupKind === "note"}
              onClick={() => onToggleMarkup(markupKind === "note" ? null : "note")}
            />
            {/* 6-swatch color palette for the active markup tool. */}
            {onChangeMarkupColor && (
              <div className="ml-1 flex items-center gap-0.5">
                {["#dc2626", "#f59e0b", "#2563eb", "#16a34a", "#0f172a", "#ffffff"].map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => onChangeMarkupColor(c)}
                    title={`Color ${c}`}
                    aria-label={`Markup color ${c}`}
                    className={`h-4 w-4 rounded-sm border transition ${
                      markupColor === c
                        ? "border-white shadow-inner"
                        : "border-white/30 hover:border-white/70"
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* Annotation + Comparison */}
        <Divider />

        {!readOnly && config.enable_annotations && onToggleMode && (
          <ToolButton
            label="Annotate"
            icon={"\u270E"}
            active={viewerMode === "annotation"}
            onClick={() => onToggleMode("annotation")}
          />
        )}

        {!readOnly && config.enable_comparison && onToggleMode && (
          <ToolButton
            label="Compare Versions"
            icon={"\u2194\uFE0F"}
            active={viewerMode === "comparison"}
            onClick={() => onToggleMode("comparison")}
          />
        )}

        {/* Share button */}
        {onOpenShare && (
          <>
            <Divider />
            <button
              onClick={onOpenShare}
              className="flex items-center gap-1 rounded p-1.5 text-xs text-slate-300 hover:bg-white/10 hover:text-white"
              title="Share via Email"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              Share
            </button>
          </>
        )}

        {/* Export links */}
        <Divider />

        {config.enable_html_report_link && (
          <a
            href={`${apiBase.replace(/\/viewer\/.*$/, '/reports/' + jobId)}/html`}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded p-1.5 text-xs text-slate-300 hover:bg-white/10 hover:text-white"
            title="View HTML Report"
          >
            Report
          </a>
        )}
        {config.enable_download && (
          <a
            href={`${apiBase.replace(/\/viewer\/.*$/, '/reports/' + jobId)}/download`}
            className="rounded p-1.5 text-xs text-slate-300 hover:bg-white/10 hover:text-white"
            title="Download PDF"
          >
            PDF
          </a>
        )}
      </div>
    </div>
  );
}
