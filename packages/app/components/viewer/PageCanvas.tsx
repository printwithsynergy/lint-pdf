"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { PageInfo, ViewerFinding } from "./types";
import { DEFAULT_DPI, SEVERITY_COLORS, useViewerApi } from "./types";

interface PageCanvasProps {
  jobId: string;
  page: PageInfo;
  zoom: number;
  findings: ViewerFinding[];
  selectedFinding: ViewerFinding | null;
  onFindingClick: (finding: ViewerFinding) => void;
}

const SEVERITY_HEX: Record<string, string> = {
  error: "#ef4444",
  warning: "#f59e0b",
  advisory: "#3b82f6",
};

export function PageCanvas({
  jobId,
  page,
  zoom,
  findings,
  selectedFinding,
  onFindingClick,
}: PageCanvasProps) {
  const { apiBase } = useViewerApi();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tileImg, setTileImg] = useState<HTMLImageElement | null>(null);
  const [loading, setLoading] = useState(true);
  const [pulsePhase, setPulsePhase] = useState(0);

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
    img.src = `${apiBase}/pages/${page.page_num}/tile?dpi=${dpi}`;
    img.onload = () => {
      setTileImg(img);
      setLoading(false);
    };
    img.onerror = () => setLoading(false);
  }, [apiBase, page.page_num, dpi]);

  // Animate pulse for selected finding
  useEffect(() => {
    if (!selectedFinding?.bbox || selectedFinding.page_num !== page.page_num) return;
    let raf: number;
    let start: number | null = null;
    const animate = (ts: number) => {
      if (start === null) start = ts;
      const elapsed = ts - start;
      // Oscillate between 0 and 1 over 1.5s
      setPulsePhase((Math.sin((elapsed / 750) * Math.PI) + 1) / 2);
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [selectedFinding, page.page_num]);

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

    const hasSelected =
      selectedFinding &&
      selectedFinding.page_num === page.page_num &&
      selectedFinding.bbox;

    // Counter for badge numbering
    let badgeIndex = 0;

    for (const finding of pageFindings) {
      if (!finding.bbox) continue;
      badgeIndex++;
      const [x0, y0, x1, y1] = finding.bbox;

      // Convert PDF coordinates (origin lower-left) to canvas (origin upper-left)
      const px0 = x0 * ptsToPixels * scale;
      const py0 = (page.height_pts - y1) * ptsToPixels * scale;
      const pw = (x1 - x0) * ptsToPixels * scale;
      const ph = (y1 - y0) * ptsToPixels * scale;

      const colors = SEVERITY_COLORS[finding.severity];
      const severityHex = SEVERITY_HEX[finding.severity];
      const isSelected =
        selectedFinding?.inspection_id === finding.inspection_id &&
        selectedFinding?.page_num === finding.page_num &&
        selectedFinding?.message === finding.message;

      if (hasSelected && !isSelected) {
        // Dimmed: other findings when one is selected
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = colors.fill;
        ctx.fillRect(px0, py0, pw, ph);
        ctx.strokeStyle = colors.stroke;
        ctx.lineWidth = 1;
        ctx.strokeRect(px0, py0, pw, ph);
        ctx.globalAlpha = 1;
      } else if (isSelected) {
        // Selected finding: prominent highlight with animated glow
        const glowAlpha = 0.15 + pulsePhase * 0.2;
        ctx.fillStyle = colors.fill.replace(
          /[\d.]+\)$/,
          `${glowAlpha.toFixed(2)})`,
        );
        ctx.fillRect(px0, py0, pw, ph);

        // Animated outer glow
        const glowSize = 4 + pulsePhase * 4;
        ctx.shadowColor = severityHex;
        ctx.shadowBlur = glowSize;
        ctx.strokeStyle = severityHex;
        ctx.lineWidth = 4;
        ctx.strokeRect(px0, py0, pw, ph);
        ctx.shadowColor = "transparent";
        ctx.shadowBlur = 0;

        // Numbered badge at top-right corner
        const badgeRadius = 10;
        const bx = px0 + pw - 2;
        const by = py0 - 2;
        ctx.fillStyle = severityHex;
        ctx.beginPath();
        ctx.arc(bx, by, badgeRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 11px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(badgeIndex), bx, by);
      } else {
        // No selection active: show all at normal opacity
        ctx.fillStyle = colors.fill;
        ctx.fillRect(px0, py0, pw, ph);
        ctx.strokeStyle = colors.stroke;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(px0, py0, pw, ph);
      }
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
    pulsePhase,
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
