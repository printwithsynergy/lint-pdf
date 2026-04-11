"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ComparisonState, PageInfo, ViewerConfig, ViewerFinding } from "./types";
import { DEFAULT_VIEWER_CONFIG, ViewerApiContext } from "./types";
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

type ViewerMode = "normal" | "separation" | "layers" | "annotation" | "comparison";
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
          setConfig({ ...DEFAULT_VIEWER_CONFIG, ...configData });
          setZoom(configData.default_zoom ?? 100);
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
        <span className="animate-pulse text-muted-foreground">Loading viewer...</span>
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
  const canvasWidth = currentPageInfo ? Math.round(currentPageInfo.width_pts * (zoom / 100)) : 0;
  const canvasHeight = currentPageInfo ? Math.round(currentPageInfo.height_pts * (zoom / 100)) : 0;

  const ctxValue = { apiBase, jobApiBase, readOnly };

  return (
    <ViewerApiContext.Provider value={ctxValue}>
    <div className={`flex h-[calc(100vh-4rem)] flex-col ${config.dark_mode ? "dark bg-neutral-900" : ""}`}>
      {/* Verdict bar */}
      <VerdictBar jobId={jobId} config={config} />

      {/* Toolbar */}
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

      {/* Main content: thumbnails | canvas | panel */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Page thumbnails */}
        {config.enable_page_thumbnails && (
          <div className="w-28 shrink-0 border-r bg-muted/30 overflow-y-auto">
            <PageNavigator
              pages={pages}
              currentPage={currentPage}
              findings={findings}
              jobId={jobId}
              onPageChange={setCurrentPage}
            />
          </div>
        )}

        {/* Center: Page canvas */}
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

        {/* Right: Context panel */}
        <div className="w-80 shrink-0 border-l bg-background overflow-hidden overflow-y-auto">
          {viewerMode === "annotation" ? (
            <AnnotationThread jobId={jobId} onJumpToPage={setCurrentPage} />
          ) : viewerMode === "separation" ? (
            <SeparationPanel
              jobId={jobId}
              enabledChannels={enabledChannels}
              onToggleChannel={handleToggleChannel}
              onSetAllChannels={handleSetAllChannels}
            />
          ) : viewerMode === "layers" ? (
            <LayerPanel
              jobId={jobId}
              enabledLayers={enabledLayers}
              onToggleLayer={handleToggleLayer}
              onSetAllLayers={handleSetAllLayers}
            />
          ) : viewerMode === "comparison" ? (
            <ComparisonPanel
              jobId={jobId}
              comparison={comparison}
              onStartComparison={setComparison}
              comparisonMode={comparisonMode}
              onModeChange={setComparisonMode}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
            />
          ) : config.enable_findings_panel ? (
            <FindingsPanel
              findings={findings}
              selectedFinding={selectedFinding}
              onSelectFinding={handleSelectFinding}
              currentPage={currentPage}
            />
          ) : null}
        </div>
      </div>
    </div>
    </ViewerApiContext.Provider>
  );
}
