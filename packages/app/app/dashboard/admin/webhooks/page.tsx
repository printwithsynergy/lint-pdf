"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface DeadDelivery {
  id: string;
  tenant_id: string;
  webhook_id: string;
  event: string;
  url: string;
  attempt_count: number;
  final_status_code: number;
  success: boolean;
  is_dead: boolean;
  replay_count: number;
  last_error: string | null;
  created_at: string;
  delivered_at: string | null;
}

const PAGE_SIZE = 50;

export default function AdminWebhookDlqPage() {
  const [rows, setRows] = useState<DeadDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const [replaying, setReplaying] = useState<string | null>(null);
  const [replayMessage, setReplayMessage] = useState<string | null>(null);

  const fetchRows = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams({
        page: String(page),
        page_size: String(PAGE_SIZE),
      });
      if (!showAll) qs.set("dead", "true");
      const resp = await fetch(
        `/api/lintpdf/admin/webhook-deliveries?${qs.toString()}`,
      );
      if (!resp.ok) {
        const data = (await resp.json().catch(() => ({}))) as {
          error?: string;
        };
        throw new Error(
          data.error ?? `Failed to load deliveries (${resp.status})`,
        );
      }
      const data = (await resp.json()) as {
        deliveries: DeadDelivery[];
        total: number;
      };
      setRows(data.deliveries ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load deliveries");
    } finally {
      setLoading(false);
    }
  }, [page, showAll]);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  const replay = useCallback(
    async (id: string) => {
      setReplaying(id);
      setReplayMessage(null);
      try {
        const resp = await fetch(
          `/api/lintpdf/admin/webhook-deliveries/${id}/replay`,
          { method: "POST" },
        );
        if (!resp.ok) {
          const data = (await resp.json().catch(() => ({}))) as {
            error?: string;
            detail?: string;
          };
          throw new Error(data.error ?? data.detail ?? `Replay failed (${resp.status})`);
        }
        setReplayMessage(`Replay queued for delivery ${id.slice(0, 8)}.`);
        await fetchRows();
      } catch (e) {
        setReplayMessage(
          e instanceof Error ? e.message : "Replay failed",
        );
      } finally {
        setReplaying(null);
      }
    },
    [fetchRows],
  );

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <h1 className="font-display text-2xl font-bold">Webhook Dead Letters</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Deliveries that exhausted their retries. Replay reissues them against
        the current endpoint URL + secret.
      </p>

      <div className="mt-4 flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={showAll}
            onChange={(e) => {
              setShowAll(e.target.checked);
              setPage(1);
            }}
          />
          Show all deliveries (not just dead)
        </label>
        <Button
          type="button"
          variant="secondary"
          onClick={() => {
            setPage(1);
            fetchRows();
          }}
        >
          Refresh
        </Button>
      </div>

      {replayMessage && (
        <div className="mt-3 rounded-md border border-brand-200 bg-brand-50/60 p-3 text-sm">
          {replayMessage}
        </div>
      )}

      {error && (
        <div className="mt-3 rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard />
      ) : rows.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          {showAll
            ? "No webhook deliveries recorded."
            : "No dead-letter deliveries. All webhooks are healthy."}
        </p>
      ) : (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2">Tenant</th>
                <th className="px-3 py-2">Event</th>
                <th className="px-3 py-2">URL</th>
                <th className="px-3 py-2">Attempts</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Error</th>
                <th className="px-3 py-2">Replays</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="px-3 py-2 font-mono text-xs">
                    {new Date(r.created_at).toISOString().replace("T", " ").slice(0, 19)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {r.tenant_id.slice(0, 8)}
                  </td>
                  <td className="px-3 py-2">{r.event}</td>
                  <td className="px-3 py-2 max-w-xs truncate" title={r.url}>
                    {r.url}
                  </td>
                  <td className="px-3 py-2">{r.attempt_count}</td>
                  <td className="px-3 py-2">
                    <span
                      className={
                        r.is_dead
                          ? "rounded-full bg-destructive/10 px-2 py-0.5 text-xs text-destructive"
                          : r.success
                            ? "rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800"
                            : "rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800"
                      }
                    >
                      {r.is_dead ? "DEAD" : r.success ? "OK" : "FAILED"}
                    </span>
                  </td>
                  <td
                    className="px-3 py-2 max-w-xs truncate text-xs text-muted-foreground"
                    title={r.last_error ?? ""}
                  >
                    {r.last_error ?? "—"}
                  </td>
                  <td className="px-3 py-2">{r.replay_count}</td>
                  <td className="px-3 py-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={replaying === r.id}
                      onClick={() => replay(r.id)}
                    >
                      {replaying === r.id ? "Replaying…" : "Replay"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {total} total · page {page} of {totalPages}
        </span>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
}
