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
  /** Email used when posting new comments. Share-link visitors supply
   *  this through the email-gate modal in ``PdfViewer``; dashboard
   *  users can leave it null (the API fills it from the session). */
  visitorEmail?: string | null;
  /** Deep-link annotation id to auto-select after annotations load. */
  autoOpenAnnotationId?: string | null;
  /** Fires once after the deep-link annotation has been opened, so the
   *  caller can clear the URL fragment. */
  onAutoOpenConsumed?: () => void;
}

/** A reply on a markup thread. */
export interface AnnotationComment {
  id: string;
  annotation_id: string;
  author_email: string;
  body: string;
  created_at: string;
  updated_at: string;
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
  onDelete,
  canWrite,
  visitorEmail,
  autoOpenAnnotationId,
  onAutoOpenConsumed,
}: AnnotationLayerProps) {
  const { apiBase } = useViewerApi();
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

  // Open the annotation referenced by the URL deep-link fragment
  // (``#ann=<id>``) once it lands in the list. We do not auto-flip
  // pages — the caller is responsible for navigating to the correct
  // page before passing ``autoOpenAnnotationId`` through.
  useEffect(() => {
    if (!autoOpenAnnotationId) return;
    const match = annotations.find((a) => a.id === autoOpenAnnotationId);
    if (!match) return;
    if (match.page_num !== pageNum) return;
    setSelectedId(match.id);
    onAutoOpenConsumed?.();
  }, [autoOpenAnnotationId, annotations, pageNum, onAutoOpenConsumed]);

  const selectedAnnotation = useMemo(
    () => (selectedId ? pageAnnotations.find((a) => a.id === selectedId) ?? null : null),
    [selectedId, pageAnnotations],
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
    // noUncheckedIndexedAccess makes every ``g["x0"]`` a ``number |
    // undefined`` lookup. We fall back to 0 so a malformed geometry row
    // degrades to a zero-size shape instead of a runtime NaN.
    // k is supplied by the renderer below (literal geometry field names).
    // eslint-disable-next-line security/detect-object-injection
    const n = (k: string): number => g[k] ?? 0;
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
      const p0 = ptToPx(n("x0"), n("y0"), canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const p1 = ptToPx(n("x1"), n("y1"), canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const x = Math.min(p0.x, p1.x);
      const y = Math.min(p0.y, p1.y);
      const w = Math.abs(p1.x - p0.x);
      const h = Math.abs(p1.y - p0.y);
      return <rect key={a.id} {...common} x={x} y={y} width={w} height={h} />;
    }
    if (a.kind === "circle") {
      const c = ptToPx(n("cx"), n("cy"), canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const rx = (n("rx") / pageWidthPts) * canvasWidth;
      const ry = (n("ry") / pageHeightPts) * canvasHeight;
      return <ellipse key={a.id} {...common} cx={c.x} cy={c.y} rx={rx} ry={ry} />;
    }
    if (a.kind === "arrow") {
      const p0 = ptToPx(n("x0"), n("y0"), canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      const p1 = ptToPx(n("x1"), n("y1"), canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
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
      const p = ptToPx(n("x"), n("y"), canvasWidth, canvasHeight, pageWidthPts, pageHeightPts);
      // Thread panel is rendered as a DOM sibling of the SVG (not a
      // foreignObject) so its textarea, buttons, and scrollable list
      // play nicely with the surrounding layout and don't fight SVG
      // event bubbling rules. We still render the marker here.
      return (
        <g key={a.id} data-annotation-id={a.id} onClick={(e) => { e.stopPropagation(); setSelectedId(a.id); }}
           style={{ cursor: canWrite ? "pointer" : "default" }}>
          <circle cx={p.x} cy={p.y} r={10} fill={a.color} stroke="white" strokeWidth={1.5} />
          <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={11} fontWeight={700} fill="white">!</text>
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

      {/* Comment thread panel for the currently selected note */}
      {selectedAnnotation && selectedAnnotation.kind === "note" && (
        <NoteThreadPanel
          annotation={selectedAnnotation}
          canvasWidth={canvasWidth}
          canvasHeight={canvasHeight}
          pageWidthPts={pageWidthPts}
          pageHeightPts={pageHeightPts}
          visitorEmail={visitorEmail ?? null}
          canWrite={canWrite}
          apiBase={apiBase}
          onClose={() => setSelectedId(null)}
        />
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
export function useAnnotations(_jobId: string, visitorEmail: string | null) {
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

/** Hook: loads + mutates the threaded comments on a single annotation.
 *
 * Uses ``apiBase`` so both the authenticated (``/jobs/{id}``) and public
 * (``/public/{token}``) surfaces work without branching in callers. The
 * ``X-Visitor-Email`` header is only attached when the caller actually
 * provides one — dashboard writers leave it blank.
 */
export function useAnnotationComments(
  annotationId: string | null,
  visitorEmail: string | null,
) {
  const { apiBase } = useViewerApi();
  const [comments, setComments] = useState<AnnotationComment[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const base = useMemo(() => apiBase.replace(/\/$/, ""), [apiBase]);

  const headers = useCallback(
    (extra?: Record<string, string>): HeadersInit => {
      const h: Record<string, string> = { "Content-Type": "application/json", ...(extra ?? {}) };
      if (visitorEmail) h["X-Visitor-Email"] = visitorEmail;
      return h;
    },
    [visitorEmail],
  );

  const refresh = useCallback(async () => {
    if (!annotationId) {
      setComments([]);
      return;
    }
    setLoading(true);
    try {
      const resp = await fetch(`${base}/annotations/${annotationId}/comments`, {
        headers: headers(),
      });
      if (resp.ok) setComments(await resp.json());
    } finally {
      setLoading(false);
    }
  }, [annotationId, base, headers]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const create = useCallback(
    async (body: string): Promise<AnnotationComment | null> => {
      if (!annotationId || !body.trim()) return null;
      setSaving(true);
      try {
        const resp = await fetch(`${base}/annotations/${annotationId}/comments`, {
          method: "POST",
          headers: headers(),
          body: JSON.stringify({ body: body.trim() }),
        });
        if (!resp.ok) return null;
        const row: AnnotationComment = await resp.json();
        setComments((prev) => [...prev, row]);
        return row;
      } finally {
        setSaving(false);
      }
    },
    [annotationId, base, headers],
  );

  const remove = useCallback(
    async (id: string): Promise<boolean> => {
      if (!annotationId) return false;
      const resp = await fetch(`${base}/annotations/${annotationId}/comments/${id}`, {
        method: "DELETE",
        headers: headers(),
      });
      if (resp.ok) {
        setComments((prev) => prev.filter((c) => c.id !== id));
        return true;
      }
      return false;
    },
    [annotationId, base, headers],
  );

  return { comments, loading, saving, create, remove, refresh };
}

interface NoteThreadPanelProps {
  annotation: Annotation;
  canvasWidth: number;
  canvasHeight: number;
  pageWidthPts: number;
  pageHeightPts: number;
  visitorEmail: string | null;
  canWrite: boolean;
  apiBase: string;
  onClose: () => void;
}

function NoteThreadPanel({
  annotation,
  canvasWidth,
  canvasHeight,
  pageWidthPts,
  pageHeightPts,
  visitorEmail,
  canWrite,
  onClose,
}: NoteThreadPanelProps) {
  const g = annotation.geometry as Record<string, number>;
  const px = ptToPx(
    g.x ?? 0,
    g.y ?? 0,
    canvasWidth,
    canvasHeight,
    pageWidthPts,
    pageHeightPts,
  );
  const { comments, saving, create, remove } = useAnnotationComments(
    annotation.id,
    visitorEmail,
  );
  const [draft, setDraft] = useState("");

  // Anchor the panel just to the right of the note pin; clamp so it
  // never overflows the canvas.
  const panelW = 280;
  const panelH = 260;
  const left = Math.min(px.x + 18, canvasWidth - panelW - 4);
  const top = Math.min(Math.max(px.y - 20, 4), canvasHeight - panelH - 4);

  return (
    <div
      className="absolute z-40 flex flex-col gap-2 rounded-lg border border-slate-700 bg-slate-900/95 p-3 text-white shadow-xl"
      style={{ left, top, width: panelW, maxHeight: panelH }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-slate-400">
            Note
          </div>
          <div className="whitespace-pre-wrap break-words text-xs">
            {annotation.text ?? ""}
          </div>
          <div className="mt-0.5 text-[9px] text-slate-500">
            {annotation.author_email}
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded px-1 text-xs text-slate-400 hover:bg-slate-800 hover:text-white"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-1.5 overflow-y-auto border-t border-slate-800 pt-2">
        {comments.length === 0 && (
          <div className="text-[10px] text-slate-500">No replies yet.</div>
        )}
        {comments.map((c) => {
          const canDelete = canWrite && (!visitorEmail || c.author_email === visitorEmail);
          return (
            <div
              key={c.id}
              className="rounded bg-slate-800/60 px-2 py-1 text-[11px]"
            >
              <div className="mb-0.5 flex items-center justify-between text-[9px] text-slate-400">
                <span className="truncate">{c.author_email}</span>
                <span>{new Date(c.created_at).toLocaleString()}</span>
              </div>
              <div className="whitespace-pre-wrap break-words">{c.body}</div>
              {canDelete && (
                <button
                  type="button"
                  onClick={() => void remove(c.id)}
                  className="mt-0.5 text-[9px] text-rose-400 hover:text-rose-300"
                >
                  Delete
                </button>
              )}
            </div>
          );
        })}
      </div>

      {canWrite && (
        <div className="flex flex-col gap-1 border-t border-slate-800 pt-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={visitorEmail ? "Reply…" : "Reply (email required)"}
            rows={2}
            disabled={saving || !visitorEmail}
            className="w-full resize-none rounded border border-slate-700 bg-slate-800 p-1.5 text-[11px] text-white focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <div className="flex items-center justify-end gap-1">
            <button
              type="button"
              disabled={!draft.trim() || saving || !visitorEmail}
              onClick={async () => {
                const row = await create(draft);
                if (row) setDraft("");
              }}
              className="rounded bg-blue-600 px-2 py-0.5 text-[11px] font-semibold hover:bg-blue-500 disabled:opacity-50"
            >
              {saving ? "Posting…" : "Post"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
