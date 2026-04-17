"use client";

/**
 * Tenant AI Credits billing page.
 *
 * Balance + monthly allotment summary up top, three pack cards (500 /
 * 2,000 / 10,000) that redirect to Stripe Checkout, and a history
 * table sourced from the engine's GET /api/v1/ai/credits/packages
 * endpoint. All Pixie Dust UI components + theme tokens so the
 * tenant's brand colors (via theme-default) flow automatically.
 */

import { Suspense, useCallback, useEffect, useState } from "react";
import {
  Badge,
  Button,
  EmptyState,
  useToast,
} from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface CreditBalance {
  credit_balance: number;
  billing_mode: string;
  packages_active: number;
  package_credits_remaining: number;
  monthly_spent: number;
  monthly_spending_limit: number | null;
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

const PACKS: { size: "500" | "2000" | "10000"; usd: number; label: string; perCredit: number }[] = [
  { size: "500", usd: 25, label: "500 credits", perCredit: 0.05 },
  { size: "2000", usd: 90, label: "2,000 credits", perCredit: 0.045 },
  { size: "10000", usd: 400, label: "10,000 credits", perCredit: 0.04 },
];

export default function CreditsBillingPage() {
  return (
    <Suspense fallback={<SkeletonDashboard />}>
      <CreditsBillingPageInner />
    </Suspense>
  );
}

function CreditsBillingPageInner() {
  const toast = useToast();
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [history, setHistory] = useState<MeteredPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [buyingSize, setBuyingSize] = useState<string | null>(null);

  const fetchBalance = useCallback(async () => {
    try {
      const [balResp, pkgResp] = await Promise.all([
        fetch("/api/lintpdf/credits"),
        fetch("/api/lintpdf/credits/packages").catch(() => null),
      ]);
      if (balResp.ok) setBalance(await balResp.json());
      if (pkgResp && pkgResp.ok) {
        const data = await pkgResp.json();
        setHistory(
          (data.packages ?? []).filter(
            (p: MeteredPackage) => p.kind === "credits",
          ),
        );
      }
    } catch (e) {
      toast({
        title: "Couldn't load balance",
        description: e instanceof Error ? e.message : String(e),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void fetchBalance();
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "success") {
      toast({
        title: "Payment received",
        description:
          "Credits land in your account within ~10 seconds after Stripe confirms.",
      });
    } else if (params.get("checkout") === "cancelled") {
      toast({
        title: "Purchase cancelled",
        description: "Your balance is unchanged.",
      });
    }
  }, [fetchBalance, toast]);

  async function handleBuy(size: "500" | "2000" | "10000") {
    setBuyingSize(size);
    try {
      const resp = await fetch("/api/lintpdf/credits/topup", {
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
        <h1 className="text-2xl font-semibold text-foreground">AI Credits</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          AI analyzers (spell check, barcode decode, brand compliance,
          regulatory labels, image quality) consume credits per run. Your plan
          includes a monthly allotment that resets each billing cycle;
          purchased packs roll over for 12 months.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Current balance
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat
            label="Active credits"
            value={(balance?.package_credits_remaining ?? 0).toLocaleString()}
          />
          <Stat
            label="Packages active"
            value={(balance?.packages_active ?? 0).toLocaleString()}
          />
          <Stat
            label="Spent this month"
            value={`$${(balance?.monthly_spent ?? 0).toFixed(2)}`}
          />
          <Stat
            label="Monthly cap"
            value={
              balance?.monthly_spending_limit == null
                ? "No cap"
                : `$${balance.monthly_spending_limit.toFixed(2)}`
            }
          />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-foreground">
          Buy more credits
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
                  ${p.perCredit.toFixed(3)} per credit
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
            Everything Stripe or your monthly subscription has granted you.
          </p>
        </header>
        {history.length === 0 ? (
          <EmptyState
            title="No credit packages yet"
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
