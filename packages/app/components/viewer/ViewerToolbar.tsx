"use client";

import { ZoomControls } from "./ZoomControls";
import type { ViewerConfig } from "./types";
import { DEFAULT_VIEWER_CONFIG, useViewerApi } from "./types";

type ViewerMode = "normal" | "separation" | "layers" | "annotation" | "comparison";
type MeasureMode = "none" | "densitometer" | "ruler";

interface ViewerToolbarProps {
  currentPage: number;
  pageCount: number;
  zoom: number;
  onPageChange: (page: number) => void;
  onZoomChange: (zoom: number) => void;
  jobId: string;
  config?: ViewerConfig;
  viewerMode?: ViewerMode;
  onToggleMode?: (mode: ViewerMode) => void;
  measureMode?: MeasureMode;
  onToggleMeasure?: (mode: MeasureMode) => void;
  showTacHeatmap?: boolean;
  onToggleTacHeatmap?: () => void;
  showBoxOverlay?: boolean;
  onToggleBoxOverlay?: () => void;
  // Legacy props for backward compat
  separationMode?: boolean;
  onToggleSeparationMode?: () => void;
  annotationMode?: boolean;
  onToggleAnnotationMode?: () => void;
}

function ToolButton({
  label,
  active,
  onClick,
  activeClass = "border-primary bg-primary/10 text-primary",
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  activeClass?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded border px-3 py-1 text-sm transition-colors ${
        active ? activeClass : "hover:bg-muted"
      }`}
      title={label}
    >
      {label}
    </button>
  );
}

export function ViewerToolbar({
  currentPage,
  pageCount,
  zoom,
  onPageChange,
  onZoomChange,
  jobId,
  config = DEFAULT_VIEWER_CONFIG,
  viewerMode = "normal",
  onToggleMode,
  measureMode = "none",
  onToggleMeasure,
  showTacHeatmap = false,
  onToggleTacHeatmap,
  showBoxOverlay = false,
  onToggleBoxOverlay,
}: ViewerToolbarProps) {
  const { apiBase, readOnly } = useViewerApi();
  return (
    <div className="flex items-center justify-between border-b bg-background px-4 py-2">
      {/* Left: Brand logo + Page navigation */}
      <div className="flex items-center gap-3">
        {(config.viewer_logo_url || config.brand_logo_url) && (
          <img
            src={config.viewer_logo_url ?? config.brand_logo_url ?? undefined}
            alt={config.brand_name}
            className="h-7 w-auto shrink-0"
          />
        )}
        <button
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
          className="rounded border px-2 py-1 text-sm hover:bg-muted disabled:opacity-40"
          title="Previous page"
        >
          ← Prev
        </button>
        <span className="text-sm">
          Page{" "}
          <input
            type="number"
            min={1}
            max={pageCount}
            value={currentPage}
            onChange={(e) => {
              const p = Number(e.target.value);
              if (p >= 1 && p <= pageCount) onPageChange(p);
            }}
            className="w-12 rounded border px-1 py-0.5 text-center text-sm"
          />{" "}
          of {pageCount}
        </span>
        <button
          onClick={() => onPageChange(Math.min(pageCount, currentPage + 1))}
          disabled={currentPage >= pageCount}
          className="rounded border px-2 py-1 text-sm hover:bg-muted disabled:opacity-40"
          title="Next page"
        >
          Next →
        </button>
      </div>

      {/* Center: Zoom */}
      {config.enable_zoom && (
        <ZoomControls zoom={zoom} onZoomChange={onZoomChange} />
      )}

      {/* Right: Tool buttons */}
      <div className="flex items-center gap-1.5">
        {/* Inspection tools */}
        {config.enable_separations && onToggleMode && (
          <ToolButton
            label="Separations"
            active={viewerMode === "separation"}
            onClick={() => onToggleMode("separation")}
          />
        )}

        {config.enable_layers && onToggleMode && (
          <ToolButton
            label="Layers"
            active={viewerMode === "layers"}
            onClick={() => onToggleMode("layers")}
            activeClass="border-violet-500 bg-violet-500/10 text-violet-600"
          />
        )}

        {config.enable_tac_heatmap && onToggleTacHeatmap && (
          <ToolButton
            label="TAC"
            active={showTacHeatmap}
            onClick={onToggleTacHeatmap}
            activeClass="border-amber-500 bg-amber-500/10 text-amber-600"
          />
        )}

        {onToggleBoxOverlay && (
          <ToolButton
            label="Boxes"
            active={showBoxOverlay}
            onClick={onToggleBoxOverlay}
            activeClass="border-blue-500 bg-blue-500/10 text-blue-600"
          />
        )}

        {/* Measurement tools */}
        {config.enable_measurement && onToggleMeasure && (
          <>
            <span className="mx-0.5 h-4 border-r" />
            <ToolButton
              label="&#128270;"
              active={measureMode === "densitometer"}
              onClick={() => onToggleMeasure("densitometer")}
              activeClass="border-cyan-500 bg-cyan-500/10 text-cyan-600"
            />
            <ToolButton
              label="&#8596;"
              active={measureMode === "ruler"}
              onClick={() => onToggleMeasure("ruler")}
              activeClass="border-green-500 bg-green-500/10 text-green-600"
            />
          </>
        )}

        {/* Annotation + Comparison */}
        <span className="mx-0.5 h-4 border-r" />

        {!readOnly && config.enable_annotations && onToggleMode && (
          <ToolButton
            label="Annotate"
            active={viewerMode === "annotation"}
            onClick={() => onToggleMode("annotation")}
            activeClass="border-violet-500 bg-violet-500/10 text-violet-600"
          />
        )}

        {!readOnly && config.enable_comparison && onToggleMode && (
          <ToolButton
            label="Compare"
            active={viewerMode === "comparison"}
            onClick={() => onToggleMode("comparison")}
            activeClass="border-indigo-500 bg-indigo-500/10 text-indigo-600"
          />
        )}

        {/* Export links */}
        <span className="mx-0.5 h-4 border-r" />

        {config.enable_html_report_link && (
          <a
            href={`${apiBase.replace(/\/viewer\/.*$/, '/reports/' + jobId)}/html`}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded border px-3 py-1 text-sm hover:bg-muted"
          >
            Report
          </a>
        )}
        {config.enable_download && (
          <a
            href={`${apiBase.replace(/\/viewer\/.*$/, '/reports/' + jobId)}/download`}
            className="rounded border px-3 py-1 text-sm hover:bg-muted"
          >
            PDF
          </a>
        )}
      </div>
    </div>
  );
}
