"use client";

import { ZoomControls } from "./ZoomControls";
import type { ViewerConfig } from "./types";
import { DEFAULT_VIEWER_CONFIG, useViewerApi } from "./types";

type ViewerMode = "normal" | "separation" | "layers" | "annotation" | "comparison" | "health" | "chain";
type MeasureMode = "none" | "densitometer" | "ruler";

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
  showTacHeatmap?: boolean;
  onToggleTacHeatmap?: () => void;
  showBoxOverlay?: boolean;
  onToggleBoxOverlay?: () => void;
  onOpenShare?: () => void;
  hasChain?: boolean;
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
}: {
  label: string;
  icon: string;
  active: boolean;
  onClick: () => void;
  activeClass?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded p-1.5 text-sm transition-colors ${
        active ? activeClass : "text-slate-300 hover:bg-white/10 hover:text-white"
      }`}
      title={label}
    >
      {icon}
    </button>
  );
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
  showTacHeatmap = false,
  onToggleTacHeatmap,
  showBoxOverlay = false,
  onToggleBoxOverlay,
  onOpenShare,
  hasChain,
}: ViewerToolbarProps) {
  const { apiBase, readOnly } = useViewerApi();

  const bgColor = config.brand_primary_color || "#1e293b";

  return (
    <div
      className="flex items-center gap-2 overflow-x-auto px-3 py-1.5 text-white scrollbar-none"
      style={{ backgroundColor: bgColor, WebkitOverflowScrolling: "touch" }}
    >
      {/* Logo */}
      {(config.viewer_logo_url || config.brand_logo_url) && (
        <img
          src={config.viewer_logo_url ?? config.brand_logo_url ?? undefined}
          alt={config.brand_name}
          className="h-6 w-auto shrink-0"
        />
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
          <ToolButton
            label="Separations"
            icon="CMYK"
            active={viewerMode === "separation"}
            onClick={() => onToggleMode("separation")}
          />
        )}

        {config.enable_layers && onToggleMode && (
          <ToolButton
            label="Layers"
            icon="Layers"
            active={viewerMode === "layers"}
            onClick={() => onToggleMode("layers")}
          />
        )}

        {config.enable_tac_heatmap && onToggleTacHeatmap && (
          <ToolButton
            label="TAC Heatmap"
            icon="TAC"
            active={showTacHeatmap}
            onClick={onToggleTacHeatmap}
          />
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
              label="Densitometer"
              icon={"\u{1F50D}"}
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
