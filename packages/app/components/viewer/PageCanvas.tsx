"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PageInfo, ViewerFinding } from "./types";
import { DEFAULT_DPI, SEVERITY_COLORS } from "./types";

interface PageCanvasProps {
  jobId: string;
  page: PageInfo;
  zoom: number;
  findings: ViewerFinding[];
  selectedFinding: ViewerFinding | null;
  onFindingClick: (finding: ViewerFinding) => void;
}

export function PageCanvas({
  jobId,
  page,
  zoom,
  findings,
  selectedFinding,
  onFindingClick,
}: PageCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tileImg, setTileImg] = useState<HTMLImageElement | null>(null);
  const [loading, setLoading] = useState(true);

  // Scale factor: zoom% maps to DPI scaling
  const scale = zoom / 100;
  const dpi = DEFAULT_DPI;

  // PDF points to pixels at the given DPI
  const ptsToPixels = dpi / 72;
  const canvasWidth = Math.round(page.width_pts * ptsToPixels * scale);
  const canvasHeight = Math.round(page.height_pts * ptsToPixels * scale);

  // Load tile image
  useEffect(() => {
    setLoading(true);
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = `/api/lintpdf/viewer/${jobId}/pages/${page.page_num}/tile?dpi=${dpi}`;
    img.onload = () => {
      setTileImg(img);
      setLoading(false);
    };
    img.onerror = () => setLoading(false);
  }, [jobId, page.page_num, dpi]);

  // Render canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !tileImg) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;

    // Draw the page tile, scaled to the canvas size
    ctx.drawImage(tileImg, 0, 0, canvasWidth, canvasHeight);

    // Draw finding overlays
    const pageFindings = findings.filter(
      (f) => f.page_num === page.page_num && f.bbox,
    );

    for (const finding of pageFindings) {
      if (!finding.bbox) continue;
      const [x0, y0, x1, y1] = finding.bbox;

      // Convert PDF coordinates (origin lower-left) to canvas (origin upper-left)
      const px0 = x0 * ptsToPixels * scale;
      const py0 = (page.height_pts - y1) * ptsToPixels * scale;
      const pw = (x1 - x0) * ptsToPixels * scale;
      const ph = (y1 - y0) * ptsToPixels * scale;

      const colors = SEVERITY_COLORS[finding.severity];
      const isSelected =
        selectedFinding?.inspection_id === finding.inspection_id &&
        selectedFinding?.page_num === finding.page_num &&
        selectedFinding?.message === finding.message;

      // Fill
      ctx.fillStyle = isSelected
        ? colors.fill.replace("0.15", "0.3")
        : colors.fill;
      ctx.fillRect(px0, py0, pw, ph);

      // Stroke
      ctx.strokeStyle = colors.stroke;
      ctx.lineWidth = isSelected ? 3 : 1.5;
      ctx.strokeRect(px0, py0, pw, ph);
    }
  }, [
    tileImg,
    canvasWidth,
    canvasHeight,
    findings,
    page,
    ptsToPixels,
    scale,
    selectedFinding,
  ]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Handle click on canvas to detect finding
  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = (e.clientX - rect.left) * (canvas.width / rect.width);
    const clickY = (e.clientY - rect.top) * (canvas.height / rect.height);

    // Convert to PDF coordinates
    const pdfX = clickX / (ptsToPixels * scale);
    const pdfY = page.height_pts - clickY / (ptsToPixels * scale);

    // Find clicked finding
    const pageFindings = findings.filter(
      (f) => f.page_num === page.page_num && f.bbox,
    );
    for (const finding of pageFindings) {
      if (!finding.bbox) continue;
      const [x0, y0, x1, y1] = finding.bbox;
      if (pdfX >= x0 && pdfX <= x1 && pdfY >= y0 && pdfY <= y1) {
        onFindingClick(finding);
        return;
      }
    }
  };

  return (
    <div className="relative inline-block">
      {loading && (
        <div
          className="flex items-center justify-center bg-muted/50"
          style={{ width: canvasWidth, height: canvasHeight }}
        >
          <span className="animate-pulse text-sm text-muted-foreground">
            Loading page {page.page_num}...
          </span>
        </div>
      )}
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        className={`cursor-crosshair ${loading ? "hidden" : ""}`}
        style={{ width: canvasWidth, height: canvasHeight }}
      />
    </div>
  );
}
