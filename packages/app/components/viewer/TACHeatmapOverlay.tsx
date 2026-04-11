"use client";

import { useEffect, useRef, useState } from "react";
import { DEFAULT_DPI, useViewerApi } from "./types";

interface TACHeatmapOverlayProps {
  jobId: string;
  pageNum: number;
  width: number;
  height: number;
  opacity?: number;
  dpi?: number;
  tacLimit?: number;
}

export function TACHeatmapOverlay({
  jobId,
  pageNum,
  width,
  height,
  opacity = 0.5,
  dpi = DEFAULT_DPI,
  tacLimit = 300,
}: TACHeatmapOverlayProps) {
  const { apiBase } = useViewerApi();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [heatmapImg, setHeatmapImg] = useState<HTMLImageElement | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");

    const img = new Image();
    img.onload = () => {
      setHeatmapImg(img);
      setLoading(false);
    };
    img.onerror = () => {
      setError("Failed to load TAC heatmap");
      setLoading(false);
    };
    img.src = `${apiBase}/pages/${pageNum}/tac-heatmap?dpi=${dpi}&tac_limit=${tacLimit}`;
  }, [apiBase, pageNum, dpi, tacLimit]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !heatmapImg) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);
    ctx.globalAlpha = opacity;
    ctx.drawImage(heatmapImg, 0, 0, width, height);
    ctx.globalAlpha = 1.0;
  }, [heatmapImg, width, height, opacity]);

  if (loading) {
    return (
      <div
        className="absolute left-0 top-0 flex items-center justify-center"
        style={{ width, height }}
      >
        <span className="text-xs text-muted-foreground">
          Loading TAC heatmap...
        </span>
      </div>
    );
  }

  if (error) {
    return null;
  }

  return (
    <>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="pointer-events-none absolute left-0 top-0"
        style={{ width, height }}
      />
      {/* Legend */}
      <div className="absolute bottom-2 right-2 rounded bg-black/70 p-2 text-xs text-white">
        <p className="mb-1 font-semibold">TAC Coverage</p>
        <div className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: "rgb(0, 180, 0)" }} />
          <span>&lt; 250%</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: "rgb(255, 200, 0)" }} />
          <span>250–{tacLimit}%</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded" style={{ backgroundColor: "rgb(255, 0, 0)" }} />
          <span>&ge; {tacLimit}%</span>
        </div>
      </div>
    </>
  );
}
