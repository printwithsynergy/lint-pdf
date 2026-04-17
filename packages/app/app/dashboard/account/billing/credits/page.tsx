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

interface UsagePoint {
  date: string;
  credits_consumed: number;
  ai_jobs: number;
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
  const [usage, setUsage] = useState<UsagePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [buyingSize, setBuyingSize] = useState<string | null>(null);

  const fetchBalance = useCallback(async () => {
    try {
      const [balResp, pkgResp, usageResp] = await Promise.all([
        fetch("/api/lintpdf/credits"),
        fetch("/api/lintpdf/credits/packages").catch(() => null),
        fetch("/api/lintpdf/credits/usage?days=30").catch(() => null),
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
      if (usageResp && usageResp.ok) {
        const data = await usageResp.json();
        setUsage(
          (data.data_points ?? []).map((p: UsagePoint & { credits_consumed: number | string }) => ({
            date: p.date,
            credits_consumed: Number(p.credits_consumed ?? 0),
            ai_jobs: Number(p.ai_jobs ?? 0),
          })),
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

      <section className="rounded-lg border border-border bg-card p-5 shadow-sm">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              Usage (last 30 days)
            </h2>
            <p className="text-xs text-muted-foreground">
              Credits consumed per day across AI inspections.
            </p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-foreground">
              {usage.reduce((n, p) => n + p.credits_consumed, 0).toLocaleString()}
            </div>
            <div className="text-xs text-muted-foreground">
              total credits in window
            </div>
          </div>
        </header>
        <UsageChart points={usage} />
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

function UsageChart({ points }: { points: UsagePoint[] }) {
  if (points.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-muted/20 p-8 text-center text-sm text-muted-foreground">
        No usage data yet. Once AI analyzers run they&rsquo;ll show up here.
      </div>
    );
  }
  // Pad the series to exactly 30 slots so bars render at a fixed width
  // even when the engine only returns days with activity.
  const byDate = new Map(points.map((p) => [p.date, p]));
  const today = new Date();
  const series: UsagePoint[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setUTCDate(today.getUTCDate() - i);
    const iso = d.toISOString().slice(0, 10);
    series.push(byDate.get(iso) ?? { date: iso, credits_consumed: 0, ai_jobs: 0 });
  }
  const max = Math.max(1, ...series.map((p) => p.credits_consumed));
  const width = 600;
  const height = 140;
  const pad = 8;
  const bw = (width - pad * 2) / series.length;
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-36 w-full"
      role="img"
      aria-label="Daily AI credit consumption over the last 30 days"
    >
      {series.map((p, i) => {
        const h = p.credits_consumed === 0 ? 1 : ((height - pad * 2) * p.credits_consumed) / max;
        const x = pad + i * bw + 1;
        const y = height - pad - h;
        const w = Math.max(1, bw - 2);
        return (
          <g key={p.date}>
            <title>{`${p.date}: ${p.credits_consumed} credits, ${p.ai_jobs} jobs`}</title>
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              rx={1}
              className="fill-[color:var(--primary,currentColor)] opacity-80"
            />
          </g>
        );
      })}
      <line
        x1={pad}
        x2={width - pad}
        y1={height - pad}
        y2={height - pad}
        className="stroke-border"
        strokeWidth={0.5}
      />
    </svg>
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
