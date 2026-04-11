"use client";

import type { ViewerConfig } from "./types";
import { useViewerApi } from "./types";

type ViewerMode = "normal" | "separation" | "layers" | "annotation" | "comparison";
type MeasureMode = "none" | "densitometer" | "ruler";

interface MobileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  config: ViewerConfig;
  viewerMode: ViewerMode;
  onToggleMode: (mode: ViewerMode) => void;
  measureMode: MeasureMode;
  onToggleMeasure: (mode: MeasureMode) => void;
  showTacHeatmap: boolean;
  onToggleTacHeatmap: () => void;
  showBoxOverlay: boolean;
  onToggleBoxOverlay: () => void;
  fileName?: string;
  findingSummary: { error: number; warning: number; advisory: number };
}

function DrawerItem({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm text-slate-200 transition-colors hover:bg-slate-800"
    >
      <span className={active ? "font-medium text-white" : ""}>{label}</span>
      {active && (
        <span className="h-2 w-2 rounded-full bg-blue-400" />
      )}
    </button>
  );
}

export function MobileDrawer({
  isOpen,
  onClose,
  config,
  viewerMode,
  onToggleMode,
  measureMode,
  onToggleMeasure,
  showTacHeatmap,
  onToggleTacHeatmap,
  showBoxOverlay,
  onToggleBoxOverlay,
  fileName,
  findingSummary,
}: MobileDrawerProps) {
  const { readOnly } = useViewerApi();

  const handleTool = (fn: () => void) => {
    fn();
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-50 bg-black/50 transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />

      {/* Drawer panel */}
      <div
        className={`fixed inset-y-0 left-0 z-[60] w-[280px] bg-slate-900 shadow-xl transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex h-12 items-center justify-between border-b border-slate-700 px-4">
          <span className="text-sm font-bold text-white">
            {config.brand_name || "LintPDF"}
          </span>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="overflow-y-auto px-2 py-3" style={{ height: "calc(100% - 48px)" }}>
          {/* View Modes */}
          <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            View Modes
          </div>
          {config.enable_separations && (
            <DrawerItem
              label="Ink Separations"
              active={viewerMode === "separation"}
              onClick={() => handleTool(() => onToggleMode("separation"))}
            />
          )}
          {config.enable_layers && (
            <DrawerItem
              label="PDF Layers"
              active={viewerMode === "layers"}
              onClick={() => handleTool(() => onToggleMode("layers"))}
            />
          )}
          {config.enable_annotations && !readOnly && (
            <DrawerItem
              label="Annotations"
              active={viewerMode === "annotation"}
              onClick={() => handleTool(() => onToggleMode("annotation"))}
            />
          )}

          {/* Divider */}
          <div className="my-3 border-t border-slate-700" />

          {/* Tools */}
          <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Tools
          </div>
          {config.enable_tac_heatmap && (
            <DrawerItem
              label="TAC Heatmap"
              active={showTacHeatmap}
              onClick={() => handleTool(onToggleTacHeatmap)}
            />
          )}
          {config.enable_measurement && (
            <>
              <DrawerItem
                label="Measure Distance"
                active={measureMode === "ruler"}
                onClick={() => handleTool(() => onToggleMeasure("ruler"))}
              />
              <DrawerItem
                label="Densitometer"
                active={measureMode === "densitometer"}
                onClick={() => handleTool(() => onToggleMeasure("densitometer"))}
              />
            </>
          )}
          <DrawerItem
            label="Show Boxes (Trim/Bleed)"
            active={showBoxOverlay}
            onClick={() => handleTool(onToggleBoxOverlay)}
          />

          {/* Divider */}
          <div className="my-3 border-t border-slate-700" />

          {/* Info */}
          <div className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Info
          </div>
          {fileName && (
            <div className="px-3 py-1.5 text-xs text-slate-400 truncate">
              {fileName}
            </div>
          )}
          <div className="flex gap-3 px-3 py-1.5 text-xs">
            <span className="text-red-400">{findingSummary.error} errors</span>
            <span className="text-amber-400">{findingSummary.warning} warnings</span>
            <span className="text-blue-400">{findingSummary.advisory} info</span>
          </div>
        </div>
      </div>
    </>
  );
}
