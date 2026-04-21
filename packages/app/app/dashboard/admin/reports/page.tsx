"use client";

/**
 * Admin "Reports (All Tenants)" page — super-admin-only cross-tenant view
 * of every report token (share-link) minted. Clicking a token row opens its
 * public URL in a new tab.
 */

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface TokenRow {
  id: string;
  tenant_id: string;
  tenant_name: string | null;
  job_id: string;
  token: string;
  format: string;
  brand_mode: string | null;
  allow_annotations: boolean;
  accessed_count: number;
  last_accessed_at: string | null;
  expires_at: string | null;
  created_at: string;
}

interface Group {
  key: string;
  label: string;
  count: number;
  items: TokenRow[];
}

interface ListResponse {
  groups: Group[];
  total: number;
  page: number;
  page_size: number;
  group_by: string;
}

export default function AdminReportsPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [formatFilter, setFormatFilter] = useState("");
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
      if (formatFilter) qs.set("format", formatFilter);
      const resp = await fetch(
        `/api/lintpdf/admin/report-tokens?${qs.toString()}`,
      );
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as {
          error?: string;
        };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      setData((await resp.json()) as ListResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report tokens");
    } finally {
      setLoading(false);
    }
  }, [page, q, formatFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <>
      <h1 className="font-display text-2xl font-bold">
        Reports — All Tenants
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Read-only cross-tenant view of every share-link token ever minted.
        Click a token to open the public report in a new tab.
      </p>

      <div className="mt-4 flex items-center gap-2">
        <input
          type="search"
          value={q}
          placeholder="Search token or format…"
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
          className="h-10 w-full max-w-md rounded-md border px-3 py-2 text-sm"
        />
        <select
          value={formatFilter}
          onChange={(e) => {
            setFormatFilter(e.target.value);
            setPage(1);
          }}
          className="h-10 rounded-md border px-3 py-2 text-sm"
        >
          <option value="">All formats</option>
          <option value="html">html</option>
          <option value="pdf">pdf</option>
          <option value="json">json</option>
          <option value="xml">xml</option>
          <option value="annotated_pdf">annotated_pdf</option>
          <option value="annotated_pdf_markup">annotated_pdf_markup</option>
        </select>
        <span className="ml-auto text-xs text-muted-foreground">
          {total} token{total === 1 ? "" : "s"}
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
                No report tokens found.
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

function publicUrl(token: string, format: string): string {
  // Mirror the engine's public-report URL shape. The token-only path works for
  // every format; the format path segment makes it obvious from the URL what
  // renderer will respond.
  return `/r/${token}/${format}`;
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
          {group.count} token{group.count === 1 ? "" : "s"}
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
              <th className="px-3 py-2 font-medium">Token</th>
              <th className="px-3 py-2 font-medium">Format</th>
              <th className="px-3 py-2 font-medium">Brand</th>
              <th className="px-3 py-2 font-medium">Views</th>
              <th className="px-3 py-2 font-medium">Last accessed</th>
              <th className="px-3 py-2 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {group.items.map((t) => (
              <tr key={t.id} className="border-b hover:bg-muted/30">
                <td className="px-3 py-2 font-mono text-xs">
                  <a
                    href={publicUrl(t.token, t.format)}
                    target="_blank"
                    rel="noreferrer"
                    className="text-primary hover:underline"
                  >
                    {t.token.slice(0, 12)}…
                  </a>
                </td>
                <td className="px-3 py-2 text-xs">
                  <span className="rounded bg-muted px-1.5 py-0.5 font-medium uppercase">
                    {t.format}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {t.brand_mode ?? "—"}
                  {t.allow_annotations ? " · ✎" : ""}
                </td>
                <td className="px-3 py-2 text-xs">{t.accessed_count}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {t.last_accessed_at
                    ? new Date(t.last_accessed_at).toLocaleDateString()
                    : "—"}
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {new Date(t.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
