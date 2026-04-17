"use client";

// AI-credits billing page. Shows the tenant's balance + monthly plan
// allotment alongside three "Buy more credits" pack cards that
// redirect to Stripe Checkout. The actual package insert happens when
// Stripe posts back `checkout.session.completed` to the engine webhook.

import { useCallback, useEffect, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";

import { SkeletonDashboard } from "@/components/skeleton";

interface CreditBalance {
  credit_balance: number;
  billing_mode: string;
  packages_active: number;
  package_credits_remaining: number;
  monthly_spent: number;
  monthly_spending_limit: number | null;
}

const CREDIT_PACKS: { size: "500" | "2000" | "10000"; usd: number; label: string }[] = [
  { size: "500", usd: 25, label: "500 credits" },
  { size: "2000", usd: 90, label: "2,000 credits — 10% off" },
  { size: "10000", usd: 400, label: "10,000 credits — 20% off" },
];

export default function CreditsBillingPage() {
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [buyingSize, setBuyingSize] = useState<string | null>(null);
  const [toast, setToast] = useState<string>("");

  const fetchBalance = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/credits");
      if (!resp.ok) throw new Error(`Balance fetch failed (${resp.status})`);
      setBalance(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load balance");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchBalance();
    // Pick up ?checkout=success / ?checkout=cancelled from the return URL.
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "success") {
      setToast(
        "Payment received — credits land in your account within ~10 seconds after Stripe confirms.",
      );
    } else if (params.get("checkout") === "cancelled") {
      setToast("Purchase cancelled. Your balance is unchanged.");
    }
  }, [fetchBalance]);

  async function handleBuy(size: "500" | "2000" | "10000") {
    setBuyingSize(size);
    setError("");
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
      setError(e instanceof Error ? e.message : "Failed to create checkout session");
      setBuyingSize(null);
    }
  }

  if (loading) return <SkeletonDashboard />;

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">AI Credits</h1>
        <p className="text-slate-600 mt-1 text-sm">
          AI analyzers (spell check, barcode decode, brand compliance, regulatory
          labels) consume credits per run. Your plan includes a monthly allotment;
          buy extra in fixed packs that roll over for a year.
        </p>
      </div>

      {toast && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          {toast}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">
          {error}
        </div>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Current balance
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Stat
            label="Active credits"
            value={balance?.package_credits_remaining ?? 0}
          />
          <Stat label="Packages active" value={balance?.packages_active ?? 0} />
          <Stat
            label="Billing mode"
            value={balance?.billing_mode ?? "-"}
            valueClassName="text-base font-medium text-slate-900 capitalize"
          />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-900">Buy more credits</h2>
        <p className="text-sm text-slate-600">
          Purchased packs expire 12 months after the purchase date. Payments are
          processed by Stripe — we never see your card details.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {CREDIT_PACKS.map((p) => (
            <article
              key={p.size}
              className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-5"
            >
              <div>
                <h3 className="text-lg font-semibold text-slate-900">{p.label}</h3>
                <p className="mt-1 text-2xl font-bold text-slate-900">
                  ${p.usd.toLocaleString()}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  ${(p.usd / parseInt(p.size, 10)).toFixed(3)} per credit
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
    </div>
  );
}

function Stat({
  label,
  value,
  valueClassName = "text-2xl font-bold text-slate-900",
}: {
  label: string;
  value: number | string;
  valueClassName?: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 ${valueClassName}`}>{value}</p>
    </div>
  );
}
