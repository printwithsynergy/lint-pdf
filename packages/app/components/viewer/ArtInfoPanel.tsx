/**
 * Art Info — consolidated viewer panel (WS-E).
 *
 * Single place for:
 * - Trim size derived from the dieline centerline (WS-D)
 * - Dieline toggle (show/hide the cut/crease polyline overlay)
 * - Text-layer toggle (show/hide OCR-recovered text bboxes from WS-C)
 * - Swatch list with per-swatch hide toggle + legend/art badge
 *
 * Hide-state persists per (jobId, spotName) in localStorage under
 * `lintpdf:art-info:<jobId>`. The Separations panel reads the same key,
 * so flipping a swatch here instantly hides it there (and vice-versa).
 */

"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  ArtSizeMM,
  DielineResult,
  OCRPage,
  SwatchClassification,
} from "./types";

export interface ArtInfoPanelProps {
  jobId: string;
  dieline: DielineResult | null;
  artSize: ArtSizeMM | null;
  swatches: SwatchClassification[];
  ocrLayer: OCRPage[] | null;
  /** Called when the dieline overlay is toggled. */
  onDielineToggle?: (visible: boolean) => void;
  /** Called when the text-layer overlay is toggled. */
  onTextLayerToggle?: (visible: boolean) => void;
  /** Called when a swatch's hide state flips. */
  onSwatchHideToggle?: (spotName: string, hidden: boolean) => void;
}

type HideMap = Record<string, boolean>;

function storageKey(jobId: string): string {
  return `lintpdf:art-info:${jobId}`;
}

function loadHiddenSwatches(jobId: string): HideMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(storageKey(jobId));
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? parsed : {};
  } catch {
    return {};
  }
}

function saveHiddenSwatches(jobId: string, hidden: HideMap): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(storageKey(jobId), JSON.stringify(hidden));
    // Notify other panels on the same page that state changed.
    window.dispatchEvent(
      new CustomEvent("lintpdf:art-info:change", {
        detail: { jobId, hidden },
      }),
    );
  } catch {
    /* localStorage unavailable — ignore */
  }
}

const DIELINE_SOURCE_LABEL: Record<DielineResult["source"], string> = {
  name: "Spot name match",
  vision: "AI-detected",
  missing: "Not found",
};

const SWATCH_KIND_LABEL: Record<SwatchClassification["kind"], string> = {
  legend: "Legend",
  art: "Art",
  unknown: "Unknown",
};

export function ArtInfoPanel({
  jobId,
  dieline,
  artSize,
  swatches,
  ocrLayer,
  onDielineToggle,
  onTextLayerToggle,
  onSwatchHideToggle,
}: ArtInfoPanelProps): React.ReactElement {
  const [hidden, setHidden] = useState<HideMap>(() =>
    loadHiddenSwatches(jobId),
  );
  const [dielineVisible, setDielineVisible] = useState<boolean>(true);
  const [textLayerVisible, setTextLayerVisible] = useState<boolean>(false);

  // Cross-panel sync — if Separations panel flips a swatch we pick it up.
  useEffect(() => {
    function onChange(ev: Event): void {
      const detail = (ev as CustomEvent<{ jobId: string; hidden: HideMap }>)
        .detail;
      if (!detail || detail.jobId !== jobId) return;
      setHidden({ ...detail.hidden });
    }
    window.addEventListener("lintpdf:art-info:change", onChange);
    return () => window.removeEventListener("lintpdf:art-info:change", onChange);
  }, [jobId]);

  function toggleSwatch(spotName: string): void {
    setHidden((prev) => {
      const next = { ...prev, [spotName]: !prev[spotName] };
      saveHiddenSwatches(jobId, next);
      onSwatchHideToggle?.(spotName, Boolean(next[spotName]));
      return next;
    });
  }

  function toggleDieline(): void {
    const next = !dielineVisible;
    setDielineVisible(next);
    onDielineToggle?.(next);
  }

  function toggleTextLayer(): void {
    const next = !textLayerVisible;
    setTextLayerVisible(next);
    onTextLayerToggle?.(next);
  }

  const ocrPageCount = useMemo(
    () => (ocrLayer ? ocrLayer.length : 0),
    [ocrLayer],
  );
  const ocrBlockCount = useMemo(
    () =>
      ocrLayer
        ? ocrLayer.reduce((n, p) => n + p.blocks.length, 0)
        : 0,
    [ocrLayer],
  );

  return (
    <aside
      aria-label="Art info"
      className="flex flex-col gap-4 p-4 text-sm text-slate-100"
    >
      <header className="flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Art info
        </h2>
      </header>

      {/* Trim size */}
      <section className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wider text-slate-500">
          Trim size
        </span>
        {artSize ? (
          <span className="font-mono text-base text-slate-100">
            {artSize.width_mm.toFixed(1)} × {artSize.height_mm.toFixed(1)} mm
          </span>
        ) : (
          <span className="text-slate-500">
            Unavailable — no dieline detected
          </span>
        )}
      </section>

      {/* Dieline */}
      <section className="flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs uppercase tracking-wider text-slate-500">
            Dieline
          </span>
          <span className="text-slate-200">
            {dieline
              ? DIELINE_SOURCE_LABEL[dieline.source]
              : DIELINE_SOURCE_LABEL.missing}
            {dieline?.spot_name ? (
              <span className="ml-2 rounded bg-slate-800 px-1.5 py-0.5 text-xs font-mono text-slate-300">
                {dieline.spot_name}
              </span>
            ) : null}
          </span>
        </div>
        <button
          type="button"
          onClick={toggleDieline}
          disabled={!dieline || dieline.source === "missing"}
          className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40"
        >
          {dielineVisible ? "Hide" : "Show"}
        </button>
      </section>

      {/* Text layer (OCR) */}
      <section className="flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs uppercase tracking-wider text-slate-500">
            OCR text layer
          </span>
          <span className="text-slate-200">
            {ocrBlockCount > 0
              ? `${ocrBlockCount} blocks on ${ocrPageCount} page${ocrPageCount === 1 ? "" : "s"}`
              : "Not applicable"}
          </span>
        </div>
        <button
          type="button"
          onClick={toggleTextLayer}
          disabled={ocrBlockCount === 0}
          className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40"
        >
          {textLayerVisible ? "Hide" : "Show"}
        </button>
      </section>

      {/* Swatches */}
      <section className="flex flex-col gap-2">
        <span className="text-xs uppercase tracking-wider text-slate-500">
          Swatches
        </span>
        {swatches.length === 0 ? (
          <span className="text-slate-500">No swatches detected</span>
        ) : (
          <ul className="flex flex-col gap-1">
            {swatches.map((sw) => {
              const isHidden = Boolean(hidden[sw.spot_name]);
              return (
                <li
                  key={sw.spot_name}
                  className="flex items-center justify-between gap-2 rounded border border-slate-800 bg-slate-900/40 px-2 py-1"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                        sw.kind === "legend"
                          ? "bg-amber-900/40 text-amber-200"
                          : sw.kind === "art"
                            ? "bg-emerald-900/40 text-emerald-200"
                            : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      {SWATCH_KIND_LABEL[sw.kind]}
                    </span>
                    <span className="truncate font-mono text-xs text-slate-200">
                      {sw.spot_name}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleSwatch(sw.spot_name)}
                    className="rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300 hover:bg-slate-800"
                  >
                    {isHidden ? "Show" : "Hide"}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </aside>
  );
}
