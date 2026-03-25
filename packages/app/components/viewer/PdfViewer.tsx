"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PageInfo, ViewerFinding } from "./types";
import { PageCanvas } from "./PageCanvas";
import { FindingsPanel } from "./FindingsPanel";
import { PageNavigator } from "./PageNavigator";
import { ViewerToolbar } from "./ViewerToolbar";

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
              <PageCanvas
                jobId={jobId}
                page={currentPageInfo}
                zoom={zoom}
                findings={findings}
                selectedFinding={selectedFinding}
                onFindingClick={handleSelectFinding}
              />
            )}
          </div>
        </div>

        {/* Right: Findings panel */}
        <div className="w-80 shrink-0 border-l bg-background overflow-hidden">
          <FindingsPanel
            findings={findings}
            selectedFinding={selectedFinding}
            onSelectFinding={handleSelectFinding}
            currentPage={currentPage}
          />
        </div>
      </div>
    </div>
  );
}
