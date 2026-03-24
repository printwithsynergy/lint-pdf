"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface Subscription {
  plan: string;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

interface Invoice {
  id: string;
  amount_due: number;
  currency: string;
  status: string;
  created: string;
  invoice_pdf: string | null;
}

const PLAN_FEATURES: Record<string, string[]> = {
  free: [
    "50 jobs/day",
    "25 MB max file size",
    "1 custom profile",
    "No webhooks",
  ],
  starter: [
    "500 jobs/day",
    "250 MB max file size",
    "10 custom profiles",
    "No webhooks",
  ],
  growth: [
    "5,000 jobs/day",
    "500 MB max file size",
    "25 custom profiles",
    "5 webhooks",
    "Custom profiles",
    "AI features",
  ],
  scale: [
    "25,000 jobs/day",
    "1 GB max file size",
    "50 custom profiles",
    "20 webhooks",
    "Whitelabeling",
    "Priority processing",
  ],
  enterprise: [
    "100,000 jobs/day",
    "2 GB max file size",
    "100 custom profiles",
    "100 webhooks",
    "Custom integrations",
    "Dedicated support",
  ],
};

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const [subResp, invResp] = await Promise.all([
        fetch("/api/lintpdf/billing/subscription"),
        fetch("/api/lintpdf/billing/invoices"),
      ]);
      if (subResp.ok) {
        setSubscription(await subResp.json());
      }
      if (invResp.ok) {
        const data = await invResp.json();
        setInvoices(Array.isArray(data) ? data : (data.invoices ?? []));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load billing");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleUpgrade() {
    try {
      const resp = await fetch("/api/lintpdf/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!resp.ok) throw new Error("Failed to create checkout session");
      const data = await resp.json();
      if (data.url) window.location.href = data.url;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start checkout");
    }
  }

  async function handleManage() {
    try {
      const resp = await fetch("/api/lintpdf/billing/portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!resp.ok) throw new Error("Failed to open billing portal");
      const data = await resp.json();
      if (data.url) window.location.href = data.url;
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to open billing portal",
      );
    }
  }

  if (loading) {
    return <SkeletonDashboard type="detail" />;
  }

  const currentPlan = subscription?.plan ?? "free";

  return (
    <main className="p-8 max-w-4xl">
      <h1 className="font-display text-2xl font-bold">Billing & Plan</h1>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Current plan */}
      <div className="mt-6 rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Current Plan</h2>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-2xl font-bold uppercase">
                {currentPlan}
              </span>
              {subscription?.status && (
                <span
                  className={`rounded px-1.5 py-0.5 text-xs ${
                    subscription.status === "active"
                      ? "bg-green-100 text-green-700"
                      : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {subscription.status}
                </span>
              )}
            </div>
            {subscription?.current_period_end && (
              <p className="mt-1 text-xs text-muted-foreground">
                {subscription.cancel_at_period_end ? "Cancels" : "Renews"} on{" "}
                {new Date(subscription.current_period_end).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleUpgrade}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Upgrade
            </button>
            {subscription?.status === "active" && (
              <button
                onClick={handleManage}
                className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
              >
                Manage Subscription
              </button>
            )}
          </div>
        </div>

        {/* Plan features */}
        {PLAN_FEATURES[currentPlan] && (
          <ul className="mt-3 grid gap-1 text-sm sm:grid-cols-2">
            {PLAN_FEATURES[currentPlan].map((f) => (
              <li key={f} className="flex items-center gap-1.5">
                <span className="text-green-500">&#10003;</span> {f}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Plan comparison */}
      <div className="mt-6 rounded-lg border p-4">
        <h2 className="text-lg font-semibold">Compare Plans</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-5">
          {Object.entries(PLAN_FEATURES).map(([plan, features]) => (
            <div
              key={plan}
              className={`rounded-lg border p-3 ${plan === currentPlan ? "border-primary bg-primary/5" : ""}`}
            >
              <h3 className="font-semibold uppercase">{plan}</h3>
              <ul className="mt-2 space-y-1 text-xs">
                {features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Invoices */}
      {invoices.length > 0 && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">Invoice History</h2>
          <div className="mt-3 space-y-2">
            {invoices.map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between rounded border p-2 text-sm"
              >
                <div>
                  <span className="font-medium">
                    ${(inv.amount_due / 100).toFixed(2)}{" "}
                    {inv.currency.toUpperCase()}
                  </span>
                  <span className="ml-2 text-muted-foreground">
                    {new Date(inv.created).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs ${
                      inv.status === "paid"
                        ? "bg-green-100 text-green-700"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {inv.status}
                  </span>
                  {inv.invoice_pdf && (
                    <a
                      href={inv.invoice_pdf}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      PDF
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
