"use client";

import { useCallback, useEffect, useState } from "react";
import { use } from "react";
import Link from "next/link";
import { SkeletonDashboard } from "@/components/skeleton";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { useToast } from "@thinkneverland/pixie-dust-ui";

interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event: string;
  url: string;
  attempt_count: number;
  final_status_code: number;
  success: boolean;
  last_error: string | null;
  created_at: string;
  delivered_at: string | null;
}

interface DeliveryDetail extends WebhookDelivery {
  payload: Record<string, unknown>;
}

interface ListResponse {
  deliveries: WebhookDelivery[];
  total: number;
  page: number;
  page_size: number;
}

export default function WebhookDeliveriesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [list, setList] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [successFilter, setSuccessFilter] = useState<"all" | "failed">("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<DeliveryDetail | null>(null);
  const [replaying, setReplaying] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchDeliveries = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ page: String(page), page_size: "25" });
      if (successFilter === "failed") qs.set("success", "false");
      const resp = await fetch(
        `/api/lintpdf/webhook-endpoints/${id}/deliveries?${qs.toString()}`,
      );
      if (!resp.ok) throw new Error("Failed to load deliveries");
      setList(await resp.json());
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load", "error");
    } finally {
      setLoading(false);
    }
  }, [id, page, successFilter, toast]);

  useEffect(() => {
    fetchDeliveries();
  }, [fetchDeliveries]);

  async function openDetail(deliveryId: string) {
    if (expanded === deliveryId) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(deliveryId);
    setDetail(null);
    try {
      const resp = await fetch(
        `/api/lintpdf/webhook-endpoints/deliveries/${deliveryId}`,
      );
      if (!resp.ok) throw new Error("Failed to load delivery");
      setDetail(await resp.json());
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to load", "error");
      setExpanded(null);
    }
  }

  async function replay(deliveryId: string) {
    setReplaying(deliveryId);
    try {
      const resp = await fetch(
        `/api/lintpdf/webhook-endpoints/deliveries/${deliveryId}/replay`,
        { method: "POST" },
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ error: "Replay failed" }));
        throw new Error(body.error ?? "Replay failed");
      }
      toast("Replay queued", "success");
      await fetchDeliveries();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Replay failed", "error");
    } finally {
      setReplaying(null);
    }
  }

  if (loading && !list) {
    return <SkeletonDashboard type="table" />;
  }

  const totalPages = list ? Math.max(1, Math.ceil(list.total / list.page_size)) : 1;

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Webhook deliveries</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Every dispatch attempt for this endpoint. Click a row to inspect
            the signed payload, replay failed deliveries to re-fire the same
            body against the original URL.
          </p>
        </div>
        <Link href="/dashboard/webhooks">
          <Button variant="secondary">Back to webhooks</Button>
        </Link>
      </div>

      <div className="mt-4 flex gap-2">
        <Button
          variant={successFilter === "all" ? "default" : "secondary"}
          size="sm"
          onClick={() => {
            setSuccessFilter("all");
            setPage(1);
          }}
        >
          All
        </Button>
        <Button
          variant={successFilter === "failed" ? "default" : "secondary"}
          size="sm"
          onClick={() => {
            setSuccessFilter("failed");
            setPage(1);
          }}
        >
          Failed only
        </Button>
      </div>

      <div className="mt-4 overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted/30">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Event</th>
              <th className="px-3 py-2 text-left font-medium">Status</th>
              <th className="px-3 py-2 text-left font-medium">Attempts</th>
              <th className="px-3 py-2 text-left font-medium">Created</th>
              <th className="px-3 py-2 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {list?.deliveries.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                  No deliveries recorded yet.
                </td>
              </tr>
            ) : (
              list?.deliveries.map((d) => (
                <>
                  <tr
                    key={d.id}
                    className="cursor-pointer border-b last:border-b-0 hover:bg-muted/20"
                    onClick={() => openDetail(d.id)}
                  >
                    <td className="px-3 py-2 font-mono text-xs">{d.event}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs ${
                          d.success
                            ? "bg-success/10 text-success"
                            : "bg-destructive/10 text-destructive"
                        }`}
                      >
                        {d.success ? "200" : d.final_status_code || "error"}
                      </span>
                    </td>
                    <td className="px-3 py-2">{d.attempt_count}</td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">
                      {new Date(d.created_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          replay(d.id);
                        }}
                        loading={replaying === d.id}
                      >
                        Replay
                      </Button>
                    </td>
                  </tr>
                  {expanded === d.id && (
                    <tr key={`${d.id}-detail`} className="border-b last:border-b-0">
                      <td colSpan={5} className="bg-muted/10 px-3 py-3">
                        {!detail ? (
                          <p className="text-xs text-muted-foreground">Loading…</p>
                        ) : (
                          <div className="space-y-2 text-xs">
                            {d.last_error && (
                              <p className="text-destructive">
                                Last error: {d.last_error}
                              </p>
                            )}
                            <p className="text-muted-foreground">URL: {d.url}</p>
                            <details>
                              <summary className="cursor-pointer select-none">
                                Signed payload
                              </summary>
                              <pre className="mt-2 max-h-96 overflow-auto rounded bg-background p-2 font-mono text-xs">
                                {JSON.stringify(detail.payload, null, 2)}
                              </pre>
                            </details>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>

      {list && list.total > 0 && (
        <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Page {list.page} of {totalPages} — {list.total} total
          </span>
          <div className="flex gap-1">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              Prev
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
