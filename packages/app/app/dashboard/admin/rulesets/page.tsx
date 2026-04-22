"use client";

/**
 * Admin "Rulesets (All Tenants)" page — super-admin cross-tenant view.
 *
 * Fetches /api/lintpdf/admin/profiles (engine's /api/v1/admin/profiles)
 * so super admins can see every ruleset (built-in + each tenant's
 * custom profiles) and jump into the tenant-scoped editor to author
 * or tweak a custom profile on that tenant's behalf.
 *
 * System (built-in) profiles are shipped in the engine code registry
 * and cannot be edited from the UI — the "Edit" button is only shown
 * for per-tenant custom profiles.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface ProfileSummary {
  profile_id: string;
  name: string;
  description?: string | null;
  conformance?: string | null;
  workflow?: string | null;
  is_builtin: boolean;
}

interface TenantProfiles {
  tenant_id: string;
  tenant_name: string | null;
  profiles: ProfileSummary[];
}

interface ListResponse {
  system: ProfileSummary[];
  tenants: TenantProfiles[];
}

export default function AdminRulesetsPage() {
  const [data, setData] = useState<ListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch("/api/lintpdf/admin/profiles");
      if (!resp.ok) {
        const body = (await resp.json().catch(() => ({}))) as {
          error?: string;
        };
        throw new Error(body.error ?? `Failed (${resp.status})`);
      }
      setData((await resp.json()) as ListResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profiles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const systemCount = data?.system.length ?? 0;
  const tenantCustomCount =
    data?.tenants.reduce((acc, t) => acc + t.profiles.length, 0) ?? 0;

  return (
    <div className="max-w-7xl">
      <h1 className="font-display text-2xl font-bold">
        Rulesets — All Tenants
      </h1>
      <p className="mt-1 text-sm text-muted-foreground">
        System profiles ship with the engine. Per-tenant custom profiles are
        authored through this page (as admin) or through the tenant&rsquo;s own{" "}
        <code className="rounded bg-muted px-1 text-xs">/dashboard/rulesets</code>{" "}
        page.
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
          <section className="mt-6 rounded-lg border bg-card">
            <header className="flex items-center gap-3 border-b p-3">
              <h2 className="font-semibold">System profiles</h2>
              <span className="text-xs text-muted-foreground">
                {systemCount} built-in
              </span>
            </header>
            <div className="p-3">
              {data?.system.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No system profiles registered.
                </p>
              ) : (
                <ul className="space-y-1">
                  {data?.system.map((p) => (
                    <li
                      key={p.profile_id}
                      className="flex items-center justify-between rounded-md border p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{p.name}</span>
                          <code className="text-xs text-muted-foreground">
                            {p.profile_id}
                          </code>
                          <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                            built-in
                          </span>
                        </div>
                        {p.description && (
                          <p className="truncate text-sm text-muted-foreground">
                            {p.description}
                          </p>
                        )}
                      </div>
                      <span className="ml-4 text-xs text-muted-foreground">
                        read-only
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="mt-6 rounded-lg border bg-card">
            <header className="flex items-center gap-3 border-b p-3">
              <h2 className="font-semibold">Per-tenant custom profiles</h2>
              <span className="text-xs text-muted-foreground">
                {tenantCustomCount} across {data?.tenants.length ?? 0}{" "}
                tenant{data?.tenants.length === 1 ? "" : "s"}
              </span>
            </header>
            <div className="p-3">
              {data?.tenants.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No tenants have authored custom profiles yet.
                </p>
              ) : (
                <div className="space-y-4">
                  {data?.tenants.map((t) => (
                    <div key={t.tenant_id} className="rounded-lg border">
                      <header className="flex items-center gap-3 border-b bg-muted/30 p-3">
                        <span className="font-semibold">
                          {t.tenant_name ?? t.tenant_id}
                        </span>
                        <code className="text-xs text-muted-foreground">
                          {t.tenant_id}
                        </code>
                        <span className="ml-auto text-xs text-muted-foreground">
                          {t.profiles.length} profile
                          {t.profiles.length === 1 ? "" : "s"}
                        </span>
                      </header>
                      <ul className="divide-y">
                        {t.profiles.map((p) => (
                          <li
                            key={p.profile_id}
                            className="flex items-center justify-between p-3"
                          >
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{p.name}</span>
                                <code className="text-xs text-muted-foreground">
                                  {p.profile_id}
                                </code>
                                <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
                                  custom
                                </span>
                              </div>
                              {p.description && (
                                <p className="truncate text-sm text-muted-foreground">
                                  {p.description}
                                </p>
                              )}
                            </div>
                            <div className="ml-4 flex shrink-0 gap-2">
                              <Link
                                href={`/dashboard/rulesets?tenant=${t.tenant_id}&profile=${p.profile_id}`}
                              >
                                <Button variant="secondary" size="sm">
                                  Edit
                                </Button>
                              </Link>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
