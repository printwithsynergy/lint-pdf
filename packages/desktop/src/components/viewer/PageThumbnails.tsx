import { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import type { PageInfo } from "../../lib/types";
import { viewerTile } from "../../lib/tauri";

interface PageThumbnailsProps {
  jobId: string;
  pages: PageInfo[];
  currentPage: number;
  onSelect: (page: number) => void;
}

const THUMB_DPI = 36; // engine minimum — tiny, cheap, and cached

export function PageThumbnails({
  jobId,
  pages,
  currentPage,
  onSelect,
}: PageThumbnailsProps) {
  // Load thumbnails lazily. We could eagerly fetch all pages but for
  // a 200-page book that would be 200 HTTP requests; instead load
  // the visible strip and enlarge on-demand as the user scrolls.
  // Simpler: prefetch the ±5 window around currentPage.
  const [paths, setPaths] = useState<Record<number, string>>({});

  useEffect(() => {
    let cancelled = false;
    const window = 5;
    const start = Math.max(1, currentPage - window);
    const end = Math.min(pages.length, currentPage + window);
    for (let p = start; p <= end; p++) {
      if (paths[p]) continue;
      viewerTile(jobId, p, THUMB_DPI)
        .then((r) => {
          if (cancelled) return;
          setPaths((prev) => ({ ...prev, [p]: r.path }));
        })
        .catch(() => {
          /* skip — the tile will retry next navigation */
        });
    }
    return () => {
      cancelled = true;
    };
  }, [jobId, currentPage, pages.length, paths]);

  return (
    <div className="w-24 shrink-0 overflow-y-auto border-r border-gray-200 bg-gray-50 py-2">
      <ul className="space-y-2 px-2">
        {pages.map((p) => {
          const path = paths[p.page_num];
          const active = p.page_num === currentPage;
          return (
            <li key={p.page_num}>
              <button
                onClick={() => onSelect(p.page_num)}
                className={`w-full overflow-hidden rounded border-2 bg-white transition-colors ${
                  active
                    ? "border-brand-500 shadow-sm"
                    : "border-gray-200 hover:border-gray-400"
                }`}
                aria-label={`Page ${p.page_num}`}
              >
                {path ? (
                  <img
                    src={convertFileSrc(path)}
                    alt={`Page ${p.page_num}`}
                    className="block w-full"
                  />
                ) : (
                  <div
                    className="w-full bg-gray-100"
                    style={{
                      aspectRatio: `${p.width_pts} / ${p.height_pts}`,
                    }}
                  />
                )}
                <div
                  className={`px-1 py-0.5 text-center text-[10px] ${
                    active ? "bg-brand-50 text-brand-700" : "text-gray-500"
                  }`}
                >
                  {p.page_num}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
