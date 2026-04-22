"use client";

/**
 * Admin "API Keys (All Tenants)" page — super-admin cross-tenant CRUD.
 *
 * Lists every API key across tenants (grouped by tenant) and lets
 * super admins mint a new key for a tenant or revoke an existing one.
 * Proxies through /api/lintpdf/admin/api-keys (list) and
 * /api/lintpdf/admin/tenants/:tenantId/keys{,/:keyId} for CRUD.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface ApiKeyRow {
  id: string;
  tenant_id: string;
  tenant_name: string | null;
  label: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

interface Group {
  key: string;
  label: string;
  count: number;
  items: ApiKeyRow[];
}

interface ListResponse {
  groups: Group[];
  total: number;
  page: number;
  page_size: number;
  group_by: string;
}

export default function AdminApiKeysPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const pageSize = 100;

  const [mintFor, setMintFor] = useState<{ tenantId: string; tenantName: string } | null>(null);
  const [mintLabel, setMintLabel] = useState("");
  const [mintBusy, setMintBusy] = useState(false);
  const [mintedKey, setMintedKey] = useState<string | null>(null);

  const [revokeBusy, setRevokeBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams();
      qs.set("page", String(page));
      qs.set("page_size", String(pageSize));
      qs.set("group_by", "tenant");
      if (q) qs.set("q", q);
      const resp = await fetch(`/api/lintpdf/admin/api-keys?${qs.toString()}`);
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as {
          error?: string;
        };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      setData((await resp.json()) as ListResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }, [page, q]);

  useEffect(() => {
    load();
  }, [load]);

  async function mintKey() {
    if (!mintFor) return;
    setMintBusy(true);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${mintFor.tenantId}/keys`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label: mintLabel || "Admin-minted" }),
        },
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      const created = (await resp.json()) as { key?: string };
      setMintedKey(created.key ?? null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to mint API key");
    } finally {
      setMintBusy(false);
    }
  }

  async function revokeKey(tenantId: string, keyId: string, label: string) {
    if (!window.confirm(`Revoke API key "${label}"? The tenant will have to re-authenticate any caller using it.`)) {
      return;
    }
    setRevokeBusy(keyId);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${tenantId}/keys/${keyId}`,
        { method: "DELETE" },
      );
      if (!resp.ok && resp.status !== 204) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to revoke API key");
    } finally {
      setRevokeBusy(null);
    }
  }

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="max-w-7xl">
      <h1 className="font-display text-2xl font-bold">API Keys — All Tenants</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Cross-tenant view with mint + revoke. Use this to help a tenant
        rotate a key they&apos;ve lost access to.
      </p>

      <div className="mt-4 flex items-center gap-2">
        <input
          type="search"
          value={q}
          placeholder="Search label or key prefix…"
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          className="h-10 w-full max-w-md rounded-md border px-3 py-2 text-sm"
        />
        <span className="ml-auto text-xs text-muted-foreground">
          {total} key{total === 1 ? "" : "s"}
        </span>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {mintedKey && (
        <div className="mt-4 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm">
          <div className="font-semibold text-emerald-800">New key minted</div>
          <p className="mt-1 text-emerald-700">
            Copy it now — it&apos;s shown only once and cannot be retrieved later.
          </p>
          <code className="mt-2 block break-all rounded bg-white p-2 font-mono text-xs">
            {mintedKey}
          </code>
          <button
            type="button"
            className="mt-2 text-xs text-emerald-800 underline"
            onClick={() => setMintedKey(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {mintFor && (
        <div className="mt-4 rounded-md border bg-card p-3">
          <div className="text-sm font-semibold">
            Mint API key for{" "}
            <span className="font-mono">{mintFor.tenantName}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={mintLabel}
              placeholder="Label (optional)"
              onChange={(e) => setMintLabel(e.target.value)}
              className="h-9 flex-1 rounded-md border px-3 text-sm"
              disabled={mintBusy}
            />
            <Button
              size="sm"
              onClick={mintKey}
              loading={mintBusy}
              disabled={mintBusy}
            >
              Mint
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setMintFor(null);
                setMintLabel("");
              }}
              disabled={mintBusy}
            >
              Cancel
            </Button>
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
                onMint={(tenantId, tenantName) => {
                  setMintFor({ tenantId, tenantName });
                  setMintLabel("");
                  setMintedKey(null);
                }}
                onRevoke={revokeKey}
                revokeBusyKeyId={revokeBusy}
              />
            ))}
            {(!data || data.groups.length === 0) && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No API keys found.
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
  onMint,
  onRevoke,
  revokeBusyKeyId,
}: {
  group: Group;
  onMint: (tenantId: string, tenantName: string) => void;
  onRevoke: (tenantId: string, keyId: string, label: string) => void;
  revokeBusyKeyId: string | null;
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
            {group.count} key{group.count === 1 ? "" : "s"}
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
          onClick={() => onMint(tenantId, tenantName)}
        >
          Mint key
        </Button>
      </div>
      {expanded && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="px-3 py-2 font-medium">Label</th>
              <th className="px-3 py-2 font-medium">Prefix</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Last used</th>
              <th className="px-3 py-2 font-medium">Created</th>
              <th className="px-3 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {group.items.map((k) => (
              <tr key={k.id} className="border-b hover:bg-muted/30">
                <td className="px-3 py-2 font-medium">{k.label}</td>
                <td className="px-3 py-2 font-mono text-xs">
                  {k.key_prefix}…
                </td>
                <td className="px-3 py-2 text-xs">
                  <span
                    className={`rounded px-1.5 py-0.5 font-medium ${
                      k.is_active
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {k.is_active ? "active" : "revoked"}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {k.last_used_at
                    ? new Date(k.last_used_at).toLocaleDateString()
                    : "—"}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {new Date(k.created_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-2 text-right">
                  {k.is_active && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => onRevoke(k.tenant_id, k.id, k.label)}
                      loading={revokeBusyKeyId === k.id}
                      disabled={revokeBusyKeyId === k.id}
                    >
                      Revoke
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
