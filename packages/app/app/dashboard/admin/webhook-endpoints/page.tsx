"use client";

/**
 * Admin "Webhooks (All Tenants)" page — super-admin cross-tenant CRUD.
 *
 * Lists every webhook endpoint grouped by tenant and lets super admins
 * create / edit / toggle / rotate / test / delete endpoints on any
 * tenant's behalf. The delivery audit (DLQ + per-attempt history + replay)
 * still lives on /dashboard/admin/webhooks.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";
import { NewBearerCard } from "@/components/new-bearer-card";

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

const DEFAULT_EVENTS = "job.completed,job.failed";

export default function AdminWebhookEndpointsPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const pageSize = 100;

  const [createFor, setCreateFor] = useState<{
    tenantId: string;
    tenantName: string;
  } | null>(null);
  const [createUrl, setCreateUrl] = useState("");
  const [createEvents, setCreateEvents] = useState(DEFAULT_EVENTS);
  const [createBusy, setCreateBusy] = useState(false);

  const [newSecret, setNewSecret] = useState<{ title: string; secret: string } | null>(
    null,
  );

  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, string>>({});

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

  async function createEndpoint() {
    if (!createFor) return;
    setCreateBusy(true);
    setError("");
    try {
      const events = createEvents
        .split(",")
        .map((e) => e.trim())
        .filter(Boolean);
      if (events.length === 0) throw new Error("At least one event required.");
      if (!createUrl) throw new Error("URL required.");
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${createFor.tenantId}/webhook-endpoints`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: createUrl, events }),
        },
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      const created = (await resp.json()) as { secret?: string };
      if (created.secret) {
        setNewSecret({
          title: `New webhook signing secret for ${createFor.tenantName}`,
          secret: created.secret,
        });
      }
      setCreateFor(null);
      setCreateUrl("");
      setCreateEvents(DEFAULT_EVENTS);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create endpoint");
    } finally {
      setCreateBusy(false);
    }
  }

  async function toggleActive(row: EndpointRow) {
    setRowBusy(row.id);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${row.tenant_id}/webhook-endpoints/${row.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_active: !row.is_active }),
        },
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to toggle");
    } finally {
      setRowBusy(null);
    }
  }

  async function editUrl(row: EndpointRow) {
    const next = window.prompt("New URL (must be https://)", row.url);
    if (!next || next === row.url) return;
    setRowBusy(row.id);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${row.tenant_id}/webhook-endpoints/${row.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: next }),
        },
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to edit URL");
    } finally {
      setRowBusy(null);
    }
  }

  async function rotateSecret(row: EndpointRow, tenantName: string) {
    if (
      !window.confirm(
        "Rotate the signing secret? Any verifier holding the old one will start rejecting deliveries until you hand off the new secret.",
      )
    ) {
      return;
    }
    setRowBusy(row.id);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${row.tenant_id}/webhook-endpoints/${row.id}/rotate-secret`,
        { method: "POST" },
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      const rotated = (await resp.json()) as { secret?: string };
      if (rotated.secret) {
        setNewSecret({
          title: `Rotated webhook secret for ${tenantName}`,
          secret: rotated.secret,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to rotate secret");
    } finally {
      setRowBusy(null);
    }
  }

  async function testFire(row: EndpointRow) {
    setRowBusy(row.id);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${row.tenant_id}/webhook-endpoints/${row.id}/test`,
        { method: "POST" },
      );
      const body = (await resp.json().catch(() => ({}))) as {
        success?: boolean;
        status_code?: number;
        error?: string;
      };
      setTestResult((prev) => ({
        ...prev,
        [row.id]: body.success
          ? `✓ ${body.status_code ?? "?"} OK`
          : `✗ ${body.status_code ?? "?"} ${body.error ?? "failed"}`,
      }));
    } catch (e) {
      setTestResult((prev) => ({
        ...prev,
        [row.id]: `✗ ${e instanceof Error ? e.message : "failed"}`,
      }));
    } finally {
      setRowBusy(null);
    }
  }

  async function deleteEndpoint(row: EndpointRow) {
    if (
      !window.confirm(
        `Delete webhook endpoint for ${row.url}? Pending deliveries will be lost.`,
      )
    ) {
      return;
    }
    setRowBusy(row.id);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${row.tenant_id}/webhook-endpoints/${row.id}`,
        { method: "DELETE" },
      );
      if (!resp.ok && resp.status !== 204) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
    } finally {
      setRowBusy(null);
    }
  }

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="max-w-7xl">
      <h1 className="font-display text-2xl font-bold">
        Webhook Endpoints — All Tenants
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Cross-tenant CRUD: create / edit / toggle / rotate / test / delete
        endpoints on any tenant&rsquo;s behalf. Delivery audit + dead-letter
        replay lives on{" "}
        <code className="rounded bg-muted px-1 text-xs">/dashboard/admin/webhooks</code>.
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

      {newSecret && (
        <NewBearerCard
          title={newSecret.title}
          secret={newSecret.secret}
          onDismiss={() => setNewSecret(null)}
        />
      )}

      {createFor && (
        <div className="mt-4 rounded-md border bg-card p-3">
          <div className="text-sm font-semibold">
            New endpoint for{" "}
            <span className="font-mono">{createFor.tenantName}</span>
          </div>
          <div className="mt-2 flex flex-col gap-2">
            <input
              type="url"
              value={createUrl}
              placeholder="https://hooks.example.com/lintpdf"
              onChange={(e) => setCreateUrl(e.target.value)}
              className="h-9 w-full rounded-md border px-3 text-sm"
              disabled={createBusy}
            />
            <input
              type="text"
              value={createEvents}
              placeholder="comma-separated events (e.g. job.completed,job.failed)"
              onChange={(e) => setCreateEvents(e.target.value)}
              className="h-9 w-full rounded-md border px-3 text-sm"
              disabled={createBusy}
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={createEndpoint}
                loading={createBusy}
                disabled={createBusy}
              >
                Create
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setCreateFor(null);
                  setCreateUrl("");
                  setCreateEvents(DEFAULT_EVENTS);
                }}
                disabled={createBusy}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : (
        <>
          <div className="mt-6 space-y-4">
            {data?.groups.map((group) => (
              <GroupSection
                key={group.key}
                group={group}
                onCreate={(tenantId, tenantName) => {
                  setCreateFor({ tenantId, tenantName });
                  setNewSecret(null);
                  setCreateUrl("");
                  setCreateEvents(DEFAULT_EVENTS);
                }}
                onToggle={toggleActive}
                onEditUrl={editUrl}
                onRotate={rotateSecret}
                onTest={testFire}
                onDelete={deleteEndpoint}
                rowBusyId={rowBusy}
                testResult={testResult}
              />
            ))}
            {(!data || data.groups.length === 0) && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No webhook endpoints found.
              </p>
            )}
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function GroupSection({
  group,
  onCreate,
  onToggle,
  onEditUrl,
  onRotate,
  onTest,
  onDelete,
  rowBusyId,
  testResult,
}: {
  group: Group;
  onCreate: (tenantId: string, tenantName: string) => void;
  onToggle: (row: EndpointRow) => void;
  onEditUrl: (row: EndpointRow) => void;
  onRotate: (row: EndpointRow, tenantName: string) => void;
  onTest: (row: EndpointRow) => void;
  onDelete: (row: EndpointRow) => void;
  rowBusyId: string | null;
  testResult: Record<string, string>;
}) {
  const [expanded, setExpanded] = useState(true);
  const first = group.items[0];
  const tenantId = first?.tenant_id ?? group.key;
  const tenantName = first?.tenant_name ?? group.label;

  return (
    <div className="overflow-hidden rounded-lg border bg-card">
      <div className="flex w-full items-center gap-3 border-b p-3">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex flex-1 items-center gap-3 text-left hover:bg-muted/30"
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
        <Button
          size="sm"
          variant="secondary"
          onClick={() => onCreate(tenantId, tenantName)}
        >
          New endpoint
        </Button>
      </div>
      {expanded && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="px-3 py-2 font-medium">URL</th>
              <th className="px-3 py-2 font-medium">Events</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Retention (d)</th>
              <th className="px-3 py-2 font-medium">Created</th>
              <th className="px-3 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {group.items.map((h) => {
              const busy = rowBusyId === h.id;
              const last = testResult[h.id];
              return (
                <tr key={h.id} className="border-b hover:bg-muted/30">
                  <td className="max-w-sm truncate px-3 py-2 font-mono text-xs">
                    {h.url}
                    {last && (
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        Last test: {last}
                      </div>
                    )}
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
                  <td className="px-3 py-2 text-right">
                    <div className="flex flex-wrap justify-end gap-1">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => onEditUrl(h)}
                        disabled={busy}
                      >
                        Edit URL
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => onToggle(h)}
                        disabled={busy}
                      >
                        {h.is_active ? "Pause" : "Resume"}
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => onTest(h)}
                        disabled={busy}
                      >
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => onRotate(h, tenantName)}
                        disabled={busy}
                      >
                        Rotate
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => onDelete(h)}
                        disabled={busy}
                      >
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
