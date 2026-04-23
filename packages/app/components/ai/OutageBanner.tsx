/**
 * AI outage banner — surfaces the reactive sliding-window detector
 * from the engine (WS-B). Polls `/api/v1/ai/health` every 60s and
 * renders a visible banner when the response is `degraded`.
 *
 * Intentionally passive: the banner never blocks the UI or the
 * submit flow. Non-AI preflight keeps running during a Claude
 * outage; AI checks just no-op and emit LPDF_AI_QUOTA_EXCEEDED /
 * LPDF_FEATURE_LOCKED findings as usual.
 */

"use client";

import { useEffect, useState } from "react";

const POLL_INTERVAL_MS = 60_000;
// Default to the app-relative proxy; override via `endpoint` prop in
// contexts (viewer, desktop) that talk directly to the engine.
const HEALTH_URL = "/api/lintpdf/ai/health";

type HealthStatus = "ok" | "degraded" | "unknown";

export interface OutageBannerProps {
  /** Override the health endpoint (mostly for tests). */
  endpoint?: string;
  /** Override the poll interval in ms. */
  intervalMs?: number;
}

export function OutageBanner({
  endpoint = HEALTH_URL,
  intervalMs = POLL_INTERVAL_MS,
}: OutageBannerProps = {}): React.ReactElement | null {
  const [status, setStatus] = useState<HealthStatus>("unknown");

  useEffect(() => {
    let cancelled = false;

    async function poll(): Promise<void> {
      try {
        const res = await fetch(endpoint, { cache: "no-store" });
        if (!res.ok) return;
        const body = (await res.json()) as { status?: string };
        if (cancelled) return;
        setStatus(body.status === "degraded" ? "degraded" : "ok");
      } catch {
        // Network flap — don't flip the banner on a single failure;
        // the engine is the source of truth.
      }
    }

    void poll();
    const id = window.setInterval(() => void poll(), intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [endpoint, intervalMs]);

  if (status !== "degraded") return null;

  return (
    <div
      role="status"
      className="flex items-center gap-3 border-b border-amber-500/30 bg-amber-950/60 px-4 py-2 text-sm text-amber-100"
    >
      <svg
        aria-hidden
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <span>
        <strong>AI checks are temporarily degraded.</strong> Preflight still
        runs; AI-backed audits and inspectors may be paused until service
        recovers.
      </span>
    </div>
  );
}
