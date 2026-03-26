"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { Button } from "@thinkneverland/pixie-dust-ui";

interface TenantSummary {
  id: string;
  name: string;
  plan: string;
  is_active: boolean;
  contact_email: string;
  rate_limit_daily: number;
  created_at: string;
}

const PLANS = ["free", "starter", "growth", "scale", "enterprise"];
const STATUSES = ["active", "suspended"];

export default function AdminTenantsPage() {
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 50;

  const fetchTenants = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants?page=${page}&page_size=${pageSize}`,
      );
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(
          (data as { error?: string }).error ??
            `Failed to load tenants (${resp.status})`,
        );
      }
      const data = await resp.json();
      setTenants(data.tenants ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  async function handlePlanChange(tenantId: string, newPlan: string) {
    try {
      await fetch(`/api/lintpdf/admin/tenants/${tenantId}/plan`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: newPlan }),
      });
      await fetchTenants();
    } catch {
      setError("Failed to update plan");
    }
  }

  async function handleStatusChange(tenantId: string, newStatus: string) {
    try {
      await fetch(`/api/lintpdf/admin/tenants/${tenantId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: newStatus === "active" }),
      });
      await fetchTenants();
    } catch {
      setError("Failed to update status");
    }
  }

  async function handleAssist(tenantId: string) {
    try {
      const resp = await fetch("/api/auth/impersonate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenantId }),
      });
      if (resp.ok) {
        // Reload dashboard to show the customer's view
        window.location.href = "/dashboard/preflight";
      }
    } catch {
      setError("Failed to start customer assist");
    }
  }

  const totalPages = Math.ceil(total / pageSize);

  return (
    <main className="p-8 max-w-6xl">
      <h1 className="font-display text-2xl font-bold">All Tenants</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        {total} total organizations
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="pb-2 font-medium">Organization</th>
                  <th className="pb-2 font-medium">Plan</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Daily Limit</th>
                  <th className="pb-2 font-medium">Created</th>
                  <th className="pb-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => (
                  <tr key={t.id} className="border-b">
                    <td className="py-2">
                      <div className="font-medium">{t.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {t.contact_email}
                      </div>
                    </td>
                    <td className="py-2">
                      <select
                        value={t.plan}
                        onChange={(e) => handlePlanChange(t.id, e.target.value)}
                        className="rounded border px-2 py-1 text-xs"
                      >
                        {PLANS.map((p) => (
                          <option key={p} value={p}>
                            {p.toUpperCase()}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2">
                      <select
                        value={t.is_active ? "active" : "suspended"}
                        onChange={(e) =>
                          handleStatusChange(t.id, e.target.value)
                        }
                        className="rounded border px-2 py-1 text-xs"
                      >
                        {STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 text-xs">
                      {t.rate_limit_daily?.toLocaleString()}
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2">
                      <Button
                        size="sm"
                        onClick={() => handleAssist(t.id)}
                        className="bg-violet-600 text-white hover:bg-violet-500"
                      >
                        Assist
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
    </main>
  );
}
