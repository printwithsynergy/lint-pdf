"use client";

import { useCallback, useEffect, useState } from "react";
import { ConfirmDialog } from "@thinkneverland/pixie-dust-ui";
import { Button, Input, Dropdown, DropdownItem, DropdownLabel } from "@thinkneverland/pixie-dust-ui";

interface TenantInfo {
  id: string;
  name: string;
  slug: string;
}

interface MeResponse {
  user: {
    id: string;
    isSuperAdmin: boolean;
    tenants: { id: string; name: string; slug: string; role: string }[];
  };
  impersonating: {
    tenantId: string;
    tenantName: string;
    tenantSlug: string;
  } | null;
}

/**
 * Super Admin Toolbar — shown at the top of the dashboard when logged in as a super admin.
 *
 * Features:
 * 1. "Customer View" toggle — switches the super admin to their own tenant with full features
 * 2. "Assist Customer" — dropdown to pick a customer tenant to help configure
 * 3. Impersonation banner — shows when assisting a customer, with "Stop Assisting" button
 */
export function SuperAdminToolbar() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [allTenants, setAllTenants] = useState<TenantInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [switching, setSwitching] = useState(false);

  // Confirm dialog state for start impersonation
  const [confirmStartOpen, setConfirmStartOpen] = useState(false);
  const [confirmStartTarget, setConfirmStartTarget] = useState<string | null>(null);
  const [confirmStartLabel, setConfirmStartLabel] = useState("");

  // Confirm dialog state for stop impersonation
  const [confirmStopOpen, setConfirmStopOpen] = useState(false);

  const fetchMe = useCallback(async () => {
    try {
      const resp = await fetch("/api/auth/me");
      if (resp.ok) {
        const data = await resp.json();
        if (data.user?.isSuperAdmin) {
          setMe(data);
        }
      }
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTenants = useCallback(async () => {
    try {
      const resp = await fetch(
        "/api/lintpdf/admin/tenants?page=1&page_size=200",
      );
      if (resp.ok) {
        const data = await resp.json();
        setAllTenants(
          (data.tenants ?? []).map((t: Record<string, string>) => ({
            id: t.id,
            name: t.name,
            slug: t.slug ?? (t.id ?? "").slice(0, 8),
          })),
        );
      }
    } catch {
      // Non-critical
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  async function startImpersonation(tenantId: string) {
    setSwitching(true);
    try {
      const resp = await fetch("/api/auth/impersonate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenantId }),
      });
      if (resp.ok) {
        window.location.reload();
      }
    } catch (e) {
      console.error("Failed to start impersonation:", e);
    } finally {
      setSwitching(false);
    }
  }

  async function stopImpersonation() {
    setSwitching(true);
    try {
      await fetch("/api/auth/impersonate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenantId: null }),
      });
      window.location.href = "/dashboard/admin";
    } catch (e) {
      console.error("Failed to stop impersonation:", e);
    } finally {
      setSwitching(false);
    }
  }

  // Don't render anything for non-super-admins or while loading
  if (loading || !me) return null;

  const impersonating = me.impersonating;
  const filteredTenants = allTenants.filter(
    (t) =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.id.includes(searchQuery),
  );

  return (
    <>
      {/* Impersonation banner */}
      {impersonating && (
        <div className="bg-amber-500 text-amber-950 px-4 py-2 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-semibold">Assisting Customer:</span>
            <span>{impersonating.tenantName}</span>
            <span className="text-amber-800">
              (All changes are logged under your admin account)
            </span>
          </div>
          <Button
            size="sm"
            onClick={() => setConfirmStopOpen(true)}
            loading={switching}
            className="bg-amber-900 text-amber-50 hover:bg-amber-800"
          >
            Stop Assisting
          </Button>
        </div>
      )}

      {/* Super admin toolbar */}
      {!impersonating && (
        <div className="bg-violet-600 text-white px-4 py-2 text-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="rounded bg-violet-500 px-2 py-0.5 text-xs font-bold">
              SUPER ADMIN
            </span>
            <span className="text-violet-200">
              You have access to all features without subscription limits.
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Dropdown
              trigger={
                <Button
                  size="sm"
                  className="bg-violet-500 hover:bg-violet-400"
                  onClick={() => {
                    if (allTenants.length === 0) {
                      fetchTenants();
                    }
                  }}
                >
                  Assist Customer
                </Button>
              }
              align="right"
            >
              <div className="p-2">
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search tenants..."
                  autoFocus
                />
              </div>
              <DropdownLabel>Tenants</DropdownLabel>
              <div className="max-h-64 overflow-y-auto">
                {filteredTenants.length === 0 ? (
                  <p className="p-3 text-center text-xs text-gray-500">
                    {allTenants.length === 0
                      ? "Loading tenants..."
                      : "No tenants match"}
                  </p>
                ) : (
                  filteredTenants.map((t) => (
                    <DropdownItem
                      key={t.id}
                      onClick={() => {
                        setConfirmStartTarget(t.id);
                        setConfirmStartLabel(`${t.name} (${t.slug})`);
                        setConfirmStartOpen(true);
                      }}
                    >
                      <span className="font-medium">{t.name}</span>
                      <span className="ml-auto text-xs text-gray-500">
                        {t.id.slice(0, 8)}
                      </span>
                    </DropdownItem>
                  ))
                )}
              </div>
            </Dropdown>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmStartOpen}
        onClose={() => {
          setConfirmStartOpen(false);
          setConfirmStartTarget(null);
          setConfirmStartLabel("");
        }}
        onConfirm={async () => {
          if (confirmStartTarget) await startImpersonation(confirmStartTarget);
          setConfirmStartOpen(false);
          setConfirmStartTarget(null);
          setConfirmStartLabel("");
        }}
        title="Start assisting customer?"
        description={`You will view the dashboard for "${confirmStartLabel}" as them. All changes are logged under your admin account.`}
        variant="default"
        confirmLabel="Start Assisting"
        loading={switching}
      />

      <ConfirmDialog
        open={confirmStopOpen}
        onClose={() => setConfirmStopOpen(false)}
        onConfirm={async () => {
          await stopImpersonation();
          setConfirmStopOpen(false);
        }}
        title="Stop assisting?"
        description="Stop assisting this customer and return to admin view?"
        variant="default"
        confirmLabel="Stop Assisting"
        loading={switching}
      />
    </>
  );
}
