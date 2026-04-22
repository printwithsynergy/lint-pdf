"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
  entitlement_overrides?: Record<string, unknown> | null;
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

  async function handleEntitlementToggle(
    tenantId: string,
    key: "desktop_app_enabled" | "ai_audit_enabled",
    enabled: boolean,
  ) {
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${tenantId}/entitlements`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ [key]: enabled }),
        },
      );
      if (!resp.ok) {
        throw new Error(`Failed (${resp.status})`);
      }
      await fetchTenants();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : `Failed to update ${key}`,
      );
    }
  }

  const handleDesktopToggle = (tenantId: string, enabled: boolean) =>
    handleEntitlementToggle(tenantId, "desktop_app_enabled", enabled);
  const handleAuditToggle = (tenantId: string, enabled: boolean) =>
    handleEntitlementToggle(tenantId, "ai_audit_enabled", enabled);

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
    <>
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
                  <th className="pb-2 font-medium">Desktop App</th>
                  <th className="pb-2 font-medium">AI Audit</th>
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
                    <td className="py-2">
                      <label className="inline-flex items-center gap-2 text-xs">
                        <input
                          type="checkbox"
                          checked={Boolean(
                            (t.entitlement_overrides as
                              | { desktop_app_enabled?: boolean }
                              | null
                              | undefined)?.desktop_app_enabled,
                          )}
                          onChange={(e) =>
                            handleDesktopToggle(t.id, e.target.checked)
                          }
                        />
                        <span>Enabled</span>
                      </label>
                    </td>
                    <td className="py-2">
                      <label
                        className="inline-flex items-center gap-2 text-xs"
                        title={
                          // Default-on when the plan (Scale / Enterprise)
                          // sets `ai_audit_enabled: true` and the tenant
                          // hasn't overridden it. Checkbox state reflects
                          // the override only — unchecked for Scale means
                          // "inherit plan default (ON)", checked
                          // for Growth means "force ON despite the plan".
                          "Per-tenant override. Leave unchecked to inherit the plan default (Scale + Enterprise = on). Check to force ON regardless of plan."
                        }
                      >
                        <input
                          type="checkbox"
                          checked={Boolean(
                            (t.entitlement_overrides as
                              | { ai_audit_enabled?: boolean }
                              | null
                              | undefined)?.ai_audit_enabled,
                          )}
                          onChange={(e) =>
                            handleAuditToggle(t.id, e.target.checked)
                          }
                        />
                        <span>Override</span>
                      </label>
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/dashboard/admin/tenants/${t.id}`}
                          className="rounded border px-2 py-1 text-xs hover:bg-muted"
                          title="Edit every entitlement for this tenant"
                        >
                          Edit
                        </Link>
                        <Button
                          size="sm"
                          onClick={() => handleAssist(t.id)}
                          className="bg-violet-600 text-white hover:bg-violet-500"
                        >
                          Assist
                        </Button>
                      </div>
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
    </>
  );
}
