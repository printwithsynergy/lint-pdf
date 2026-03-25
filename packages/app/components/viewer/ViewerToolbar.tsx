"use client";

import { ZoomControls } from "./ZoomControls";

interface ViewerToolbarProps {
  currentPage: number;
  pageCount: number;
  zoom: number;
  onPageChange: (page: number) => void;
  onZoomChange: (zoom: number) => void;
  jobId: string;
}

export function ViewerToolbar({
  currentPage,
  pageCount,
  zoom,
  onPageChange,
  onZoomChange,
  jobId,
}: ViewerToolbarProps) {
  return (
    <div className="flex items-center justify-between border-b bg-background px-4 py-2">
      {/* Left: Page navigation */}
      <div className="flex items-center gap-2">
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
      <ZoomControls zoom={zoom} onZoomChange={onZoomChange} />

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        <a
          href={`/api/lintpdf/reports/${jobId}/html`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded border px-3 py-1 text-sm hover:bg-muted"
        >
          HTML Report
        </a>
        <a
          href={`/api/lintpdf/reports/${jobId}/download`}
          className="rounded border px-3 py-1 text-sm hover:bg-muted"
        >
          Download PDF
        </a>
      </div>
    </div>
  );
}
