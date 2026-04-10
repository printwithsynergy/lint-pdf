"use client";

import type { PageInfo } from "./types";

interface BoxOverlayProps {
  page: PageInfo;
  canvasWidth: number;
  canvasHeight: number;
}

/** Convert a PDF-coordinate box to pixel-space for the canvas. */
function boxToPixels(
  box: { x0: number; y0: number; x1: number; y1: number },
  page: PageInfo,
  canvasWidth: number,
  canvasHeight: number,
) {
  const scaleX = canvasWidth / page.width_pts;
  const scaleY = canvasHeight / page.height_pts;
  const mb = page.media_box;

  return {
    left: (box.x0 - mb.x0) * scaleX,
    top: canvasHeight - (box.y1 - mb.y0) * scaleY,
    width: (box.x1 - box.x0) * scaleX,
    height: (box.y1 - box.y0) * scaleY,
  };
}

function ptToMm(pts: number): string {
  return (pts * 25.4 / 72).toFixed(1);
}

export function BoxOverlay({ page, canvasWidth, canvasHeight }: BoxOverlayProps) {
  const boxes: {
    label: string;
    color: string;
    dashArray: string;
    box: { x0: number; y0: number; x1: number; y1: number };
  }[] = [];

  if (page.trim_box) {
    boxes.push({
      label: "Trim",
      color: "#3b82f6",
      dashArray: "none",
      box: page.trim_box,
    });
  }

  if (page.bleed_box) {
    boxes.push({
      label: "Bleed",
      color: "#22c55e",
      dashArray: "8 4",
      box: page.bleed_box,
    });
  }

  if (page.crop_box) {
    boxes.push({
      label: "Crop",
      color: "#a855f7",
      dashArray: "4 2",
      box: page.crop_box,
    });
  }

  if (boxes.length === 0) return null;

  return (
    <div
      className="pointer-events-none absolute inset-0"
      style={{ zIndex: 15 }}
    >
      <svg width={canvasWidth} height={canvasHeight}>
        {boxes.map(({ label, color, dashArray, box }) => {
          const px = boxToPixels(box, page, canvasWidth, canvasHeight);
          const widthMm = ptToMm(box.x1 - box.x0);
          const heightMm = ptToMm(box.y1 - box.y0);

          return (
            <g key={label}>
              <rect
                x={px.left}
                y={px.top}
                width={px.width}
                height={px.height}
                fill="none"
                stroke={color}
                strokeWidth={1.5}
                strokeDasharray={dashArray}
                opacity={0.8}
              />
              {/* Label */}
              <text
                x={px.left + 4}
                y={px.top - 4}
                fill={color}
                fontSize={10}
                fontWeight="bold"
                fontFamily="sans-serif"
              >
                {label} ({widthMm} x {heightMm} mm)
              </text>
              {/* Width dimension */}
              <text
                x={px.left + px.width / 2}
                y={px.top + px.height + 14}
                fill={color}
                fontSize={9}
                textAnchor="middle"
                fontFamily="sans-serif"
              >
                {widthMm} mm
              </text>
              {/* Height dimension */}
              <text
                x={px.left - 4}
                y={px.top + px.height / 2}
                fill={color}
                fontSize={9}
                textAnchor="end"
                fontFamily="sans-serif"
                transform={`rotate(-90, ${px.left - 4}, ${px.top + px.height / 2})`}
              >
                {heightMm} mm
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-2 left-2 rounded bg-black/70 p-2 text-xs text-white">
        <p className="mb-1 font-semibold">Page Boxes</p>
        {boxes.map(({ label, color }) => (
          <div key={label} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-4 rounded"
              style={{ backgroundColor: color }}
            />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
