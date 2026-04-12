"use client";

import { useCallback, useEffect, useRef, useState, useMemo } from "react";
import type { ComparisonState, PageInfo, ViewerConfig, ViewerFinding } from "./types";
import { DEFAULT_VIEWER_CONFIG, DEFAULT_DPI, ViewerApiContext } from "./types";
import { PageCanvas } from "./PageCanvas";
import { FindingsPanel } from "./FindingsPanel";
import { PageNavigator } from "./PageNavigator";
import { ViewerToolbar } from "./ViewerToolbar";
import { SeparationPanel } from "./SeparationPanel";
import { SeparationCanvas } from "./SeparationCanvas";
import { TACHeatmapOverlay } from "./TACHeatmapOverlay";
import { AnnotationCanvas } from "./AnnotationCanvas";
import { AnnotationToolbar } from "./AnnotationToolbar";
import type { AnnotationTool } from "./AnnotationToolbar";
import { AnnotationThread } from "./AnnotationThread";
import { DensitometerTool } from "./DensitometerTool";
import { MeasureTool } from "./MeasureTool";
import { BoxOverlay } from "./BoxOverlay";
import { LayerPanel } from "./LayerPanel";
import { VerdictBar } from "./VerdictBar";
import { ComparisonPanel } from "./ComparisonPanel";
import { MobileBottomSheet } from "./MobileBottomSheet";
import type { SnapPosition } from "./MobileBottomSheet";
import { MobileDrawer } from "./MobileDrawer";
import { ShareDialog } from "./ShareDialog";

type ViewerMode = "normal" | "separation" | "layers" | "annotation" | "comparison" | "health";
type MeasureMode = "none" | "densitometer" | "ruler";

interface PdfViewerProps {
  jobId: string;
  /** When set, the viewer uses token-based public proxy routes (read-only). */
  publicToken?: string;
}

export function PdfViewer({ jobId, publicToken }: PdfViewerProps) {
  const readOnly = !!publicToken;
  const apiBase = publicToken
    ? `/api/lintpdf/viewer/public/${publicToken}`
    : `/api/lintpdf/viewer/${jobId}`;
  const jobApiBase = publicToken
    ? `/api/lintpdf/viewer/public/${publicToken}`
    : `/api/lintpdf/jobs/${jobId}`;
  const [pages, setPages] = useState<PageInfo[]>([]);
  const [findings, setFindings] = useState<ViewerFinding[]>([]);
  const [config, setConfig] = useState<ViewerConfig>(DEFAULT_VIEWER_CONFIG);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [selectedFinding, setSelectedFinding] = useState<ViewerFinding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Mobile detection (SSR-safe: check window width on first client render)
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth < 768 : false,
  );
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [bottomSheetSnap, setBottomSheetSnap] = useState<SnapPosition>("collapsed");
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // Auto-expand bottom sheet when a panel-mode is selected on mobile
  const handleExpandSheet = useCallback(() => {
    setBottomSheetSnap("half");
  }, []);

  // Collapsible thumbnails (for left panel header)
  const [thumbnailsExpanded, setThumbnailsExpanded] = useState(false);

  // Mode states (mutually exclusive main modes)
  const [viewerMode, setViewerMode] = useState<ViewerMode>("normal");
  const [measureMode, setMeasureMode] = useState<MeasureMode>("none");
  const [showTacHeatmap, setShowTacHeatmap] = useState(false);
  const [showBoxOverlay, setShowBoxOverlay] = useState(false);

  // Separation state
  const [enabledChannels, setEnabledChannels] = useState<Set<string>>(
    new Set(["Cyan", "Magenta", "Yellow", "Black"]),
  );
  const [allChannelNames, setAllChannelNames] = useState<string[]>([]);

  // Layer state
  const [enabledLayers, setEnabledLayers] = useState<Set<number>>(new Set());
  const [allLayerIndices, setAllLayerIndices] = useState<number[]>([]);

  // Annotation state
  const [annotationTool, setAnnotationTool] = useState<AnnotationTool>("pointer");
  const [strokeColor, setStrokeColor] = useState("#ef4444");
  const [annotationSaving, setAnnotationSaving] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const annotationCanvasRef = useRef<HTMLCanvasElement>(null);

  // Comparison state
  const [comparison, setComparison] = useState<ComparisonState | null>(null);
  const [comparisonMode, setComparisonMode] = useState<"ab" | "side-by-side" | "overlay">("ab");
  const [showVersionB, setShowVersionB] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Findings summary for mobile bottom sheet
  const findingsSummary = useMemo(() => {
    const counts = { error: 0, warning: 0, advisory: 0 };
    for (const f of findings) counts[f.severity]++;
    return counts;
  }, [findings]);

  // Health score
  const health = useMemo(() => {
    const { error, warning, advisory } = findingsSummary;
    const score = Math.max(0, Math.min(100, Math.round(100 - error * 10 - warning * 3 - advisory * 0.5)));
    const grade = score >= 90 ? "A" : score >= 80 ? "B" : score >= 70 ? "C" : score >= 60 ? "D" : "F";
    const color = score >= 80 ? "#22c55e" : score >= 70 ? "#f59e0b" : "#ef4444";
    return { score, grade, color };
  }, [findingsSummary]);

  // Load pages + findings + config on mount
  useEffect(() => {
    async function load() {
      try {
        const [pagesResp, jobResp, configResp] = await Promise.all([
          fetch(`${apiBase}/pages`),
          fetch(publicToken ? `${apiBase}/findings` : `/api/lintpdf/jobs/${jobId}`),
          fetch(`${apiBase}/config`),
        ]);

        if (!pagesResp.ok) throw new Error("Failed to load page data");
        if (!jobResp.ok) throw new Error("Failed to load job data");

        const pagesData = await pagesResp.json();
        const jobData = await jobResp.json();

        setPages(pagesData.pages ?? []);
        setFindings(jobData.findings ?? []);

        if (configResp.ok) {
          const configData = await configResp.json();
          // Filter out null values so API nulls don't override defaults
          // (e.g., brand_logo_url: null would erase the default logo)
          const filtered = Object.fromEntries(
            Object.entries(configData).filter(([, v]) => v != null),
          );
          setConfig({ ...DEFAULT_VIEWER_CONFIG, ...filtered });

          // Auto-fit zoom on mobile: fit page width to screen
          const firstPage = (pagesData.pages ?? [])[0];
          if (window.innerWidth < 768 && firstPage) {
            const ptsToPixels = 150 / 72; // DEFAULT_DPI / 72
            const pagePixelWidth = firstPage.width_pts * ptsToPixels;
            const fitZoom = Math.round(((window.innerWidth - 16) / pagePixelWidth) * 100);
            setZoom(Math.max(25, Math.min(200, fitZoom)));
          } else {
            setZoom(configData.default_zoom ?? 100);
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load viewer");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [jobId, apiBase, publicToken]);

  // Navigate to a finding
  const handleSelectFinding = useCallback(
    (finding: ViewerFinding) => {
      setSelectedFinding(finding);
      if (finding.page_num && finding.page_num !== currentPage) {
        setCurrentPage(finding.page_num);
      }
    },
    [currentPage],
  );

  // Load channel names when separation mode is first enabled
  useEffect(() => {
    if (viewerMode !== "separation" || allChannelNames.length > 0) return;
    fetch(`${apiBase}/separations`)
      .then((r) => r.json())
      .then((data) => {
        const names = (data.channels ?? []).map((c: { name: string }) => c.name);
        setAllChannelNames(names);
        setEnabledChannels(new Set(names));
      })
      .catch(() => {});
  }, [viewerMode, allChannelNames.length, apiBase]);

  // Load layer list when layer mode is first enabled
  useEffect(() => {
    if (viewerMode !== "layers" || allLayerIndices.length > 0) return;
    fetch(`${apiBase}/layers`)
      .then((r) => r.json())
      .then((data) => {
        const indices = (data.layers ?? []).map((l: { ocg_index: number }) => l.ocg_index);
        setAllLayerIndices(indices);
        setEnabledLayers(new Set(indices));
      })
      .catch(() => {});
  }, [viewerMode, allLayerIndices.length, apiBase]);

  const handleToggleChannel = useCallback((channel: string) => {
    setEnabledChannels((prev) => {
      const next = new Set(prev);
      if (next.has(channel)) next.delete(channel);
      else next.add(channel);
      return next;
    });
  }, []);

  const handleSetAllChannels = useCallback(
    (enabled: boolean) => {
      setEnabledChannels(enabled ? new Set(allChannelNames) : new Set());
    },
    [allChannelNames],
  );

  const handleToggleLayer = useCallback((ocgIndex: number) => {
    setEnabledLayers((prev) => {
      const next = new Set(prev);
      if (next.has(ocgIndex)) next.delete(ocgIndex);
      else next.add(ocgIndex);
      return next;
    });
  }, []);

  const handleSetAllLayers = useCallback(
    (enabled: boolean) => {
      setEnabledLayers(enabled ? new Set(allLayerIndices) : new Set());
    },
    [allLayerIndices],
  );

  const handleAnnotationUndo = useCallback(() => {
    const el = annotationCanvasRef.current as any;
    el?.__annotationUndo?.();
  }, []);

  const handleAnnotationRedo = useCallback(() => {
    const el = annotationCanvasRef.current as any;
    el?.__annotationRedo?.();
  }, []);

  const handleHistoryChange = useCallback((undo: boolean, redo: boolean) => {
    setCanUndo(undo);
    setCanRedo(redo);
  }, []);

  // Mode toggles
  const toggleMode = useCallback((mode: ViewerMode) => {
    setViewerMode((prev) => (prev === mode ? "normal" : mode));
    setMeasureMode("none");
  }, []);

  const toggleMeasure = useCallback((mode: MeasureMode) => {
    setMeasureMode((prev) => (prev === mode ? "none" : mode));
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") {
        e.preventDefault();
        setCurrentPage((p) => Math.min(pages.length, p + 1));
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        setCurrentPage((p) => Math.max(1, p - 1));
      } else if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        setZoom((z) => Math.min(400, z + 25));
      } else if (e.key === "-") {
        e.preventDefault();
        setZoom((z) => Math.max(25, z - 25));
      } else if (e.key === "Escape") {
        setMeasureMode("none");
        if (viewerMode !== "normal") setViewerMode("normal");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pages.length, viewerMode]);

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <svg className="h-10 w-10 animate-spin text-primary" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
          <span className="text-sm text-muted-foreground">Preparing viewer</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="text-center">
          <p className="text-destructive">{error}</p>
          <a
            href={`/dashboard/preflight/${jobId}`}
            className="mt-2 inline-block text-sm text-primary underline"
          >
            Back to job details
          </a>
        </div>
      </div>
    );
  }

  const currentPageInfo = pages.find((p) => p.page_num === currentPage);
  const ptsToPixels = DEFAULT_DPI / 72;
  const canvasWidth = currentPageInfo ? Math.round(currentPageInfo.width_pts * ptsToPixels * (zoom / 100)) : 0;
  const canvasHeight = currentPageInfo ? Math.round(currentPageInfo.height_pts * ptsToPixels * (zoom / 100)) : 0;

  const ctxValue = { apiBase, jobApiBase, readOnly };

  // Determine what to render in the left panel
  const renderLeftPanel = () => {
    if (viewerMode === "health") {
      return (
        <div className="flex flex-col gap-4 p-4 text-slate-200">
          {/* Health gauge */}
          <div className="flex items-center gap-4">
            <div
              className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border-[6px]"
              style={{ borderColor: health.color }}
            >
              <div className="text-center">
                <div className="text-2xl font-extrabold leading-none" style={{ color: health.color }}>{health.score}</div>
                <div className="text-[10px] text-slate-500">/100</div>
              </div>
            </div>
            <div>
              <div className="text-lg font-bold" style={{ color: health.color }}>Grade {health.grade}</div>
              <div className="text-xs text-slate-400">{config.enable_findings_panel ? `${findingsSummary.error + findingsSummary.warning + findingsSummary.advisory} total findings` : ""}</div>
            </div>
          </div>

          {/* Finding breakdown bars */}
          <div className="space-y-2">
            {([
              { label: "Errors", count: findingsSummary.error, color: "#ef4444", max: Math.max(findingsSummary.error, findingsSummary.warning, findingsSummary.advisory, 1) },
              { label: "Warnings", count: findingsSummary.warning, color: "#f59e0b", max: Math.max(findingsSummary.error, findingsSummary.warning, findingsSummary.advisory, 1) },
              { label: "Advisory", count: findingsSummary.advisory, color: "#3b82f6", max: Math.max(findingsSummary.error, findingsSummary.warning, findingsSummary.advisory, 1) },
            ] as const).map(({ label, count, color, max }) => (
              <div key={label}>
                <div className="mb-0.5 flex items-center justify-between text-xs">
                  <span className="text-slate-400">{label}</span>
                  <span className="font-bold" style={{ color }}>{count}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full transition-all" style={{ width: `${(count / max) * 100}%`, backgroundColor: color }} />
                </div>
              </div>
            ))}
          </div>

          {/* File info */}
          <div className="space-y-1 border-t border-slate-700 pt-3 text-xs text-slate-400">
            <div><span className="text-slate-500">Pages:</span> {pages.length}</div>
            <div><span className="text-slate-500">Profile:</span> {config.brand_name}</div>
          </div>

          {/* Verdict */}
          <div className="rounded-lg border border-slate-700 p-3 text-center">
            <div className={`text-lg font-extrabold ${findingsSummary.error > 0 ? "text-red-400" : "text-green-400"}`}>
              {findingsSummary.error > 0 ? "FAIL" : "PASS"}
            </div>
            <div className="text-[10px] text-slate-500">Auto verdict from preflight</div>
          </div>
        </div>
      );
    }
    if (viewerMode === "annotation") {
      return <AnnotationThread jobId={jobId} onJumpToPage={setCurrentPage} />;
    }
    if (viewerMode === "separation") {
      return (
        <SeparationPanel
          jobId={jobId}
          enabledChannels={enabledChannels}
          onToggleChannel={handleToggleChannel}
          onSetAllChannels={handleSetAllChannels}
        />
      );
    }
    if (viewerMode === "layers") {
      return (
        <LayerPanel
          jobId={jobId}
          enabledLayers={enabledLayers}
          onToggleLayer={handleToggleLayer}
          onSetAllLayers={handleSetAllLayers}
        />
      );
    }
    if (viewerMode === "comparison") {
      return (
        <ComparisonPanel
          jobId={jobId}
          comparison={comparison}
          onStartComparison={setComparison}
          comparisonMode={comparisonMode}
          onModeChange={setComparisonMode}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />
      );
    }
    if (config.enable_findings_panel) {
      return (
        <>
          {/* Collapsible horizontal page thumbnails strip */}
          {config.enable_page_thumbnails && (
            <div className="shrink-0 border-b border-slate-700">
              <button
                onClick={() => setThumbnailsExpanded((v) => !v)}
                className="flex w-full items-center justify-between px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200"
              >
                <span>Pages ({pages.length})</span>
                <svg
                  className={`h-3.5 w-3.5 transition-transform ${thumbnailsExpanded ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {thumbnailsExpanded && (
                <div className="flex gap-1.5 overflow-x-auto px-3 pb-2">
                  <PageNavigator
                    pages={pages}
                    currentPage={currentPage}
                    findings={findings}
                    jobId={jobId}
                    onPageChange={setCurrentPage}
                    horizontal
                  />
                </div>
              )}
            </div>
          )}
          <FindingsPanel
            findings={findings}
            selectedFinding={selectedFinding}
            onSelectFinding={handleSelectFinding}
            currentPage={currentPage}
          />
        </>
      );
    }
    return null;
  };

  const summaryNode = (
    <div className="flex items-center gap-3 text-xs font-medium">
      <span className="text-red-400">{findingsSummary.error} errors</span>
      <span className="text-amber-400">{findingsSummary.warning} warnings</span>
      <span className="text-blue-400">{findingsSummary.advisory} advisory</span>
    </div>
  );

  return (
    <ViewerApiContext.Provider value={ctxValue}>
    <div className={`flex h-[calc(100vh-4rem)] flex-col ${config.dark_mode ? "dark bg-neutral-900" : ""}`}>
      {/* Verdict bar */}
      <VerdictBar jobId={jobId} config={config} />

      {isMobile ? (
        <>
          {/* ── MOBILE LAYOUT ── */}
          {/* Compact top bar */}
          <div
            className="flex h-11 shrink-0 items-center justify-between gap-1 px-2 text-white"
            style={{ backgroundColor: config.brand_primary_color || "#1e293b" }}
          >
            <button onClick={() => setDrawerOpen(true)} className="shrink-0 rounded p-1.5 hover:bg-white/10">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Active mode badge */}
            {viewerMode !== "normal" && (
              <span className="shrink-0 rounded-full bg-blue-500/30 px-1.5 py-0.5 text-[10px] font-bold text-blue-300">
                {viewerMode === "separation" ? "CMYK" : viewerMode === "layers" ? "LAYERS" : viewerMode === "annotation" ? "ANNOTATE" : viewerMode === "health" ? "HEALTH" : "COMPARE"}
              </span>
            )}
            {(showTacHeatmap || measureMode !== "none") && (
              <span className="shrink-0 rounded-full bg-green-500/30 px-1.5 py-0.5 text-[10px] font-bold text-green-300">
                {showTacHeatmap ? "TAC" : measureMode === "ruler" ? "RULER" : "DENSITY"}
              </span>
            )}

            {/* Page navigation */}
            <div className="flex items-center gap-1 text-sm">
              <button onClick={() => setCurrentPage((p) => Math.max(1, p - 1))} className="p-1 hover:bg-white/10 rounded">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path d="M15 19l-7-7 7-7" /></svg>
              </button>
              <span className="min-w-[2.5rem] text-center text-xs font-medium">{currentPage}/{pages.length}</span>
              <button onClick={() => setCurrentPage((p) => Math.min(pages.length, p + 1))} className="p-1 hover:bg-white/10 rounded">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path d="M9 5l7 7-7 7" /></svg>
              </button>
            </div>

            {/* Zoom controls */}
            <div className="flex shrink-0 items-center gap-0.5">
              <button onClick={() => setZoom((z) => Math.max(25, z - 25))} className="rounded p-1 text-xs hover:bg-white/10">
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path d="M5 12h14" /></svg>
              </button>
              <span className="min-w-[2rem] text-center text-[10px] font-medium">{zoom}%</span>
              <button onClick={() => setZoom((z) => Math.min(400, z + 25))} className="rounded p-1 text-xs hover:bg-white/10">
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path d="M12 5v14M5 12h14" /></svg>
              </button>
            </div>
          </div>

          {/* Full-screen canvas */}
          <div className="flex-1 overflow-auto bg-neutral-800">
            <div className="flex min-h-full items-start justify-center p-2 pb-20">
              {currentPageInfo && (
                <div className="relative">
                  {viewerMode === "separation" ? (
                    <SeparationCanvas jobId={jobId} pageNum={currentPage} enabledChannels={enabledChannels} allChannels={allChannelNames} width={canvasWidth} height={canvasHeight} />
                  ) : (
                    <PageCanvas jobId={jobId} page={currentPageInfo} zoom={zoom} findings={findings} selectedFinding={selectedFinding} onFindingClick={handleSelectFinding} onZoomChange={measureMode === "none" ? setZoom : undefined} onPageChange={measureMode === "none" ? (d) => setCurrentPage((p) => Math.max(1, Math.min(pages.length, p + d))) : undefined} />
                  )}

                  {/* Annotation overlay */}
                  {viewerMode === "annotation" && currentPageInfo && (
                    <AnnotationCanvas
                      jobId={jobId}
                      pageNum={currentPage}
                      width={canvasWidth}
                      height={canvasHeight}
                      activeTool={annotationTool}
                      strokeColor={strokeColor}
                      onSavingChange={setAnnotationSaving}
                      onHistoryChange={handleHistoryChange}
                    />
                  )}

                  {showTacHeatmap && currentPageInfo && (
                    <TACHeatmapOverlay jobId={jobId} pageNum={currentPage} width={canvasWidth} height={canvasHeight} tacLimit={config.default_tac_limit} />
                  )}
                  {showBoxOverlay && currentPageInfo && (
                    <BoxOverlay page={currentPageInfo} canvasWidth={canvasWidth} canvasHeight={canvasHeight} />
                  )}
                  {measureMode === "densitometer" && currentPageInfo && (
                    <DensitometerTool jobId={jobId} pageNum={currentPage} pageWidthPts={currentPageInfo.width_pts} pageHeightPts={currentPageInfo.height_pts} canvasWidth={canvasWidth} canvasHeight={canvasHeight} />
                  )}
                  {measureMode === "ruler" && currentPageInfo && (
                    <MeasureTool pageWidthPts={currentPageInfo.width_pts} pageHeightPts={currentPageInfo.height_pts} canvasWidth={canvasWidth} canvasHeight={canvasHeight} />
                  )}

                  {/* Comparison diff overlay */}
                  {viewerMode === "comparison" && comparison && comparisonMode === "overlay" && (
                    <img
                      src={`/api/lintpdf/viewer/compare/${comparison.comparison_id}/pages/${currentPage}/diff`}
                      alt="Difference overlay"
                      className="pointer-events-none absolute inset-0"
                      style={{ width: canvasWidth, height: canvasHeight, opacity: 0.7 }}
                    />
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Mobile annotation toolbar */}
          {viewerMode === "annotation" && !readOnly && (
            <div className="shrink-0 overflow-x-auto border-t border-slate-700 bg-slate-900 px-2 py-1.5">
              <div className="flex items-center gap-1 min-w-max">
                {/* Tool buttons */}
                {([
                  { id: "pointer" as AnnotationTool, label: "Select", icon: "\u25B3" },
                  { id: "pen" as AnnotationTool, label: "Pen", icon: "\u270E" },
                  { id: "arrow" as AnnotationTool, label: "Arrow", icon: "\u2192" },
                  { id: "rectangle" as AnnotationTool, label: "Rect", icon: "\u25A1" },
                  { id: "ellipse" as AnnotationTool, label: "Ellipse", icon: "\u25CB" },
                  { id: "text" as AnnotationTool, label: "Text", icon: "T" },
                  { id: "highlight" as AnnotationTool, label: "Highlight", icon: "\u2588" },
                ]).map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => setAnnotationTool(tool.id)}
                    className={`rounded px-2 py-1.5 text-sm font-medium transition-colors ${
                      annotationTool === tool.id
                        ? "bg-blue-600 text-white"
                        : "text-slate-300 hover:bg-slate-800"
                    }`}
                    title={tool.label}
                  >
                    {tool.icon}
                  </button>
                ))}
                <span className="mx-1 h-5 w-px bg-slate-700" />
                {/* Color swatches */}
                {["#ef4444", "#f59e0b", "#22c55e", "#3b82f6", "#8b5cf6", "#000000", "#ffffff"].map((color) => (
                  <button
                    key={color}
                    onClick={() => setStrokeColor(color)}
                    className={`h-5 w-5 shrink-0 rounded-full border-2 transition-transform ${
                      strokeColor === color ? "scale-125 border-blue-400" : "border-transparent hover:scale-110"
                    }`}
                    style={{ backgroundColor: color }}
                  />
                ))}
                <span className="mx-1 h-5 w-px bg-slate-700" />
                {/* Undo/Redo */}
                <button onClick={handleAnnotationUndo} disabled={!canUndo} className="rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-40">Undo</button>
                <button onClick={handleAnnotationRedo} disabled={!canRedo} className="rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-40">Redo</button>
                {annotationSaving && <span className="text-[10px] text-slate-500">Saving...</span>}
              </div>
            </div>
          )}

          {/* Bottom sheet with findings */}
          <MobileBottomSheet summary={summaryNode} snap={bottomSheetSnap} onSnapChange={setBottomSheetSnap}>
            {renderLeftPanel()}
          </MobileBottomSheet>

          {/* Hamburger drawer */}
          <MobileDrawer
            isOpen={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            config={config}
            viewerMode={viewerMode}
            onToggleMode={toggleMode}
            measureMode={measureMode}
            onToggleMeasure={toggleMeasure}
            showTacHeatmap={showTacHeatmap}
            onToggleTacHeatmap={() => setShowTacHeatmap((v) => !v)}
            showBoxOverlay={showBoxOverlay}
            onToggleBoxOverlay={() => setShowBoxOverlay((v) => !v)}
            findingSummary={findingsSummary}
            zoom={zoom}
            onZoomChange={setZoom}
            jobId={jobId}
            onExpandSheet={handleExpandSheet}
            onOpenShare={publicToken ? () => setShareOpen(true) : undefined}
          />
        </>
      ) : (
        <>
      {/* ── DESKTOP LAYOUT ── */}
      {/* Toolbar at top */}
      <ViewerToolbar
        currentPage={currentPage}
        pageCount={pages.length}
        zoom={zoom}
        onPageChange={setCurrentPage}
        onZoomChange={setZoom}
        jobId={jobId}
        config={config}
        viewerMode={viewerMode}
        onToggleMode={toggleMode}
        measureMode={measureMode}
        onToggleMeasure={toggleMeasure}
        showTacHeatmap={showTacHeatmap}
        onToggleTacHeatmap={() => setShowTacHeatmap((v) => !v)}
        showBoxOverlay={showBoxOverlay}
        onToggleBoxOverlay={() => setShowBoxOverlay((v) => !v)}
        onOpenShare={publicToken ? () => setShareOpen(true) : undefined}
      />

      {/* Annotation toolbar (hidden in read-only / public mode) */}
      {viewerMode === "annotation" && !readOnly && (
        <div className="flex justify-center border-b bg-muted/30 px-4 py-1">
          <AnnotationToolbar
            activeTool={annotationTool}
            onToolChange={setAnnotationTool}
            strokeColor={strokeColor}
            onStrokeColorChange={setStrokeColor}
            onUndo={handleAnnotationUndo}
            onRedo={handleAnnotationRedo}
            canUndo={canUndo}
            canRedo={canRedo}
            saving={annotationSaving}
          />
        </div>
      )}

      {/* Main content: LEFT panel | RIGHT canvas */}
      <div className="flex flex-1 overflow-hidden">
        {/* LEFT: Findings / context panel (desktop only) */}
        {!isMobile && (
          <div className="flex w-[280px] shrink-0 flex-col border-r border-slate-700 bg-slate-900 overflow-hidden">
            {renderLeftPanel()}
          </div>
        )}

        {/* RIGHT: Page canvas */}
        <div ref={scrollRef} className="flex-1 overflow-auto bg-neutral-800 p-4">
          <div className="flex justify-center">
            {currentPageInfo && (
              <div className="relative">
                {viewerMode === "separation" ? (
                  <SeparationCanvas
                    jobId={jobId}
                    pageNum={currentPage}
                    enabledChannels={enabledChannels}
                    allChannels={allChannelNames}
                    width={canvasWidth}
                    height={canvasHeight}
                  />
                ) : (
                  <PageCanvas
                    jobId={jobId}
                    page={currentPageInfo}
                    zoom={zoom}
                    findings={findings}
                    selectedFinding={selectedFinding}
                    onFindingClick={handleSelectFinding}
                  />
                )}

                {/* Annotation overlay */}
                {viewerMode === "annotation" && currentPageInfo && (
                  <AnnotationCanvas
                    jobId={jobId}
                    pageNum={currentPage}
                    width={canvasWidth}
                    height={canvasHeight}
                    activeTool={annotationTool}
                    strokeColor={strokeColor}
                    onSavingChange={setAnnotationSaving}
                    onHistoryChange={handleHistoryChange}
                  />
                )}

                {/* TAC heatmap overlay */}
                {showTacHeatmap && currentPageInfo && (
                  <TACHeatmapOverlay
                    jobId={jobId}
                    pageNum={currentPage}
                    width={canvasWidth}
                    height={canvasHeight}
                    tacLimit={config.default_tac_limit}
                  />
                )}

                {/* Box overlay (trim/bleed/crop) */}
                {showBoxOverlay && currentPageInfo && (
                  <BoxOverlay
                    page={currentPageInfo}
                    canvasWidth={canvasWidth}
                    canvasHeight={canvasHeight}
                  />
                )}

                {/* Densitometer tool overlay */}
                {measureMode === "densitometer" && currentPageInfo && (
                  <DensitometerTool
                    jobId={jobId}
                    pageNum={currentPage}
                    pageWidthPts={currentPageInfo.width_pts}
                    pageHeightPts={currentPageInfo.height_pts}
                    canvasWidth={canvasWidth}
                    canvasHeight={canvasHeight}
                  />
                )}

                {/* Ruler tool overlay */}
                {measureMode === "ruler" && currentPageInfo && (
                  <MeasureTool
                    pageWidthPts={currentPageInfo.width_pts}
                    pageHeightPts={currentPageInfo.height_pts}
                    canvasWidth={canvasWidth}
                    canvasHeight={canvasHeight}
                  />
                )}

                {/* Comparison diff overlay */}
                {viewerMode === "comparison" && comparison && comparisonMode === "overlay" && (
                  <img
                    src={`/api/lintpdf/viewer/compare/${comparison.comparison_id}/pages/${currentPage}/diff`}
                    alt="Difference overlay"
                    className="pointer-events-none absolute inset-0"
                    style={{ width: canvasWidth, height: canvasHeight, opacity: 0.7 }}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      </>
      )}
    </div>
    {publicToken && (
      <ShareDialog
        isOpen={shareOpen}
        onClose={() => setShareOpen(false)}
        token={publicToken}
        viewerUrl={typeof window !== "undefined" ? window.location.href.split("?")[0] ?? "" : ""}
      />
    )}
    </ViewerApiContext.Provider>
  );
}
