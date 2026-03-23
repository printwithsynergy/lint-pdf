"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface UsageData {
  rate_limit_daily: number;
  jobs_today: number;
  max_file_size_mb: number;
  max_custom_profiles: number;
  custom_profiles_count: number;
  max_webhooks: number;
  webhooks_count: number;
  plan: string;
  overage_enabled: boolean;
  overage_today_cents: number;
  overage_cap_cents: number;
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
      const resp = await fetch("/api/grounded/usage");
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
          <h2 className="text-lg font-semibold">Daily Usage</h2>
          <div className="mt-3 space-y-4">
            <ProgressBar
              label="Preflight Jobs"
              current={usage.jobs_today}
              max={usage.rate_limit_daily}
              unit="jobs"
            />
          </div>
        </div>

        <div className="rounded-lg border p-4">
          <h2 className="text-lg font-semibold">Resource Limits</h2>
          <div className="mt-3 space-y-4">
            <ProgressBar
              label="Custom Profiles"
              current={usage.custom_profiles_count}
              max={usage.max_custom_profiles}
            />
            <ProgressBar
              label="Webhook Endpoints"
              current={usage.webhooks_count}
              max={usage.max_webhooks}
            />
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Max File Size</span>
              <span className="text-muted-foreground">
                {usage.max_file_size_mb} MB
              </span>
            </div>
          </div>
        </div>

        {usage.overage_enabled && (
          <div className="rounded-lg border p-4">
            <h2 className="text-lg font-semibold">Overage</h2>
            <div className="mt-3 space-y-4">
              <ProgressBar
                label="Daily Overage Spend"
                current={usage.overage_today_cents}
                max={usage.overage_cap_cents}
                unit="cents"
              />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
