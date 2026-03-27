"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Alert,
  AlertDescription,
} from "@thinkneverland/pixie-dust-ui";

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
    <>
      <h1 className="text-2xl font-bold">Billing & Plan</h1>

      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Current plan */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Current Plan</CardTitle>
            <div className="flex gap-2">
              <Button onClick={handleUpgrade}>Upgrade</Button>
              {subscription?.status === "active" && (
                <Button variant="secondary" onClick={handleManage}>
                  Manage Subscription
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold uppercase">
              {currentPlan}
            </span>
            {subscription?.status && (
              <Badge variant={subscription.status === "active" ? "success" : "warning"}>
                {subscription.status}
              </Badge>
            )}
          </div>
          {subscription?.current_period_end && (
            <p className="mt-1 text-xs text-muted-foreground">
              {subscription.cancel_at_period_end ? "Cancels" : "Renews"} on{" "}
              {new Date(subscription.current_period_end).toLocaleDateString()}
            </p>
          )}

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
        </CardContent>
      </Card>

      {/* Plan comparison */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Compare Plans</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-5">
            {Object.entries(PLAN_FEATURES).map(([plan, features]) => (
              <Card
                key={plan}
                className={plan === currentPlan ? "border-primary bg-primary/5" : ""}
              >
                <CardContent className="p-3">
                  <h3 className="font-semibold uppercase">{plan}</h3>
                  <ul className="mt-2 space-y-1 text-xs">
                    {features.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Invoices */}
      {invoices.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Invoice History</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Amount</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((inv) => (
                  <TableRow key={inv.id}>
                    <TableCell>
                      ${(inv.amount_due / 100).toFixed(2)}{" "}
                      {inv.currency.toUpperCase()}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(inv.created).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Badge variant={inv.status === "paid" ? "success" : "warning"}>
                        {inv.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
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
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </>
  );
}
