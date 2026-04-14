"use client";

import { useEffect, useRef, useState } from "react";

/** Shape returned by ``GET /api/v1/viewer/jobs/{id}/tile-warming``.
 *
 * Kept in sync with :class:`TileWarmingStatusResponse` on the engine
 * side (packages/engine/src/lintpdf/api/routes/viewer.py).
 */
export interface TileWarmingStatus {
  job_id: string;
  /**
   * - ``pending`` — job not COMPLETE yet; nothing to warm.
   * - ``in_progress`` — worker rendering tiles into S3.
   * - ``complete`` — every page tile cached.
   * - ``failed`` — worker crashed; ``error`` may carry a message.
   * - ``disabled`` — warming is off (no Redis or feature-flag off).
   */
  status: "pending" | "in_progress" | "complete" | "failed" | "disabled";
  rendered: number;
  total: number;
  dpi: number;
  percent: number;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
}

/**
 * Poll ``{apiBase}/tile-warming`` until warming settles. Returns the
 * most recent status plus a ``terminal`` flag the caller can use to
 * hide the progress badge.
 */
export function useTileWarmingStatus(
  apiBase: string | null,
  /** Poll interval in ms. Default 1500 — fast enough to feel live
   *  without hammering the engine. */
  intervalMs: number = 1500,
): { status: TileWarmingStatus | null; terminal: boolean } {
  const [status, setStatus] = useState<TileWarmingStatus | null>(null);
  const terminalRef = useRef(false);

  useEffect(() => {
    if (!apiBase) return;
    terminalRef.current = false;
    let cancelled = false;
    let timerId: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      if (cancelled) return;
      try {
        const resp = await fetch(`${apiBase}/tile-warming`, {
          cache: "no-store",
        });
        if (resp.ok) {
          const body: TileWarmingStatus = await resp.json();
          if (cancelled) return;
          setStatus(body);
          if (
            body.status === "complete" ||
            body.status === "failed" ||
            body.status === "disabled"
          ) {
            terminalRef.current = true;
            return;
          }
        }
      } catch {
        // Network glitch — retry next tick.
      }
      timerId = setTimeout(poll, intervalMs);
    }

    void poll();
    return () => {
      cancelled = true;
      if (timerId !== null) clearTimeout(timerId);
    };
  }, [apiBase, intervalMs]);

  return { status, terminal: terminalRef.current };
}

/**
 * Prefetch every page tile into the browser's HTTP cache.
 *
 * The engine sends ``Cache-Control: public, max-age=86400`` on tile
 * responses, so a plain ``fetch(url)`` populates the browser cache and
 * subsequent renders of ``<img src>`` resolve instantly from local
 * memory / disk — click-to-paint drops to <20 ms.
 *
 * Concurrency is capped at
 * ``navigator.hardwareConcurrency ?? 4`` so we don't saturate mobile
 * connections. Adjacent pages are prefetched first so a reviewer
 * who immediately flips to page 2 still hits the cache even when
 * the full pass hasn't finished.
 */
export function useTilePrefetch(
  apiBase: string | null,
  pageCount: number,
  /** When false, don't run the prefetcher — let the page-canvas
   *  resolve tiles on demand. Typically set false while backend
   *  warming is still ``in_progress``. */
  enabled: boolean,
  /** The currently-visible page (1-indexed). Prefetch order radiates
   *  outward from this page. */
  anchorPage: number = 1,
  /** Tile DPI to prefetch. Defaults to the viewer's default (150). */
  dpi: number = 150,
): { prefetched: number; total: number } {
  const [prefetched, setPrefetched] = useState(0);

  useEffect(() => {
    if (!apiBase || !enabled || pageCount <= 0) {
      setPrefetched(0);
      return;
    }

    // Build a page order that radiates outward from anchorPage so the
    // reviewer's most-likely-next pages cache first.
    const order: number[] = [];
    const seen = new Set<number>();
    const push = (n: number) => {
      if (n >= 1 && n <= pageCount && !seen.has(n)) {
        seen.add(n);
        order.push(n);
      }
    };
    push(anchorPage);
    for (let delta = 1; delta <= pageCount; delta++) {
      push(anchorPage - delta);
      push(anchorPage + delta);
    }

    const hw =
      typeof navigator !== "undefined" && navigator.hardwareConcurrency
        ? navigator.hardwareConcurrency
        : 4;
    const concurrency = Math.max(1, Math.min(hw, 6));

    let cancelled = false;
    let nextIdx = 0;
    let done = 0;
    setPrefetched(0);

    const worker = async () => {
      while (!cancelled) {
        const idx = nextIdx++;
        if (idx >= order.length) return;
        // idx is a local monotonic counter bounded above by order.length — safe index.
        // eslint-disable-next-line security/detect-object-injection
        const page = order[idx]!;
        try {
          await fetch(`${apiBase}/pages/${page}/tile?dpi=${dpi}`, {
            cache: "force-cache",
            // Don't need the response body in JS — the browser HTTP
            // cache holds the bytes. Drain the stream so the TCP
            // connection frees up for the next request.
            keepalive: false,
          }).then((r) => r.arrayBuffer().catch(() => null));
        } catch {
          // Ignore — a single prefetch failure shouldn't poison the batch.
        }
        if (cancelled) return;
        done += 1;
        setPrefetched(done);
      }
    };

    const workers = Array.from({ length: concurrency }, () => worker());
    void Promise.all(workers);

    return () => {
      cancelled = true;
    };
  }, [apiBase, enabled, pageCount, anchorPage, dpi]);

  return { prefetched, total: pageCount };
}
