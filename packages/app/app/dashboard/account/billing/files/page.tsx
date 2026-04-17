"use client";

/**
 * Tenant File Packs billing page — same shape as credits page but
 * pulls from /api/v1/files/quota.
 */

import { Suspense, useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  EmptyState,
  useToast,
} from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface FileQuota {
  tenant_id: string;
  total_remaining: number;
  monthly_allotment_remaining: number;
  purchased_remaining: number;
  active_packages: number;
  monthly_allotment: number;
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
}

const PACKS: { size: "500" | "2500" | "10000"; usd: number; label: string; perFile: number }[] = [
  { size: "500", usd: 15, label: "500 files", perFile: 0.03 },
  { size: "2500", usd: 60, label: "2,500 files", perFile: 0.024 },
  { size: "10000", usd: 200, label: "10,000 files", perFile: 0.02 },
];

export default function FilesBillingPage() {
  return (
    <Suspense fallback={<SkeletonDashboard />}>
      <FilesBillingPageInner />
    </Suspense>
  );
}

function FilesBillingPageInner() {
  const toast = useToast();
  const [quota, setQuota] = useState<FileQuota | null>(null);
  const [history, setHistory] = useState<MeteredPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [buyingSize, setBuyingSize] = useState<string | null>(null);

  const fetchQuota = useCallback(async () => {
    try {
      const [qResp, pkgResp] = await Promise.all([
        fetch("/api/lintpdf/files/quota"),
        fetch("/api/lintpdf/files/packages").catch(() => null),
      ]);
      if (qResp.ok) setQuota(await qResp.json());
      if (pkgResp && pkgResp.ok) {
        const data = await pkgResp.json();
        setHistory(
          (data.packages ?? []).filter((p: MeteredPackage) => p.kind === "files"),
        );
      }
    } catch (e) {
      toast({
        title: "Couldn't load quota",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void fetchQuota();
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "success") {
      toast({
        title: "Payment received",
        description:
          "Files land in your account within ~10 seconds after Stripe confirms.",
      });
    } else if (params.get("checkout") === "cancelled") {
      toast({
        title: "Purchase cancelled",
        description: "Your quota is unchanged.",
      });
    }
  }, [fetchQuota, toast]);

  async function handleBuy(size: "500" | "2500" | "10000") {
    setBuyingSize(size);
    try {
      const resp = await fetch("/api/lintpdf/files/topup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pack: size }),
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || `Topup failed (${resp.status})`);
      }
      const { checkout_url } = await resp.json();
      if (!checkout_url) throw new Error("No checkout URL returned");
      window.location.href = checkout_url;
    } catch (e) {
      toast({
        title: "Couldn't start checkout",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
      setBuyingSize(null);
    }
  }

  if (loading) return <SkeletonDashboard />;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-foreground">File Packs</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Each PDF submission consumes one file from your monthly allotment.
          When the monthly pool is empty you can either enable overage billing
          (per-file) or buy a file pack below. Purchased packs roll over for
          12 months.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Current quota
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat
            label="Monthly allotment"
            value={(quota?.monthly_allotment ?? 0).toLocaleString()}
          />
          <Stat
            label="Monthly remaining"
            value={(quota?.monthly_allotment_remaining ?? 0).toLocaleString()}
          />
          <Stat
            label="Purchased remaining"
            value={(quota?.purchased_remaining ?? 0).toLocaleString()}
          />
          <Stat
            label="Total available"
            value={(quota?.total_remaining ?? 0).toLocaleString()}
          />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-foreground">
          Buy more file packs
        </h2>
        <p className="text-sm text-muted-foreground">
          Purchased packs expire 12 months from purchase. Payments are
          processed by Stripe — we never see your card details.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {PACKS.map((p) => (
            <article
              key={p.size}
              className="flex flex-col justify-between rounded-lg border border-border bg-card p-5 shadow-sm"
            >
              <div>
                <h3 className="text-lg font-semibold text-foreground">
                  {p.label}
                </h3>
                <p className="mt-1 text-3xl font-bold text-foreground">
                  ${p.usd.toLocaleString()}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  ${p.perFile.toFixed(3)} per file
                </p>
              </div>
              <Button
                className="mt-4 w-full"
                onClick={() => handleBuy(p.size)}
                disabled={buyingSize !== null}
              >
                {buyingSize === p.size ? "Redirecting…" : "Buy"}
              </Button>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card shadow-sm">
        <header className="border-b border-border px-5 py-3">
          <h2 className="text-lg font-semibold text-foreground">
            Package history
          </h2>
          <p className="text-xs text-muted-foreground">
            Every file pack granted or purchased for your tenant.
          </p>
        </header>
        {history.length === 0 ? (
          <EmptyState
            title="No file packs yet"
            description="Buy a pack above, or wait for your next billing renewal to grant the plan-monthly allotment."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-5 py-2">Source</th>
                  <th className="px-5 py-2 text-right">Total</th>
                  <th className="px-5 py-2 text-right">Remaining</th>
                  <th className="px-5 py-2 text-right">Paid</th>
                  <th className="px-5 py-2">Purchased</th>
                  <th className="px-5 py-2">Expires</th>
                </tr>
              </thead>
              <tbody>
                {history.map((p) => (
                  <tr key={p.id} className="border-t border-border">
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
                        : "No expiry"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-foreground">{value}</p>
    </div>
  );
}

function SourceBadge({ source }: { source: MeteredPackage["source"] }) {
  const variant =
    source === "purchase"
      ? "default"
      : source === "plan_monthly"
        ? "secondary"
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
