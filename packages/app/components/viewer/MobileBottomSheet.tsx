"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type SnapPosition = "collapsed" | "half" | "full";

interface MobileBottomSheetProps {
  children: React.ReactNode;
  summary: React.ReactNode;
  /** Controlled snap position from parent. */
  snap?: SnapPosition;
  /** Notify parent when snap changes (drag or tap). */
  onSnapChange?: (snap: SnapPosition) => void;
}

const SNAP_HEIGHTS: Record<SnapPosition, string> = {
  collapsed: "64px",
  half: "50vh",
  full: "90vh",
};

const SNAP_ORDER: SnapPosition[] = ["collapsed", "half", "full"];

export function MobileBottomSheet({ children, summary, snap: controlledSnap, onSnapChange }: MobileBottomSheetProps) {
  const [internalSnap, setInternalSnap] = useState<SnapPosition>("collapsed");
  const [dragging, setDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState<number | null>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);

  const snap = controlledSnap ?? internalSnap;

  const updateSnap = useCallback(
    (next: SnapPosition) => {
      setInternalSnap(next);
      onSnapChange?.(next);
    },
    [onSnapChange],
  );

  // Sync when controlled prop changes
  useEffect(() => {
    if (controlledSnap !== undefined) {
      setInternalSnap(controlledSnap);
    }
  }, [controlledSnap]);

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      const touch = e.touches[0];
      startYRef.current = touch.clientY;
      const el = sheetRef.current;
      if (el) {
        startHeightRef.current = el.getBoundingClientRect().height;
      }
      setDragging(true);
    },
    [],
  );

  const handleTouchMove = useCallback(
    (e: React.TouchEvent) => {
      if (!dragging) return;
      const touch = e.touches[0];
      const delta = startYRef.current - touch.clientY;
      const newHeight = startHeightRef.current + delta;
      const vh = window.innerHeight;
      const clamped = Math.max(64, Math.min(vh * 0.9, newHeight));
      setDragOffset(clamped);
    },
    [dragging],
  );

  const handleTouchEnd = useCallback(() => {
    setDragging(false);
    if (dragOffset === null) return;

    const vh = window.innerHeight;
    const snapValues = {
      collapsed: 64,
      half: vh * 0.5,
      full: vh * 0.9,
    };

    // Find nearest snap point
    let closest: SnapPosition = "collapsed";
    let minDist = Infinity;
    for (const pos of SNAP_ORDER) {
      const dist = Math.abs(dragOffset - snapValues[pos]);
      if (dist < minDist) {
        minDist = dist;
        closest = pos;
      }
    }

    // Velocity-based: if user was in half and dragged down a bit, collapse
    const currentIdx = SNAP_ORDER.indexOf(snap);
    if (currentIdx === 1 && dragOffset < snapValues.half - 40) {
      closest = "collapsed";
    } else if (currentIdx === 1 && dragOffset > snapValues.half + 40) {
      closest = "full";
    }

    updateSnap(closest);
    setDragOffset(null);
  }, [dragOffset, snap, updateSnap]);

  const isCollapsed = snap === "collapsed" && dragOffset === null;

  return (
    <div
      ref={sheetRef}
      className="fixed inset-x-0 bottom-0 z-50 flex flex-col rounded-t-2xl bg-slate-900 shadow-2xl"
      style={{
        height: dragOffset !== null ? `${dragOffset}px` : SNAP_HEIGHTS[snap],
        transition: dragging ? "none" : "height 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      {/* Drag handle */}
      <div
        className="flex shrink-0 cursor-grab touch-none flex-col items-center pb-1 pt-2 active:cursor-grabbing"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="h-1 w-10 rounded-full bg-slate-600" />
      </div>

      {/* Summary bar (always visible) */}
      <div
        className="flex shrink-0 items-center px-4 pb-2"
        onClick={() => {
          if (isCollapsed) updateSnap("half");
        }}
      >
        {summary}
      </div>

      {/* Content (scrollable when expanded) */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      )}
    </div>
  );
}
