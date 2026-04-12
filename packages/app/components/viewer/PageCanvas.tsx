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
  onZoomChange?: (zoom: number) => void;
  onPageChange?: (delta: number) => void;
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
  onZoomChange,
  onPageChange,
}: PageCanvasProps) {
  const { apiBase } = useViewerApi();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tileImg, setTileImg] = useState<HTMLImageElement | null>(null);
  const [loading, setLoading] = useState(true);

  // Tooltip state: shows finding info near the clicked bbox
  const [tooltip, setTooltip] = useState<{ finding: ViewerFinding; x: number; y: number } | null>(null);
  const tooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Touch gesture tracking
  const touchRef = useRef<{ x: number; y: number; dist: number; zoom: number; moved: boolean } | null>(null);

  const getTouchDist = (touches: React.TouchList) => {
    if (touches.length < 2) return 0;
    const dx = touches[1]!.clientX - touches[0]!.clientX;
    const dy = touches[1]!.clientY - touches[0]!.clientY;
    return Math.hypot(dx, dy);
  };

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 2 && onZoomChange) {
      e.preventDefault();
      touchRef.current = { x: 0, y: 0, dist: getTouchDist(e.touches), zoom, moved: false };
    } else if (e.touches.length === 1) {
      touchRef.current = { x: e.touches[0]!.clientX, y: e.touches[0]!.clientY, dist: 0, zoom, moved: false };
    }
  }, [zoom, onZoomChange]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchRef.current) return;
    if (e.touches.length === 2 && onZoomChange && touchRef.current.dist > 0) {
      e.preventDefault();
      const newDist = getTouchDist(e.touches);
      const scale = newDist / touchRef.current.dist;
      const newZoom = Math.round(Math.max(25, Math.min(400, touchRef.current.zoom * scale)));
      onZoomChange(newZoom);
      touchRef.current.moved = true;
    } else if (e.touches.length === 1) {
      touchRef.current.moved = true;
    }
  }, [onZoomChange]);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (!touchRef.current || !onPageChange) return;
    if (touchRef.current.dist === 0 && touchRef.current.moved && e.changedTouches.length === 1) {
      const dx = e.changedTouches[0]!.clientX - touchRef.current.x;
      if (Math.abs(dx) > 60) {
        onPageChange(dx < 0 ? 1 : -1);
      }
    }
    touchRef.current = null;
  }, [onPageChange]);
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

  // Show tooltip when selectedFinding changes (from panel click or canvas click)
  useEffect(() => {
    if (!selectedFinding || selectedFinding.page_num !== page.page_num) {
      setTooltip(null);
      return;
    }
    let x: number;
    let y: number;
    if (selectedFinding.bbox) {
      const [x0, , x1, y1] = selectedFinding.bbox;
      x = ((x0 + x1) / 2) * ptsToPixels * scale;
      y = (page.height_pts - y1) * ptsToPixels * scale;
    } else {
      // No bbox: show tooltip centered at top of page
      x = canvasWidth / 2;
      y = 40;
    }
    setTooltip({ finding: selectedFinding, x, y });
    if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    tooltipTimerRef.current = setTimeout(() => setTooltip(null), 6000);
  }, [selectedFinding, page.page_num, page.height_pts, ptsToPixels, scale, canvasWidth]);

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

  // Handle click on canvas to detect finding and show tooltip
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
        // Tooltip shown by the selectedFinding useEffect
        return;
      }
    }
    // Clicked empty area: dismiss tooltip
    setTooltip(null);
  };

  return (
    <div
      className="relative inline-block"
      style={{ touchAction: onZoomChange || onPageChange ? "none" : undefined }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {loading && (
        <div
          className="flex items-center justify-center bg-muted/50"
          style={{ width: canvasWidth, height: canvasHeight }}
        >
          <div className="flex flex-col items-center gap-2">
            <svg className="h-8 w-8 animate-spin text-slate-400" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
            <span className="text-xs text-slate-500">Page {page.page_num}</span>
          </div>
        </div>
      )}
      <canvas
        ref={canvasRef}
        onClick={handleClick}
        className={`cursor-crosshair ${loading ? "hidden" : ""}`}
        style={{ width: canvasWidth, height: canvasHeight }}
      />
      {/* Page-level indicator for findings without bbox */}
      {selectedFinding && !selectedFinding.bbox && selectedFinding.page_num === page.page_num && (
        <div
          className="pointer-events-none absolute inset-0 animate-pulse rounded border-2"
          style={{ borderColor: SEVERITY_HEX[selectedFinding.severity], boxShadow: `inset 0 0 30px ${SEVERITY_HEX[selectedFinding.severity]}30` }}
        />
      )}
      {/* Finding tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-40 max-w-[280px] rounded-lg bg-black/90 px-3 py-2 text-xs text-white shadow-xl"
          style={{
            left: Math.max(8, Math.min(tooltip.x - 100, canvasWidth - 288)),
            top: Math.max(8, tooltip.y - 8),
            transform: "translateY(-100%)",
          }}
        >
          <div className="mb-1 flex items-center gap-2">
            <span
              className="inline-block h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: SEVERITY_HEX[tooltip.finding.severity] }}
            />
            <span className="font-bold uppercase" style={{ color: SEVERITY_HEX[tooltip.finding.severity] }}>
              {tooltip.finding.severity}
            </span>
            <code className="ml-auto text-[10px] text-gray-400">{tooltip.finding.inspection_id}</code>
          </div>
          <p className="leading-snug text-gray-200">{tooltip.finding.message.length > 120 ? tooltip.finding.message.slice(0, 120) + "..." : tooltip.finding.message}</p>
          {tooltip.finding.category && (
            <span className="mt-1 inline-block rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-gray-400">{tooltip.finding.category}</span>
          )}
        </div>
      )}
    </div>
  );
}
