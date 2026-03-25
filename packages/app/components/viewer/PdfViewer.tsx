"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PageInfo, ViewerFinding } from "./types";
import { PageCanvas } from "./PageCanvas";
import { FindingsPanel } from "./FindingsPanel";
import { PageNavigator } from "./PageNavigator";
import { ViewerToolbar } from "./ViewerToolbar";
import { SeparationPanel } from "./SeparationPanel";
import { SeparationCanvas } from "./SeparationCanvas";
import { TACHeatmapOverlay } from "./TACHeatmapOverlay";

interface PdfViewerProps {
  jobId: string;
}

export function PdfViewer({ jobId }: PdfViewerProps) {
  const [pages, setPages] = useState<PageInfo[]>([]);
  const [findings, setFindings] = useState<ViewerFinding[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [selectedFinding, setSelectedFinding] = useState<ViewerFinding | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [separationMode, setSeparationMode] = useState(false);
  const [enabledChannels, setEnabledChannels] = useState<Set<string>>(
    new Set(["Cyan", "Magenta", "Yellow", "Black"]),
  );
  const [allChannelNames, setAllChannelNames] = useState<string[]>([]);
  const [showTacHeatmap, setShowTacHeatmap] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load pages + findings on mount
  useEffect(() => {
    async function load() {
      try {
        const [pagesResp, jobResp] = await Promise.all([
          fetch(`/api/lintpdf/viewer/${jobId}/pages`),
          fetch(`/api/lintpdf/jobs/${jobId}`),
        ]);

        if (!pagesResp.ok) throw new Error("Failed to load page data");
        if (!jobResp.ok) throw new Error("Failed to load job data");

        const pagesData = await pagesResp.json();
        const jobData = await jobResp.json();

        setPages(pagesData.pages ?? []);
        setFindings(jobData.findings ?? []);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load viewer");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [jobId]);

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
    if (!separationMode || allChannelNames.length > 0) return;
    fetch(`/api/lintpdf/viewer/${jobId}/separations`)
      .then((r) => r.json())
      .then((data) => {
        const names = (data.channels ?? []).map((c: { name: string }) => c.name);
        setAllChannelNames(names);
        setEnabledChannels(new Set(names));
      })
      .catch(() => {});
  }, [separationMode, allChannelNames.length, jobId]);

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

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
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
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [pages.length]);

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <span className="animate-pulse text-muted-foreground">
          Loading viewer...
        </span>
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

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Toolbar */}
      <ViewerToolbar
        currentPage={currentPage}
        pageCount={pages.length}
        zoom={zoom}
        onPageChange={setCurrentPage}
        onZoomChange={setZoom}
        jobId={jobId}
        separationMode={separationMode}
        onToggleSeparationMode={() => setSeparationMode((v) => !v)}
        showTacHeatmap={showTacHeatmap}
        onToggleTacHeatmap={() => setShowTacHeatmap((v) => !v)}
      />

      {/* Main content: thumbnails | canvas | findings */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Page thumbnails */}
        <div className="w-28 shrink-0 border-r bg-muted/30 overflow-y-auto">
          <PageNavigator
            pages={pages}
            currentPage={currentPage}
            findings={findings}
            jobId={jobId}
            onPageChange={setCurrentPage}
          />
        </div>

        {/* Center: Page canvas */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-auto bg-neutral-800 p-4"
        >
          <div className="flex justify-center">
            {currentPageInfo && (
              <div className="relative">
                {separationMode ? (
                  <SeparationCanvas
                    jobId={jobId}
                    pageNum={currentPage}
                    enabledChannels={enabledChannels}
                    allChannels={allChannelNames}
                    width={Math.round(
                      currentPageInfo.width_pts * (zoom / 100),
                    )}
                    height={Math.round(
                      currentPageInfo.height_pts * (zoom / 100),
                    )}
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
                {showTacHeatmap && currentPageInfo && (
                  <TACHeatmapOverlay
                    jobId={jobId}
                    pageNum={currentPage}
                    width={Math.round(
                      currentPageInfo.width_pts * (zoom / 100),
                    )}
                    height={Math.round(
                      currentPageInfo.height_pts * (zoom / 100),
                    )}
                  />
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Findings panel or Separation panel */}
        <div className="w-80 shrink-0 border-l bg-background overflow-hidden">
          {separationMode ? (
            <SeparationPanel
              jobId={jobId}
              enabledChannels={enabledChannels}
              onToggleChannel={handleToggleChannel}
              onSetAllChannels={handleSetAllChannels}
            />
          ) : (
            <FindingsPanel
              findings={findings}
              selectedFinding={selectedFinding}
              onSelectFinding={handleSelectFinding}
              currentPage={currentPage}
            />
          )}
        </div>
      </div>
    </div>
  );
}
