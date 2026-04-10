"use client";

import { useCallback, useRef, useState } from "react";

interface MeasureToolProps {
  pageWidthPts: number;
  pageHeightPts: number;
  canvasWidth: number;
  canvasHeight: number;
}

interface Measurement {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  distancePts: number;
  distanceMm: number;
  distanceIn: number;
}

export function MeasureTool({
  pageWidthPts,
  pageHeightPts,
  canvasWidth,
  canvasHeight,
}: MeasureToolProps) {
  const [measuring, setMeasuring] = useState(false);
  const [start, setStart] = useState<{ x: number; y: number } | null>(null);
  const [end, setEnd] = useState<{ x: number; y: number } | null>(null);
  const [measurement, setMeasurement] = useState<Measurement | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const pixelToPts = useCallback(
    (px: number, py: number) => {
      const ptsX = (px / canvasWidth) * pageWidthPts;
      const ptsY = (py / canvasHeight) * pageHeightPts;
      return { x: ptsX, y: ptsY };
    },
    [canvasWidth, canvasHeight, pageWidthPts, pageHeightPts],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      setStart({ x, y });
      setEnd(null);
      setMeasurement(null);
      setMeasuring(true);
    },
    [],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!measuring || !start) return;
      const rect = e.currentTarget.getBoundingClientRect();
      let x = e.clientX - rect.left;
      let y = e.clientY - rect.top;

      // Snap to horizontal/vertical if Shift held
      if (e.shiftKey) {
        const dx = Math.abs(x - start.x);
        const dy = Math.abs(y - start.y);
        if (dx > dy) y = start.y;
        else x = start.x;
      }

      setEnd({ x, y });
    },
    [measuring, start],
  );

  const handleMouseUp = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!measuring || !start || !end) {
        setMeasuring(false);
        return;
      }

      const p1 = pixelToPts(start.x, start.y);
      const p2 = pixelToPts(end.x, end.y);

      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const distancePts = Math.sqrt(dx * dx + dy * dy);
      const distanceMm = distancePts * (25.4 / 72);
      const distanceIn = distancePts / 72;

      setMeasurement({
        x1: start.x,
        y1: start.y,
        x2: end.x,
        y2: end.y,
        distancePts: Math.round(distancePts * 100) / 100,
        distanceMm: Math.round(distanceMm * 100) / 100,
        distanceIn: Math.round(distanceIn * 1000) / 1000,
      });
      setMeasuring(false);
    },
    [measuring, start, end, pixelToPts],
  );

  const midX = start && end ? (start.x + end.x) / 2 : 0;
  const midY = start && end ? (start.y + end.y) / 2 : 0;

  return (
    <div
      ref={overlayRef}
      className="absolute inset-0 cursor-crosshair"
      style={{ zIndex: 25 }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* Ruler line (during drag or after measurement) */}
      {start && end && (
        <svg
          className="pointer-events-none absolute inset-0"
          width={canvasWidth}
          height={canvasHeight}
        >
          <line
            x1={start.x}
            y1={start.y}
            x2={end.x}
            y2={end.y}
            stroke="#22c55e"
            strokeWidth={2}
            strokeDasharray="6 3"
          />
          {/* Endpoint dots */}
          <circle cx={start.x} cy={start.y} r={4} fill="#22c55e" />
          <circle cx={end.x} cy={end.y} r={4} fill="#22c55e" />
        </svg>
      )}

      {/* Measurement label */}
      {measurement && (
        <div
          className="pointer-events-none absolute z-30 rounded bg-green-900/90 px-2 py-1 text-xs font-mono text-green-100 shadow-lg"
          style={{ left: midX + 8, top: midY - 24 }}
        >
          {measurement.distanceMm} mm &middot; {measurement.distanceIn}" &middot; {measurement.distancePts} pt
        </div>
      )}

      {/* Drag hint */}
      {!start && (
        <div className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 rounded bg-black/70 px-3 py-1 text-xs text-white">
          Click and drag to measure distance. Hold Shift to snap.
        </div>
      )}
    </div>
  );
}
