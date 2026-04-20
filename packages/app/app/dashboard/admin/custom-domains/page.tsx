"use client";

import { useCallback, useEffect, useState } from "react";

interface CustomDomainRow {
  scope: "tenant" | "brand_profile";
  tenant_id: string;
  tenant_name: string;
  brand_profile_id: string | null;
  brand_profile_name: string | null;
  domain: string;
  verified: boolean;
  requested_at: string | null;
}

interface ListResponse {
  pending: CustomDomainRow[];
  active: CustomDomainRow[];
}

export default function AdminCustomDomainsPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const fetchRows = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch("/api/lintpdf/admin/custom-domains");
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? `HTTP ${resp.status}`);
      }
      setData((await resp.json()) as ListResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchRows();
  }, [fetchRows]);

  async function patchDomain(
    row: CustomDomainRow,
    body: { domain?: string | null; verified?: boolean },
  ) {
    const key = `${row.scope}-${row.brand_profile_id ?? row.tenant_id}`;
    setBusyKey(key);
    try {
      const url =
        row.scope === "tenant"
          ? `/api/lintpdf/admin/tenants/${row.tenant_id}/custom-domain`
          : `/api/lintpdf/admin/brand-profiles/${row.brand_profile_id}/custom-domain`;
      const resp = await fetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const b = (await resp.json().catch(() => ({}))) as {
          error?: string;
          detail?: string;
        };
        throw new Error(b.detail ?? b.error ?? `HTTP ${resp.status}`);
      }
      await fetchRows();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyKey(null);
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">White-Label Custom Domains</h1>
        <p className="mt-2 text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <main className="max-w-5xl p-8">
      <h1 className="text-2xl font-bold">White-Label Custom Domains</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Approve or revoke tenant custom report domains. The DNS probe runs every
        5 minutes and auto-activates pending domains whose CNAME resolves to
        edge.lintpdf.com; use the buttons below to override.
      </p>

      {error && (
        <div className="mt-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold">
          Pending ({data?.pending.length ?? 0})
        </h2>
        {data && data.pending.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            No pending domains.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-3 py-2 text-left">Scope</th>
                  <th className="px-3 py-2 text-left">Tenant</th>
                  <th className="px-3 py-2 text-left">Profile</th>
                  <th className="px-3 py-2 text-left">Domain</th>
                  <th className="px-3 py-2 text-left">Requested</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data?.pending.map((row) => {
                  const key = `${row.scope}-${row.brand_profile_id ?? row.tenant_id}`;
                  return (
                    <tr key={key} className="border-t">
                      <td className="px-3 py-2">{row.scope}</td>
                      <td className="px-3 py-2">{row.tenant_name}</td>
                      <td className="px-3 py-2">
                        {row.brand_profile_name ?? "—"}
                      </td>
                      <td className="px-3 py-2 font-mono">{row.domain}</td>
                      <td className="px-3 py-2 text-xs">
                        {row.requested_at
                          ? new Date(row.requested_at).toLocaleString()
                          : "—"}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <button
                          className="mr-2 rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                          disabled={busyKey === key}
                          onClick={() =>
                            patchDomain(row, { verified: true })
                          }
                        >
                          Mark Active
                        </button>
                        <button
                          className="rounded-md border border-red-300 bg-red-50 px-6 py-2.5 text-sm font-medium text-red-800 hover:bg-red-100 disabled:opacity-50"
                          disabled={busyKey === key}
                          onClick={() =>
                            patchDomain(row, { domain: "" })
                          }
                        >
                          Reject
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">
          Active ({data?.active.length ?? 0})
        </h2>
        {data && data.active.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">
            No active domains.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-3 py-2 text-left">Scope</th>
                  <th className="px-3 py-2 text-left">Tenant</th>
                  <th className="px-3 py-2 text-left">Profile</th>
                  <th className="px-3 py-2 text-left">Domain</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data?.active.map((row) => {
                  const key = `${row.scope}-${row.brand_profile_id ?? row.tenant_id}`;
                  return (
                    <tr key={key} className="border-t">
                      <td className="px-3 py-2">{row.scope}</td>
                      <td className="px-3 py-2">{row.tenant_name}</td>
                      <td className="px-3 py-2">
                        {row.brand_profile_name ?? "—"}
                      </td>
                      <td className="px-3 py-2 font-mono">{row.domain}</td>
                      <td className="px-3 py-2 text-right">
                        <button
                          className="rounded-md border border-amber-300 bg-amber-50 px-6 py-2.5 text-sm font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-50"
                          disabled={busyKey === key}
                          onClick={() =>
                            patchDomain(row, { verified: false })
                          }
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
