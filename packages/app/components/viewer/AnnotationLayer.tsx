"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useViewerApi } from "./types";

export type AnnotationKind = "rect" | "circle" | "arrow" | "freehand" | "note";

export interface Annotation {
  id: string;
  page_num: number;
  kind: AnnotationKind;
  geometry: Record<string, unknown>;
  color: string;
  text: string | null;
  author_email: string;
}

export interface AnnotationLayerProps {
  jobId: string;
  pageNum: number;
  pageWidthPts: number;
  pageHeightPts: number;
  canvasWidth: number;
  canvasHeight: number;
  activeKind: AnnotationKind | null;
  activeColor: string;
  annotations: Annotation[];
  /** Returns the newly created row from the server, or null on failure. */
  onCreate: (draft: Omit<Annotation, "id" | "author_email">) => Promise<Annotation | null>;
  onUpdate: (id: string, patch: Partial<Annotation>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  /** Whether the caller has permission to write annotations. */
  canWrite: boolean;
}

/** Canvas pixel -> PDF-point coordinate (origin lower-left). */
function pxToPt(
  x: number,
  y: number,
  canvasW: number,
  canvasH: number,
  pageW: number,
  pageH: number,
): { x: number; y: number } {
  return {
    x: (x / canvasW) * pageW,
    y: pageH - (y / canvasH) * pageH,
  };
}

/** PDF-point -> canvas pixel. */
function ptToPx(
  x: number,
  y: number,
  canvasW: number,
  canvasH: number,
  pageW: number,
  pageH: number,
): { x: number; y: number } {
  return {
    x: (x / pageW) * canvasW,
    y: canvasH - (y / pageH) * canvasH,
  };
}

/**
 * SVG overlay for reviewer markup. Draws the existing annotation layer
 * (rects, ellipses, arrows, freehand strokes, sticky-note pins) and, when
 * an ``activeKind`` is set, captures pointer input to create new shapes.
 * All geometry is stored in PDF-point space so annotations survive zoom
 * and DPI changes.
 */
export function AnnotationLayer({
  pageNum,
  pageWidthPts,
  pageHeightPts,
  canvasWidth,
  canvasHeight,
  activeKind,
  activeColor,
  annotations,
  onCreate,
  onUpdate,
  onDelete,
  canWrite,
}: AnnotationLayerProps) {
  const [drawing, setDrawing] = useState<{
    kind: AnnotationKind;
    startPx: { x: number; y: number };
    endPx: { x: number; y: number };
    points?: { x: number; y: number }[];
  } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pendingNote, setPendingNote] = useState<{ x: number; y: number } | null>(null);
  const [noteText, setNoteText] = useState("");
  const svgRef = useRef<SVGSVGElement | null>(null);

  const ownedCursor = activeKind ? "crosshair" : "default";

  // Only show this page's annotations.
  const pageAnnotations = useMemo(
    () => annotations.filter((a) => a.page_num === pageNum),
    [annotations, pageNum],
  );

  const finishShape = useCallback(
    async (
      kind: AnnotationKind,
      geometry: Record<string, unknown>,
      text?: string,
    ) => {
      await onCreate({
        page_num: pageNum,
        kind,
        geometry,
        color: activeColor,
        text: text ?? null,
      });
    },
    [onCreate, pageNum, activeColor],
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      if (!canWrite || !activeKind) return;
      if ((e.target as Element).closest("[data-annotation-id]")) return; // click-through to existing annotations
      e.preventDefault();
      const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      if (activeKind === "note") {
        setPendingNote({ x, y });
        setNoteText("");
        return;
      }

      setDrawing({
        kind: activeKind,
        startPx: { x, y },
        endPx: { x, y },
        points: activeKind === "freehand" ? [{ x, y }] : undefined,
      });
      (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
    },
    [canWrite, activeKind],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      if (!drawing) return;
      const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      setDrawing((prev) => {
        if (!prev) return prev;
        if (prev.kind === "freehand") {
          return {
            ...prev,
            endPx: { x, y },
            points: [...(prev.points ?? []), { x, y }],
          };
        }
        return { ...prev, endPx: { x, y } };
      });
    },
    [drawing],
  );

  const handlePointerUp = useCallback(async () => {
    if (!drawing) return;
    const { kind, startPx, endPx, points } = drawing;
    setDrawing(null);

    const a = pxToPt(startPx.x, startPx.y, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
    const b = pxToPt(endPx.x, endPx.y, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
    if (kind === "rect") {
      if (Math.abs(endPx.x - startPx.x) < 3 || Math.abs(endPx.y - startPx.y) < 3) return;
      await finishShape("rect", {
        x0: Math.min(a.x, b.x),
        y0: Math.min(a.y, b.y),
        x1: Math.max(a.x, b.x),
        y1: Math.max(a.y, b.y),
      });
    } else if (kind === "circle") {
      if (Math.abs(endPx.x - startPx.x) < 3 || Math.abs(endPx.y - startPx.y) < 3) return;
      await finishShape("circle", {
        cx: (a.x + b.x) / 2,
        cy: (a.y + b.y) / 2,
        rx: Math.abs(a.x - b.x) / 2,
        ry: Math.abs(a.y - b.y) / 2,
      });
    } else if (kind === "arrow") {
      if (Math.hypot(endPx.x - startPx.x, endPx.y - startPx.y) < 6) return;
      await finishShape("arrow", { x0: a.x, y0: a.y, x1: b.x, y1: b.y });
    } else if (kind === "freehand" && points && points.length > 1) {
      const pts = points.map((p) =>
        pxToPt(p.x, p.y, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts),
      );
      await finishShape("freehand", { points: pts });
    }
  }, [drawing, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts, finishShape]);

  const confirmNote = useCallback(async () => {
    if (!pendingNote || !noteText.trim()) {
      setPendingNote(null);
      setNoteText("");
      return;
    }
    const pt = pxToPt(
      pendingNote.x,
      pendingNote.y,
      canvasWidth,
      canvasHeight,
      pageWidthPts,
      pageHeightPts,
    );
    await finishShape("note", { x: pt.x, y: pt.y }, noteText.trim());
    setPendingNote(null);
    setNoteText("");
  }, [pendingNote, noteText, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts, finishShape]);

  // Dismiss note composer on Escape.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setPendingNote(null);
        setNoteText("");
        setSelectedId(null);
      } else if (e.key === "Delete" || e.key === "Backspace") {
        if (selectedId && canWrite) void onDelete(selectedId);
        setSelectedId(null);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, canWrite, onDelete]);

  // Render a single saved annotation.
  const renderSaved = (a: Annotation) => {
    const g = a.geometry as Record<string, number>;
    const common = {
      stroke: a.color,
      strokeWidth: 2,
      fill: "transparent",
      cursor: canWrite ? "pointer" : "default",
      onClick: (e: React.MouseEvent) => {
        e.stopPropagation();
        setSelectedId(a.id);
      },
      "data-annotation-id": a.id,
    };
    if (a.kind === "rect") {
      const p0 = ptToPx(g.x0, g.y0, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const p1 = ptToPx(g.x1, g.y1, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const x = Math.min(p0.x, p1.x);
      const y = Math.min(p0.y, p1.y);
      const w = Math.abs(p1.x - p0.x);
      const h = Math.abs(p1.y - p0.y);
      return <rect key={a.id} {...common} x={x} y={y} width={w} height={h} />;
    }
    if (a.kind === "circle") {
      const c = ptToPx(g.cx, g.cy, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const rx = (g.rx / pageWidthPts) * canvasWidth;
      const ry = (g.ry / pageHeightPts) * canvasHeight;
      return <ellipse key={a.id} {...common} cx={c.x} cy={c.y} rx={rx} ry={ry} />;
    }
    if (a.kind === "arrow") {
      const p0 = ptToPx(g.x0, g.y0, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const p1 = ptToPx(g.x1, g.y1, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const mid = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
      const dx = p1.x - p0.x;
      const dy = p1.y - p0.y;
      const len = Math.hypot(dx, dy) || 1;
      const ux = dx / len;
      const uy = dy / len;
      const size = 10;
      const leftX = p1.x - size * ux + size * 0.5 * uy;
      const leftY = p1.y - size * uy - size * 0.5 * ux;
      const rightX = p1.x - size * ux - size * 0.5 * uy;
      const rightY = p1.y - size * uy + size * 0.5 * ux;
      return (
        <g key={a.id} data-annotation-id={a.id} onClick={(e) => { e.stopPropagation(); setSelectedId(a.id); }}>
          <line x1={p0.x} y1={p0.y} x2={p1.x} y2={p1.y} stroke={a.color} strokeWidth={2} />
          <polygon points={`${p1.x},${p1.y} ${leftX},${leftY} ${rightX},${rightY}`} fill={a.color} />
          {/* hidden midpoint label */}
          <circle cx={mid.x} cy={mid.y} r={0} />
        </g>
      );
    }
    if (a.kind === "freehand") {
      const pts = (g.points as unknown as { x: number; y: number }[]) ?? [];
      const d = pts
        .map((p, i) => {
          const px = ptToPx(p.x, p.y, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
          return `${i === 0 ? "M" : "L"}${px.x.toFixed(1)} ${px.y.toFixed(1)}`;
        })
        .join(" ");
      return <path key={a.id} {...common} d={d} strokeLinecap="round" strokeLinejoin="round" />;
    }
    if (a.kind === "note") {
      const p = ptToPx(g.x, g.y, canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      return (
        <g key={a.id} data-annotation-id={a.id} onClick={(e) => { e.stopPropagation(); setSelectedId(a.id); }}
           style={{ cursor: canWrite ? "pointer" : "default" }}>
          <circle cx={p.x} cy={p.y} r={10} fill={a.color} stroke="white" strokeWidth={1.5} />
          <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={11} fontWeight={700} fill="white">!</text>
          {selectedId === a.id && a.text && (
            <foreignObject x={p.x + 14} y={p.y - 10} width={220} height={120}>
              <div
                className="rounded-md border border-slate-700 bg-black/85 px-2 py-1.5 text-[11px] text-white shadow-lg"
                style={{ maxWidth: 220 }}
              >
                <div className="whitespace-pre-wrap break-words">{a.text}</div>
                <div className="mt-1 text-[9px] text-slate-400">{a.author_email}</div>
              </div>
            </foreignObject>
          )}
        </g>
      );
    }
    return null;
  };

  // Live preview of the in-progress drawing.
  const renderPreview = () => {
    if (!drawing) return null;
    const { kind, startPx, endPx, points } = drawing;
    if (kind === "rect") {
      return (
        <rect
          x={Math.min(startPx.x, endPx.x)}
          y={Math.min(startPx.y, endPx.y)}
          width={Math.abs(endPx.x - startPx.x)}
          height={Math.abs(endPx.y - startPx.y)}
          stroke={activeColor}
          strokeWidth={2}
          strokeDasharray="4 3"
          fill="transparent"
        />
      );
    }
    if (kind === "circle") {
      return (
        <ellipse
          cx={(startPx.x + endPx.x) / 2}
          cy={(startPx.y + endPx.y) / 2}
          rx={Math.abs(endPx.x - startPx.x) / 2}
          ry={Math.abs(endPx.y - startPx.y) / 2}
          stroke={activeColor}
          strokeWidth={2}
          strokeDasharray="4 3"
          fill="transparent"
        />
      );
    }
    if (kind === "arrow") {
      return (
        <line
          x1={startPx.x}
          y1={startPx.y}
          x2={endPx.x}
          y2={endPx.y}
          stroke={activeColor}
          strokeWidth={2}
          strokeDasharray="4 3"
        />
      );
    }
    if (kind === "freehand" && points) {
      const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x} ${p.y}`).join(" ");
      return <path d={d} stroke={activeColor} strokeWidth={2} fill="none" strokeLinecap="round" />;
    }
    return null;
  };

  return (
    <>
      <svg
        ref={svgRef}
        className="absolute inset-0"
        style={{ zIndex: 26, cursor: ownedCursor, pointerEvents: activeKind || pageAnnotations.length > 0 ? "auto" : "none" }}
        width={canvasWidth}
        height={canvasHeight}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onClick={() => setSelectedId(null)}
      >
        {pageAnnotations.map(renderSaved)}
        {renderPreview()}
      </svg>

      {/* Selection handle / delete bubble */}
      {selectedId && canWrite && (
        <div
          className="pointer-events-none absolute left-3 top-3 z-40 flex items-center gap-2 rounded-md bg-black/85 px-2 py-1 text-[11px] text-white shadow-lg"
        >
          <span>Selected — press Delete to remove</span>
          <button
            type="button"
            onClick={() => {
              if (selectedId) void onDelete(selectedId);
              setSelectedId(null);
            }}
            className="pointer-events-auto rounded bg-rose-600 px-2 py-0.5 text-[10px] font-semibold hover:bg-rose-500"
          >
            Delete
          </button>
        </div>
      )}

      {/* Sticky-note composer */}
      {pendingNote && (
        <div
          className="absolute z-40 rounded-lg border border-slate-700 bg-slate-900 p-2 text-white shadow-xl"
          style={{
            left: Math.min(pendingNote.x, canvasWidth - 260),
            top: Math.min(pendingNote.y, canvasHeight - 130),
            width: 250,
          }}
        >
          <textarea
            autoFocus
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Note…"
            rows={3}
            className="w-full rounded border border-slate-700 bg-slate-800 p-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <div className="mt-1 flex justify-end gap-1">
            <button
              type="button"
              onClick={() => {
                setPendingNote(null);
                setNoteText("");
              }}
              className="rounded bg-slate-700 px-2 py-0.5 text-[11px] hover:bg-slate-600"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void confirmNote()}
              className="rounded bg-blue-600 px-2 py-0.5 text-[11px] font-semibold hover:bg-blue-500"
              disabled={!noteText.trim()}
            >
              Pin note
            </button>
          </div>
        </div>
      )}
    </>
  );
}

/** Tiny hook: loads annotations from the engine and exposes CRUD helpers. */
export function useAnnotations(jobId: string, visitorEmail: string | null) {
  const { apiBase } = useViewerApi();
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [loading, setLoading] = useState(true);

  const base = useMemo(() => apiBase.replace(/\/$/, ""), [apiBase]);
  // Detect public vs authed URL shape — /public/{token}/... vs /jobs/{id}/...
  const isPublic = /\/public\/[^/]+/.test(base);

  const headers = useCallback(
    (extra?: Record<string, string>): HeadersInit => {
      const h: Record<string, string> = { "Content-Type": "application/json", ...(extra ?? {}) };
      if (visitorEmail) h["X-Visitor-Email"] = visitorEmail;
      return h;
    },
    [visitorEmail],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${base}/annotations`, { headers: headers() });
      if (resp.ok) setAnnotations(await resp.json());
    } finally {
      setLoading(false);
    }
  }, [base, headers]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = useCallback(
    async (draft: Omit<Annotation, "id" | "author_email">): Promise<Annotation | null> => {
      const resp = await fetch(`${base}/annotations`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          page_num: draft.page_num,
          kind: draft.kind,
          geometry: draft.geometry,
          color: draft.color,
          text: draft.text,
        }),
      });
      if (!resp.ok) return null;
      const row: Annotation = await resp.json();
      setAnnotations((prev) => [...prev, row]);
      return row;
    },
    [base, headers],
  );

  const update = useCallback(
    async (id: string, patch: Partial<Annotation>) => {
      const resp = await fetch(`${base}/annotations/${id}`, {
        method: "PATCH",
        headers: headers(),
        body: JSON.stringify(patch),
      });
      if (resp.ok) {
        const row: Annotation = await resp.json();
        setAnnotations((prev) => prev.map((a) => (a.id === id ? row : a)));
      }
    },
    [base, headers],
  );

  const remove = useCallback(
    async (id: string) => {
      const resp = await fetch(`${base}/annotations/${id}`, {
        method: "DELETE",
        headers: headers(),
      });
      if (resp.ok) setAnnotations((prev) => prev.filter((a) => a.id !== id));
    },
    [base, headers],
  );

  return { annotations, loading, create, update, remove, refresh, isPublic };
}
