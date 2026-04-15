import { useEffect, useRef, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import type { PageInfo, TacRun, ViewerAnnotation, ViewerFinding } from "../../lib/types";

interface PageCanvasProps {
  /** Absolute path (on disk) to the cached page PNG. */
  imagePath: string | null;
  /** PDF page metadata — used to translate PDF-points bbox values to
   *  on-image pixel coordinates.  */
  page: PageInfo;
  /** The raster's DPI, so we know how to scale PDF points → pixels. */
  renderedDpi: number;
  /** CSS-level zoom. 1 = fit-width. */
  zoom: number;
  /** Findings to outline in red/amber/blue. */
  findings: ViewerFinding[];
  /** Selected finding index — rendered with a thicker halo. */
  selectedFinding: number | null;
  /** TAC runs to outline when the TAC panel is active. */
  tacRuns: TacRun[];
  /** Annotations to outline. */
  annotations: ViewerAnnotation[];
  /** Clicked to record a densitometer sample. */
  onProbe?: (x: number, y: number) => void;
  /** Overlay image for the active channel / TAC heatmap. */
  overlayImagePath?: string | null;
  /** Overlay opacity, 0–1. */
  overlayOpacity?: number;
}

const PTS_PER_INCH = 72;

export function PageCanvas({
  imagePath,
  page,
  renderedDpi,
  zoom,
  findings,
  selectedFinding,
  tacRuns,
  annotations,
  onProbe,
  overlayImagePath,
  overlayOpacity = 0.6,
}: PageCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(
    null,
  );
  const [imageLoaded, setImageLoaded] = useState(false);

  // Reset when the image source changes.
  useEffect(() => {
    setImageLoaded(false);
  }, [imagePath]);

  // Render PDF points (lower-left origin) → on-image pixels (top-left
  // origin). The raster is at `renderedDpi` so one point = dpi/72 pixels.
  const ptsToPx = renderedDpi / PTS_PER_INCH;
  const pageHeightPx = page.height_pts * ptsToPx;

  function bboxToStyle(bbox: number[]) {
    const [x0, y0, x1, y1] = bbox;
    const left = x0 * ptsToPx;
    const top = pageHeightPx - y1 * ptsToPx; // Flip Y.
    const width = (x1 - x0) * ptsToPx;
    const height = (y1 - y0) * ptsToPx;
    return {
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
    };
  }

  function tacRunToStyle(run: TacRun) {
    // TAC runs come in top-left origin (pdftotext convention) — no flip.
    const left = run.x0 * ptsToPx;
    const top = run.y0 * ptsToPx;
    const width = (run.x1 - run.x0) * ptsToPx;
    const height = (run.y1 - run.y0) * ptsToPx;
    return {
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
    };
  }

  function annotationToStyle(a: ViewerAnnotation) {
    // Annotations use `geometry: {x0, y0, x1, y1}` in PDF points
    // (lower-left). Rect / freehand etc. fall back to a bounding box.
    const g = a.geometry as Record<string, number>;
    if (
      typeof g.x0 === "number" &&
      typeof g.y0 === "number" &&
      typeof g.x1 === "number" &&
      typeof g.y1 === "number"
    ) {
      return bboxToStyle([g.x0, g.y0, g.x1, g.y1]);
    }
    return null;
  }

  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!onProbe || !imgRef.current || !naturalSize) return;
    // Get click coordinates in the image's natural pixel space.
    const rect = imgRef.current.getBoundingClientRect();
    const xCss = e.clientX - rect.left;
    const yCss = e.clientY - rect.top;
    if (xCss < 0 || yCss < 0 || xCss > rect.width || yCss > rect.height) {
      return;
    }
    const xPx = (xCss / rect.width) * naturalSize.w;
    const yPxTopLeft = (yCss / rect.height) * naturalSize.h;
    // Convert to PDF points (lower-left origin).
    const xPts = xPx / ptsToPx;
    const yPts = page.height_pts - yPxTopLeft / ptsToPx;
    onProbe(xPts, yPts);
  }

  const containerStyle = naturalSize
    ? {
        width: `${naturalSize.w * zoom}px`,
        height: `${naturalSize.h * zoom}px`,
      }
    : undefined;

  return (
    <div
      ref={containerRef}
      className="relative mx-auto select-none"
      style={containerStyle}
      onClick={handleClick}
    >
      {imagePath ? (
        <img
          ref={imgRef}
          src={convertFileSrc(imagePath)}
          alt={`Page ${page.page_num}`}
          draggable={false}
          onLoad={(e) => {
            const img = e.currentTarget;
            setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
            setImageLoaded(true);
          }}
          className="block w-full h-full"
          style={{ imageRendering: zoom > 2 ? "pixelated" : "auto" }}
        />
      ) : (
        <div className="flex h-[800px] w-full items-center justify-center rounded-lg bg-gray-100 text-sm text-gray-400">
          Loading page {page.page_num}…
        </div>
      )}

      {/* Overlay raster (channel isolation or TAC heatmap). */}
      {overlayImagePath && imageLoaded && (
        <img
          src={convertFileSrc(overlayImagePath)}
          alt=""
          className="pointer-events-none absolute inset-0 block h-full w-full"
          style={{ opacity: overlayOpacity, mixBlendMode: "multiply" }}
          draggable={false}
        />
      )}

      {/* Finding outlines. */}
      {imageLoaded &&
        findings.map((f, idx) => {
          if (!f.bbox || f.bbox.length !== 4) return null;
          const colour =
            f.severity === "error"
              ? "ring-red-500/80"
              : f.severity === "warning"
                ? "ring-amber-500/70"
                : "ring-sky-500/60";
          const selected = selectedFinding === idx;
          return (
            <div
              key={`f-${idx}-${f.inspection_id}`}
              className={`absolute rounded ring-2 ${colour} ${
                selected ? "ring-offset-2 ring-offset-white" : ""
              } pointer-events-none`}
              style={bboxToStyle(f.bbox)}
              title={`${f.severity}: ${f.message}`}
            />
          );
        })}

      {/* TAC run outlines — dashed so they read differently from findings. */}
      {imageLoaded &&
        tacRuns.map((run, idx) => (
          <div
            key={`tac-${idx}`}
            className={`absolute rounded border-2 border-dashed pointer-events-none ${
              run.exceeds ? "border-red-500/80" : "border-amber-400/60"
            }`}
            style={tacRunToStyle(run)}
            title={`Mean TAC ${run.mean_tac.toFixed(0)}%${
              run.exceeds ? " — exceeds limit" : ""
            }`}
          />
        ))}

      {/* Annotation outlines. */}
      {imageLoaded &&
        annotations.map((a) => {
          const style = annotationToStyle(a);
          if (!style) return null;
          return (
            <div
              key={`a-${a.id}`}
              className="absolute rounded ring-2 ring-violet-500/70 pointer-events-none"
              style={style}
              title={a.text ?? a.kind}
            />
          );
        })}
    </div>
  );
}
