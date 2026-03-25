"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface UsageData {
  plan: string;
  used: number;
  limit: number;
  remaining_included: number;
  percentage: number;
  in_overage: boolean;
  overage_count: number;
  overage_rate_cents: number;
  overage_cost_cents: number;
  overage_enabled: boolean;
  overage_cap_cents: number | null;
  cap_remaining_cents: number | null;
  blocked: boolean;
  warning: boolean;
}

function ProgressBar({
  label,
  current,
  max,
  unit,
}: {
  label: string;
  current: number;
  max: number;
  unit?: string;
}) {
  const pct = max > 0 ? Math.min((current / max) * 100, 100) : 0;
  const isWarning = pct >= 80;
  const isDanger = pct >= 95;

  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">
          {current.toLocaleString()} / {max.toLocaleString()}
          {unit ? ` ${unit}` : ""}
        </span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all ${
            isDanger
              ? "bg-destructive"
              : isWarning
                ? "bg-yellow-500"
                : "bg-primary"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function UsagePage() {
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchUsage = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/usage");
      if (!resp.ok) throw new Error("Failed to load usage");
      const data = await resp.json();
      setUsage(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load usage");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  if (loading) {
    return <SkeletonDashboard type="cards" />;
  }

  if (error || !usage) {
    return (
      <main className="p-8">
        <h1 className="font-display text-2xl font-bold">Usage</h1>
        <p className="mt-4 text-destructive">{error || "No data available"}</p>
      </main>
    );
  }

  return (
    <main className="p-8 max-w-4xl">
      <h1 className="font-display text-2xl font-bold">Usage & Limits</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Current billing period usage for your{" "}
        <span className="font-medium uppercase">{usage.plan}</span> plan.
      </p>

      <div className="mt-6 space-y-6">
        <div className="rounded-lg border p-4">
          <h2 className="text-lg font-semibold">Job Usage</h2>
          <div className="mt-3 space-y-4">
            <ProgressBar
              label="Preflight Jobs"
              current={usage.used}
              max={usage.limit}
              unit="jobs"
            />
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Remaining (included)</span>
              <span className="text-muted-foreground">
                {usage.remaining_included.toLocaleString()} jobs
              </span>
            </div>
            {usage.blocked && (
              <p className="text-sm font-medium text-destructive">
                Usage limit reached — jobs are blocked.
              </p>
            )}
            {usage.warning && !usage.blocked && (
              <p className="text-sm font-medium text-yellow-600">
                Approaching usage limit.
              </p>
            )}
          </div>
        </div>

        {usage.overage_enabled && (
          <div className="rounded-lg border p-4">
            <h2 className="text-lg font-semibold">Overage</h2>
            <div className="mt-3 space-y-4">
              {usage.in_overage && (
                <p className="text-sm text-muted-foreground">
                  You are currently in overage (
                  {usage.overage_count.toLocaleString()} extra jobs).
                </p>
              )}
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Overage Cost</span>
                <span className="text-muted-foreground">
                  ${(usage.overage_cost_cents / 100).toFixed(2)}
                  {usage.overage_cap_cents != null && (
                    <> / ${(usage.overage_cap_cents / 100).toFixed(2)} cap</>
                  )}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Overage Rate</span>
                <span className="text-muted-foreground">
                  ${(usage.overage_rate_cents / 100).toFixed(2)} per job
                </span>
              </div>
              {usage.cap_remaining_cents != null && (
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Cap Remaining</span>
                  <span className="text-muted-foreground">
                    ${(usage.cap_remaining_cents / 100).toFixed(2)}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
