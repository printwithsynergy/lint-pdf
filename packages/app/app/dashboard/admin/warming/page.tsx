"use client";

/**
 * Super-admin tile-warming dashboard.
 *
 * Surfaces the recent warming events + 24h aggregates so an operator
 * can answer "is warming healthy right now?" in ~10 seconds. Keeps
 * the UI deliberately boring: three stacked sections, no charts.
 *
 * Backed by the Next.js proxy at /api/lintpdf/admin/tile-warming/*,
 * which forwards to the engine's super-admin endpoints. When Redis
 * is unavailable the endpoints return status="no_redis" and we
 * render a banner instead of the data.
 */

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface WarmEvent {
  event: string;
  job_id: string;
  tenant_id: string | null;
  page_count: number | null;
  dpi: number | null;
  thumbnails: boolean | null;
  duration_s: number | null;
  error: string | null;
  recorded_at: string;
}

interface TenantWarmSummary {
  tenant_id: string;
  completes: number;
  failures: number;
  pages_total: number;
  p50_duration_s: number | null;
  p95_duration_s: number | null;
  last_event_at: string | null;
}

interface SummaryResponse {
  window_hours: number;
  total_events: number;
  total_completes: number;
  total_failures: number;
  success_rate: number | null;
  p50_duration_s: number | null;
  p95_duration_s: number | null;
  p99_duration_s: number | null;
  top_tenants: TenantWarmSummary[];
  top_errors: { error: string; count: number }[];
  per_tenant: TenantWarmSummary[];
  status: string;
}

interface EventsResponse {
  events: WarmEvent[];
  status: string;
}

const WINDOW_CHOICES: { label: string; hours: number }[] = [
  { label: "1h", hours: 1 },
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
];

function formatDuration(s: number | null): string {
  if (s === null || s === undefined) return "—";
  if (s < 1) return `${Math.round(s * 1000)} ms`;
  if (s < 60) return `${s.toFixed(1)} s`;
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
}

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const diff = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(t).toLocaleString();
}

function shortId(id: string | null | undefined, n = 8): string {
  if (!id) return "—";
  return id.length <= n ? id : `${id.slice(0, n)}…`;
}

export default function AdminWarmingPage() {
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [events, setEvents] = useState<WarmEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [windowHours, setWindowHours] = useState(24);
  const [jobFilter, setJobFilter] = useState("");

  const fetchAll = useCallback(
    async (signal?: AbortSignal): Promise<void> => {
      try {
        const [sumResp, evtResp] = await Promise.all([
          fetch(
            `/api/lintpdf/admin/tile-warming/summary?since_hours=${windowHours}`,
            { signal, cache: "no-store" },
          ),
          fetch(`/api/lintpdf/admin/tile-warming/events?limit=100`, {
            signal,
            cache: "no-store",
          }),
        ]);
        if (sumResp.ok) {
          const body = (await sumResp.json()) as SummaryResponse;
          setSummary(body);
        }
        if (evtResp.ok) {
          const body = (await evtResp.json()) as EventsResponse;
          setEvents(body.events ?? []);
        }
        setError("");
      } catch (e) {
        if (e instanceof Error && e.name === "AbortError") return;
        setError(
          e instanceof Error ? e.message : "Failed to load warming data",
        );
      } finally {
        setLoading(false);
      }
    },
    [windowHours],
  );

  useEffect(() => {
    const ctrl = new AbortController();
    void fetchAll(ctrl.signal);
    return () => ctrl.abort();
  }, [fetchAll]);

  // Polling: summary refreshes every 30 s, events every 5 s. Collapsed
  // here into one 5 s interval — summary is cheap.
  useEffect(() => {
    const id = setInterval(() => {
      void fetchAll();
    }, 5000);
    return () => clearInterval(id);
  }, [fetchAll]);

  const redisDown = summary?.status === "no_redis";
  const filteredEvents = jobFilter
    ? events.filter((ev) => ev.job_id.includes(jobFilter))
    : events;

  if (loading && summary === null) {
    return <SkeletonDashboard type="cards" />;
  }

  return (
    <>
      <h1 className="font-display text-2xl font-bold">Tile Warming</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Background pre-render pipeline — events, aggregates, and a live
        feed. Polls every 5 s.
      </p>

      {redisDown && (
        <div
          role="status"
          data-testid="warming-no-redis"
          className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
        >
          <strong>Warming events require LINTPDF_REDIS_URL.</strong> The
          engine is not persisting events — Railway logs remain the only
          source of truth until Redis is configured.
        </div>
      )}

      {error && !redisDown && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </div>
      )}

      {/* Window size selector */}
      <div
        className="mt-6 flex items-center gap-2"
        data-testid="warming-window-picker"
      >
        <span className="text-sm text-muted-foreground">Window:</span>
        {WINDOW_CHOICES.map((c) => (
          <button
            key={c.hours}
            type="button"
            onClick={() => setWindowHours(c.hours)}
            className={`rounded border px-3 py-1 text-xs font-medium transition ${
              windowHours === c.hours
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-background text-foreground hover:bg-muted"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Summary strip */}
      {summary && !redisDown && (
        <div
          className="mt-4 grid gap-4 sm:grid-cols-2 md:grid-cols-4"
          data-testid="warming-summary"
        >
          <SummaryCard
            label={`Last ${windowHours}h warmed`}
            value={summary.total_completes}
            tone="success"
          />
          <SummaryCard
            label="Failures"
            value={summary.total_failures}
            tone={summary.total_failures > 0 ? "error" : "neutral"}
          />
          <SummaryCard
            label="p95 duration"
            value={formatDuration(summary.p95_duration_s)}
            tone="neutral"
          />
          <SummaryCard
            label="Success rate"
            value={
              summary.success_rate === null
                ? "—"
                : `${Math.round(summary.success_rate * 100)}%`
            }
            tone={
              summary.success_rate !== null && summary.success_rate < 0.95
                ? "error"
                : "success"
            }
          />
        </div>
      )}

      {/* Top errors */}
      {summary && !redisDown && summary.top_errors.length > 0 && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-foreground">
            Top error messages
          </h2>
          <ul
            className="mt-2 divide-y rounded-lg border"
            data-testid="warming-top-errors"
          >
            {summary.top_errors.map((e) => (
              <li
                key={e.error}
                className="flex items-center justify-between px-3 py-2 text-sm"
              >
                <span className="truncate pr-3 text-red-700">{e.error}</span>
                <span className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                  ×{e.count}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Per-tenant health table */}
      {summary && !redisDown && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-foreground">
            Per-tenant health
          </h2>
          {summary.per_tenant.length === 0 ? (
            <p className="mt-2 rounded-lg border p-3 text-sm text-muted-foreground">
              No warming activity in the last {windowHours}h.
            </p>
          ) : (
            <div className="mt-2 overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/30 text-left text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Tenant</th>
                    <th className="px-3 py-2 text-right">Warmed</th>
                    <th className="px-3 py-2 text-right">Failed</th>
                    <th className="px-3 py-2 text-right">Pages</th>
                    <th className="px-3 py-2 text-right">p50</th>
                    <th className="px-3 py-2 text-right">p95</th>
                    <th className="px-3 py-2">Last event</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.per_tenant.map((t) => (
                    <tr key={t.tenant_id} className="border-b last:border-0">
                      <td className="px-3 py-2 font-mono text-xs">
                        {shortId(t.tenant_id)}
                      </td>
                      <td className="px-3 py-2 text-right">{t.completes}</td>
                      <td className="px-3 py-2 text-right">
                        {t.failures > 0 ? (
                          <span className="text-red-700">{t.failures}</span>
                        ) : (
                          t.failures
                        )}
                      </td>
                      <td className="px-3 py-2 text-right">{t.pages_total}</td>
                      <td className="px-3 py-2 text-right">
                        {formatDuration(t.p50_duration_s)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {formatDuration(t.p95_duration_s)}
                      </td>
                      <td className="px-3 py-2 text-muted-foreground">
                        {formatRelative(t.last_event_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Live event feed */}
      {!redisDown && (
        <section className="mt-6">
          <div className="flex items-baseline justify-between">
            <h2 className="text-sm font-semibold text-foreground">
              Live event feed
            </h2>
            <input
              type="text"
              value={jobFilter}
              onChange={(e) => setJobFilter(e.target.value)}
              placeholder="Filter by job_id…"
              data-testid="warming-job-filter"
              className="w-64 rounded border border-border bg-background px-2 py-1 text-xs"
            />
          </div>
          <ul
            className="mt-2 max-h-[480px] divide-y overflow-y-auto rounded-lg border"
            data-testid="warming-event-feed"
          >
            {filteredEvents.length === 0 ? (
              <li className="px-3 py-4 text-center text-sm text-muted-foreground">
                No events to show.
              </li>
            ) : (
              filteredEvents.map((ev, idx) => (
                <li
                  key={`${ev.recorded_at}-${ev.job_id}-${idx}`}
                  data-event-kind={ev.event}
                  className="flex items-center gap-3 px-3 py-2 text-sm"
                >
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                      ev.event === "tile_warm.complete"
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {ev.event === "tile_warm.complete" ? "complete" : "failure"}
                  </span>
                  <span className="font-mono text-xs text-foreground">
                    {shortId(ev.job_id)}
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {shortId(ev.tenant_id, 8)}
                  </span>
                  {ev.page_count !== null && (
                    <span className="text-xs text-muted-foreground">
                      {ev.page_count}p
                    </span>
                  )}
                  <span className="ml-auto text-xs text-muted-foreground">
                    {formatDuration(ev.duration_s)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatRelative(ev.recorded_at)}
                  </span>
                  {ev.error && (
                    <span
                      className="max-w-[30ch] truncate text-xs text-red-700"
                      title={ev.error}
                    >
                      {ev.error}
                    </span>
                  )}
                </li>
              ))
            )}
          </ul>
        </section>
      )}
    </>
  );
}

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone: "success" | "error" | "neutral";
}) {
  const color =
    tone === "success"
      ? "text-green-700"
      : tone === "error"
        ? "text-red-700"
        : "text-foreground";
  return (
    <div className="rounded-lg border p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className={`mt-1 font-display text-2xl font-bold ${color}`}>
        {value}
      </div>
    </div>
  );
}
