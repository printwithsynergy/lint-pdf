"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { Badge } from "@thinkneverland/pixie-dust-ui";

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

interface AiCreditData {
  enabled: boolean;
  balance?: number;
  monthly_allotment?: number;
  consumed_this_month?: number;
  consumed_total?: number;
  billing_mode?: string;
  auto_topup?: boolean;
}

interface AiUsageEntry {
  inspection_id?: string;
  inspection_name?: string;
  category?: string;
  credits_consumed?: number;
  created_at?: string;
}

interface AiUsageData {
  enabled: boolean;
  items: AiUsageEntry[];
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
                ? "bg-warning"
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
  const [aiCredits, setAiCredits] = useState<AiCreditData | null>(null);
  const [aiUsage, setAiUsage] = useState<AiUsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchAll = useCallback(async () => {
    try {
      const [usageResp, creditResp, aiUsageResp] = await Promise.all([
        fetch("/api/lintpdf/usage"),
        fetch("/api/lintpdf/ai-credits"),
        fetch("/api/lintpdf/ai-usage?limit=20"),
      ]);
      if (!usageResp.ok) {
        const text = await usageResp.text();
        let detail = text;
        try {
          const data = JSON.parse(text);
          detail =
            typeof data?.error === "string"
              ? data.error
              : typeof data?.detail === "string"
                ? data.detail
                : text;
        } catch {
          /* leave as text */
        }
        throw new Error(
          `Failed to load usage (${usageResp.status}): ${detail}`,
        );
      }
      setUsage(await usageResp.json());
      if (creditResp.ok) {
        setAiCredits(await creditResp.json());
      }
      if (aiUsageResp.ok) {
        setAiUsage(await aiUsageResp.json());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load usage");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  if (loading) {
    return <SkeletonDashboard type="cards" />;
  }

  if (error || !usage) {
    return (
      <>
        <h1 className="font-display text-2xl font-bold">Usage</h1>
        <p className="mt-4 text-destructive">
          {error || "No usage data yet — submit a job to see your first row."}
        </p>
      </>
    );
  }

  return (
    <>
      <h1 className="font-display text-2xl font-bold">Usage & Limits</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Current billing period usage for your{" "}
        <Badge variant="secondary">{usage.plan.toUpperCase()}</Badge> plan.
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
              <p className="text-sm font-medium text-warning">
                Approaching usage limit.
              </p>
            )}
          </div>
        </div>

        {/* AI usage — only render when AI is enabled for the tenant */}
        {aiCredits?.enabled && (
          <div className="rounded-lg border p-4">
            <h2 className="text-lg font-semibold">AI Credits</h2>
            <div className="mt-3 space-y-4">
              {typeof aiCredits.monthly_allotment === "number" &&
                aiCredits.monthly_allotment > 0 && (
                  <ProgressBar
                    label="Monthly allotment"
                    current={aiCredits.consumed_this_month ?? 0}
                    max={aiCredits.monthly_allotment}
                    unit="credits"
                  />
                )}
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Balance</span>
                <span className="text-muted-foreground">
                  {(aiCredits.balance ?? 0).toLocaleString()} credits
                </span>
              </div>
              {aiCredits.billing_mode && (
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Billing mode</span>
                  <span className="text-muted-foreground">
                    {aiCredits.billing_mode}
                    {aiCredits.auto_topup ? " (auto top-up on)" : ""}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {aiUsage?.enabled && aiUsage.items.length > 0 && (
          <div className="rounded-lg border p-4">
            <h2 className="text-lg font-semibold">Recent AI inspections</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="pb-2">Inspection</th>
                    <th className="pb-2">Category</th>
                    <th className="pb-2 text-right">Credits</th>
                    <th className="pb-2 text-right">When</th>
                  </tr>
                </thead>
                <tbody>
                  {aiUsage.items.map((entry, idx) => (
                    <tr
                      key={`${entry.inspection_id ?? "row"}-${idx}`}
                      className="border-t border-border"
                    >
                      <td className="py-2">
                        {entry.inspection_name ??
                          entry.inspection_id ??
                          "Inspection"}
                      </td>
                      <td className="py-2 text-muted-foreground">
                        {entry.category ?? "—"}
                      </td>
                      <td className="py-2 text-right">
                        {entry.credits_consumed ?? 0}
                      </td>
                      <td className="py-2 text-right text-muted-foreground">
                        {entry.created_at
                          ? new Date(entry.created_at).toLocaleDateString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {aiCredits?.enabled === false && (
          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            AI inspections are not enabled on this tenant. Contact sales to
            unlock the AI feature set.
          </div>
        )}

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
    </>
  );
}
