"use client";

/**
 * Admin "Webhooks (All Tenants)" page — super-admin-only cross-tenant view
 * of every webhook endpoint registration. The delivery audit (DLQ / per-
 * attempt history) still lives on /dashboard/admin/webhooks.
 */

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface EndpointRow {
  id: string;
  tenant_id: string;
  tenant_name: string | null;
  url: string;
  events: string[];
  is_active: boolean;
  max_retries: number | null;
  retry_base_delay_seconds: number | null;
  retry_max_delay_seconds: number | null;
  delivery_retention_days: number | null;
  created_at: string;
}

interface Group {
  key: string;
  label: string;
  count: number;
  items: EndpointRow[];
}

interface ListResponse {
  groups: Group[];
  total: number;
  page: number;
  page_size: number;
  group_by: string;
}

export default function AdminWebhookEndpointsPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const pageSize = 100;

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams();
      qs.set("page", String(page));
      qs.set("page_size", String(pageSize));
      qs.set("group_by", "tenant");
      if (q) qs.set("q", q);
      const resp = await fetch(
        `/api/lintpdf/admin/webhook-endpoints?${qs.toString()}`,
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as {
          error?: string;
        };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      setData((await resp.json()) as ListResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load endpoints");
    } finally {
      setLoading(false);
    }
  }, [page, q]);

  useEffect(() => {
    load();
  }, [load]);

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <>
      <h1 className="font-display text-2xl font-bold">
        Webhook Endpoints — All Tenants
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Read-only cross-tenant registration list. Per-delivery attempts and
        dead-letter replay live on the existing /dashboard/admin/webhooks page.
      </p>

      <div className="mt-4 flex items-center gap-2">
        <input
          type="search"
          value={q}
          placeholder="Search URL…"
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          className="h-10 w-full max-w-md rounded-md border px-3 py-2 text-sm"
        />
        <span className="ml-auto text-xs text-muted-foreground">
          {total} endpoint{total === 1 ? "" : "s"}
        </span>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : (
        <>
          <div className="mt-6 space-y-4">
            {data?.groups.map((group) => (
              <GroupSection key={group.key} group={group} />
            ))}
            {(!data || data.groups.length === 0) && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No webhook endpoints found.
              </p>
            )}
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="h-10 rounded-md border px-3 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="h-10 rounded-md border px-3 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}

function GroupSection({ group }: { group: Group }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div className="overflow-hidden rounded-lg border bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-3 border-b p-3 text-left hover:bg-muted/30"
      >
        <span className="truncate font-medium">{group.label}</span>
        <span className="text-xs text-muted-foreground">
          {group.count} endpoint{group.count === 1 ? "" : "s"}
        </span>
        <svg
          className={`ml-auto h-4 w-4 text-muted-foreground transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {expanded && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="px-3 py-2 font-medium">URL</th>
              <th className="px-3 py-2 font-medium">Events</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Retention (d)</th>
              <th className="px-3 py-2 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {group.items.map((h) => (
              <tr key={h.id} className="border-b hover:bg-muted/30">
                <td className="max-w-sm truncate px-3 py-2 font-mono text-xs">
                  {h.url}
                </td>
                <td className="px-3 py-2 text-xs">{h.events.join(", ")}</td>
                <td className="px-3 py-2 text-xs">
                  <span
                    className={`rounded px-1.5 py-0.5 font-medium ${
                      h.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {h.is_active ? "active" : "paused"}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {h.delivery_retention_days ?? "∞"}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {new Date(h.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
