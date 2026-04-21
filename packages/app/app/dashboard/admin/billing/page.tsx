"use client";

/**
 * Admin Metered Resources console.
 *
 * Surfaces everything an operator needs to manage AI credits + file
 * packs for a specific tenant:
 *
 *  1. Tenant picker (combobox over the admin tenants list, URL-stable
 *     via ``?tenant={id}``).
 *  2. Plan + entitlement summary — shows the plan-default allotment
 *     alongside any ``monthly_*_override`` so you can see the net.
 *  3. Two monthly-override inputs (credits, files) with "Plan default"
 *     reset.
 *  4. Two direct-grant forms (credits, files) — source=admin_grant,
 *     no Stripe, immediate.
 *  5. Active-packages table with revoke action and source badges.
 *
 * All UI components come from ``@thinkneverland/pixie-dust-ui`` so
 * the admin dashboard inherits the active theme tokens (primary,
 * accent, muted, card, etc.) and dark-mode flips come for free.
 */

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  ConfirmDialog,
  EmptyState,
  FormField,
  Input,
  Select,
  useToast,
} from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface TenantSummary {
  id: string;
  name: string;
  plan: string;
  is_active: boolean;
  contact_email: string | null;
  entitlement_overrides?: Record<string, unknown> | null;
  monthly_ai_credits_override?: number | null;
  monthly_files_override?: number | null;
}

interface MeteredPackage {
  id: string;
  kind: "credits" | "files";
  source: "plan_monthly" | "purchase" | "admin_grant" | "trial";
  credits_purchased: number;
  credits_remaining: number;
  price_paid: number;
  purchased_at: string | null;
  expires_at: string | null;
  stripe_session_id: string | null;
  billing_period_start: string | null;
}

// Plan-default monthly allotments mirror PLAN_LIMITS in the engine.
// Kept here (not fetched) so the summary renders instantly before the
// tenant detail request returns.
const PLAN_DEFAULTS: Record<string, { credits: number; files: number }> = {
  free: { credits: 0, files: 50 },
  viewer: { credits: 0, files: 50 },
  starter: { credits: 100, files: 500 },
  growth: { credits: 500, files: 2500 },
  scale: { credits: 2000, files: 10000 },
  enterprise: { credits: 10000, files: 100000 },
};

export default function AdminBillingPage() {
  return (
    <Suspense fallback={<SkeletonDashboard type="form" />}>
      <AdminBillingPageInner />
    </Suspense>
  );
}

function AdminBillingPageInner() {
  const { toast } = useToast();
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [tenantId, setTenantId] = useState<string>("");
  const [tenantQuery, setTenantQuery] = useState<string>("");
  const [packages, setPackages] = useState<MeteredPackage[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [loadingPackages, setLoadingPackages] = useState(false);
  const [pendingRevoke, setPendingRevoke] = useState<MeteredPackage | null>(null);

  // URL-stable selection so operators can share deep links.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const initial = params.get("tenant") ?? "";
    setTenantId(initial);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (tenantId) url.searchParams.set("tenant", tenantId);
    else url.searchParams.delete("tenant");
    window.history.replaceState(null, "", url.toString());
  }, [tenantId]);

  const fetchTenants = useCallback(async () => {
    setLoadingTenants(true);
    try {
      const resp = await fetch("/api/lintpdf/admin/tenants?page=1&page_size=200");
      if (!resp.ok) throw new Error(`Failed to load tenants (${resp.status})`);
      const data = await resp.json();
      setTenants(data.tenants ?? []);
    } catch (e) {
      toast(
        `Failed to load tenants: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    } finally {
      setLoadingTenants(false);
    }
  }, [toast]);

  const fetchPackages = useCallback(async () => {
    if (!tenantId) {
      setPackages([]);
      return;
    }
    setLoadingPackages(true);
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${tenantId}/metered-packages`,
      );
      if (!resp.ok) throw new Error(`Failed to load packages (${resp.status})`);
      const data = await resp.json();
      setPackages(data.packages ?? []);
    } catch (e) {
      toast(
        `Failed to load packages: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    } finally {
      setLoadingPackages(false);
    }
  }, [tenantId, toast]);

  useEffect(() => {
    void fetchTenants();
  }, [fetchTenants]);
  useEffect(() => {
    void fetchPackages();
  }, [fetchPackages]);

  const tenant = useMemo(
    () => tenants.find((t) => t.id === tenantId) ?? null,
    [tenants, tenantId],
  );

  const planDefaults = (tenant
    ? PLAN_DEFAULTS[tenant.plan.toLowerCase()]
    : undefined) ?? { credits: 0, files: 0 };

  const creditsEffective =
    tenant?.monthly_ai_credits_override ?? planDefaults.credits;
  const filesEffective =
    tenant?.monthly_files_override ?? planDefaults.files;

  const tenantOptions = useMemo(() => {
    const q = tenantQuery.trim().toLowerCase();
    const filtered = q
      ? tenants.filter(
          (t) =>
            t.name.toLowerCase().includes(q) ||
            t.id.toLowerCase().includes(q) ||
            (t.contact_email ?? "").toLowerCase().includes(q),
        )
      : tenants;
    return filtered.slice(0, 100).map((t) => ({
      value: t.id,
      label: `${t.name} · ${t.plan} · ${t.id.slice(0, 8)}…`,
    }));
  }, [tenants, tenantQuery]);

  async function setOverride(kind: "credits" | "files", value: number | null) {
    if (!tenantId) return;
    try {
      const path = `/api/lintpdf/admin/tenants/${tenantId}/${kind}/monthly-override`;
      const resp = await fetch(path, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credits: value }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      toast(
        `${kind === "credits" ? "AI credits" : "Files"} override ${
          value === null ? "cleared" : `set to ${value.toLocaleString()}`
        } — takes effect at next invoice.paid for this tenant.`,
        "success",
      );
      await fetchTenants();
    } catch (e) {
      toast(
        `Override failed: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    }
  }

  async function grantPack(kind: "credits" | "files", amount: number) {
    if (!tenantId || amount <= 0) return;
    try {
      const path = `/api/lintpdf/admin/tenants/${tenantId}/${kind}/grant`;
      const body =
        kind === "credits"
          ? { credit_amount: amount, price_paid: 0 }
          : { files_granted: amount, price_paid: 0 };
      const resp = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error(await resp.text());
      toast(
        `Granted +${amount.toLocaleString()} ${kind} — package is active immediately; no Stripe charge created.`,
        "success",
      );
      await fetchPackages();
    } catch (e) {
      toast(
        `Grant failed: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    }
  }

  async function revokePackage(pkg: MeteredPackage) {
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${tenantId}/metered-packages/${pkg.id}`,
        { method: "DELETE" },
      );
      if (!resp.ok && resp.status !== 204) throw new Error(await resp.text());
      toast(
        `Package revoked — ${
          pkg.source === "purchase"
            ? "issue a Stripe refund separately if appropriate."
            : "plan-monthly packages regrant on the next invoice.paid."
        }`,
        "success",
      );
      await fetchPackages();
    } catch (e) {
      toast(
        `Revoke failed: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    } finally {
      setPendingRevoke(null);
    }
  }

  if (loadingTenants) return <SkeletonDashboard type="table" />;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-foreground">
          Metered Resources — Admin
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Set monthly overrides, grant prepaid packs, and revoke packages for
          any tenant. Overrides take effect at the next{" "}
          <code className="rounded bg-muted px-1">invoice.paid</code> webhook;
          grants and revokes are immediate.
        </p>
      </header>

      {/* ── Tenant picker ── */}
      <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Tenant
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FormField label="Filter">
            <Input
              value={tenantQuery}
              onChange={(e) => setTenantQuery(e.target.value)}
              placeholder="Search by name, email, or UUID…"
            />
          </FormField>
          <FormField label="Select tenant">
            <Select
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
            >
              <option value="">— pick a tenant —</option>
              {tenantOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </FormField>
        </div>

        {tenant && (
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Stat label="Plan" value={tenant.plan} capitalize />
            <Stat
              label="Contact"
              value={tenant.contact_email ?? "—"}
              wrap
            />
            <Stat
              label="Credits / month"
              value={creditsEffective.toLocaleString()}
              sublabel={
                tenant.monthly_ai_credits_override != null
                  ? `override (plan default: ${planDefaults.credits})`
                  : `plan default`
              }
            />
            <Stat
              label="Files / month"
              value={filesEffective.toLocaleString()}
              sublabel={
                tenant.monthly_files_override != null
                  ? `override (plan default: ${planDefaults.files})`
                  : `plan default`
              }
            />
          </div>
        )}
      </section>

      {tenant && (
        <>
          {/* ── Monthly overrides ── */}
          <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <h2 className="mb-1 text-lg font-semibold text-foreground">
              Monthly overrides
            </h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Set a per-tenant replacement for the plan default. Reset to
              revert to the plan value. Takes effect at the next{" "}
              <code className="rounded bg-muted px-1">invoice.paid</code>.
            </p>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <OverrideRow
                label="Monthly AI credits"
                placeholder={`plan default: ${planDefaults.credits}`}
                currentValue={tenant.monthly_ai_credits_override}
                onApply={(v) => setOverride("credits", v)}
                onReset={() => setOverride("credits", null)}
              />
              <OverrideRow
                label="Monthly files"
                placeholder={`plan default: ${planDefaults.files}`}
                currentValue={tenant.monthly_files_override}
                onApply={(v) => setOverride("files", v)}
                onReset={() => setOverride("files", null)}
              />
            </div>
          </section>

          {/* ── Direct grants ── */}
          <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <h2 className="mb-1 text-lg font-semibold text-foreground">
              Direct grants
            </h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Insert a free package (<code className="rounded bg-muted px-1">source=admin_grant</code>).
              No Stripe charge. Typical use: VIP seeding, make-good for outages.
            </p>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <GrantRow label="Credits" onGrant={(n) => grantPack("credits", n)} />
              <GrantRow label="Files" onGrant={(n) => grantPack("files", n)} />
            </div>
          </section>

          {/* ── Active packages table ── */}
          <section className="rounded-lg border border-border bg-card shadow-sm">
            <header className="flex items-center justify-between border-b border-border px-5 py-3">
              <h2 className="text-lg font-semibold text-foreground">
                Packages for {tenant.name}
              </h2>
              <Button variant="secondary" onClick={fetchPackages}>
                Refresh
              </Button>
            </header>
            {loadingPackages ? (
              <div className="p-5 text-sm text-muted-foreground">
                Loading packages…
              </div>
            ) : packages.length === 0 ? (
              <EmptyState
                title="No packages yet"
                description="The tenant has never had a credit or file pack allocated. Grant one above, or wait for the next invoice.paid to seed monthly allotments."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-5 py-2">Kind</th>
                      <th className="px-5 py-2">Source</th>
                      <th className="px-5 py-2 text-right">Total</th>
                      <th className="px-5 py-2 text-right">Remaining</th>
                      <th className="px-5 py-2 text-right">Paid (USD)</th>
                      <th className="px-5 py-2">Purchased</th>
                      <th className="px-5 py-2">Expires</th>
                      <th className="px-5 py-2 text-right"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {packages.map((p) => (
                      <tr
                        key={p.id}
                        className="border-t border-border hover:bg-muted/30"
                      >
                        <td className="px-5 py-3">
                          <Badge variant={p.kind === "credits" ? "default" : "secondary"}>
                            {p.kind}
                          </Badge>
                        </td>
                        <td className="px-5 py-3">
                          <SourceBadge source={p.source} />
                        </td>
                        <td className="px-5 py-3 text-right font-mono">
                          {p.credits_purchased.toLocaleString()}
                        </td>
                        <td className="px-5 py-3 text-right font-mono">
                          {p.credits_remaining.toLocaleString()}
                        </td>
                        <td className="px-5 py-3 text-right font-mono">
                          ${p.price_paid.toFixed(2)}
                        </td>
                        <td className="px-5 py-3 text-muted-foreground">
                          {p.purchased_at
                            ? new Date(p.purchased_at).toLocaleDateString()
                            : "—"}
                        </td>
                        <td className="px-5 py-3 text-muted-foreground">
                          {p.expires_at
                            ? new Date(p.expires_at).toLocaleDateString()
                            : "—"}
                        </td>
                        <td className="px-5 py-3 text-right">
                          <Button
                            variant="secondary"
                            onClick={() => setPendingRevoke(p)}
                          >
                            Revoke
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      <ConfirmDialog
        open={pendingRevoke !== null}
        onClose={() => setPendingRevoke(null)}
        title="Revoke package?"
        description={
          pendingRevoke
            ? `Permanently delete ${pendingRevoke.credits_remaining.toLocaleString()} remaining ${pendingRevoke.kind} (source: ${pendingRevoke.source}). This cannot be undone.${
                pendingRevoke.source === "purchase"
                  ? " Issue a Stripe refund separately if applicable."
                  : ""
              }`
            : ""
        }
        confirmLabel="Revoke"
        onConfirm={() => pendingRevoke && revokePackage(pendingRevoke)}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  sublabel,
  capitalize,
  wrap,
}: {
  label: string;
  value: string;
  sublabel?: string;
  capitalize?: boolean;
  wrap?: boolean;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p
        className={`mt-1 text-lg font-semibold text-foreground ${
          capitalize ? "capitalize" : ""
        } ${wrap ? "break-all" : ""}`}
      >
        {value}
      </p>
      {sublabel && (
        <p className="text-xs text-muted-foreground">{sublabel}</p>
      )}
    </div>
  );
}

function SourceBadge({ source }: { source: MeteredPackage["source"] }) {
  const variant =
    source === "purchase"
      ? "default"
      : source === "plan_monthly"
        ? "secondary"
        : source === "admin_grant"
          ? "outline"
          : "outline";
  const label =
    source === "plan_monthly"
      ? "Monthly plan"
      : source === "admin_grant"
        ? "Admin grant"
        : source === "purchase"
          ? "Purchase"
          : "Trial";
  return <Badge variant={variant as "default" | "secondary" | "outline"}>{label}</Badge>;
}

function OverrideRow({
  label,
  placeholder,
  currentValue,
  onApply,
  onReset,
}: {
  label: string;
  placeholder: string;
  currentValue: number | null | undefined;
  onApply: (n: number) => void;
  onReset: () => void;
}) {
  const [draft, setDraft] = useState<string>("");
  useEffect(() => {
    setDraft(currentValue == null ? "" : String(currentValue));
  }, [currentValue]);

  return (
    <FormField
      label={label}
      helpText={
        currentValue == null
          ? "Currently: plan default"
          : `Currently: ${currentValue.toLocaleString()} (override)`
      }
    >
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={placeholder}
          inputMode="numeric"
        />
        <Button
          onClick={() => {
            const n = parseInt(draft, 10);
            if (Number.isFinite(n) && n >= 0) onApply(n);
          }}
        >
          Apply
        </Button>
        <Button variant="secondary" onClick={onReset}>
          Reset
        </Button>
      </div>
    </FormField>
  );
}

function GrantRow({
  label,
  onGrant,
}: {
  label: string;
  onGrant: (n: number) => void;
}) {
  const [draft, setDraft] = useState<string>("");
  return (
    <FormField
      label={`Grant ${label.toLowerCase()}`}
      helpText="Inserts a package immediately. No Stripe charge. Use responsibly."
    >
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="1000"
          inputMode="numeric"
        />
        <Button
          onClick={() => {
            const n = parseInt(draft, 10);
            if (Number.isFinite(n) && n > 0) {
              onGrant(n);
              setDraft("");
            }
          }}
        >
          Grant
        </Button>
      </div>
    </FormField>
  );
}
