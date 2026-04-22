"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";

import { SkeletonDashboard } from "@/components/skeleton";

interface PlanLimit {
  plan: string;
  baseline: Record<string, unknown>;
  overrides: Record<string, unknown>;
  effective: Record<string, unknown>;
}

interface PlanLimitList {
  plans: PlanLimit[];
}

/**
 * Plan-tier entitlement editor.
 *
 * Flips global defaults — e.g. "every Growth tenant now gets
 * `ai_audit_enabled=True`" — without a code deploy, by writing
 * to the new `plan_limit_overrides` table. The resolver reads
 * that table after the hardcoded `PLAN_LIMITS` baseline and
 * before per-tenant overrides, so this UI affects every tenant
 * on the plan that doesn't have a per-tenant override of its own.
 *
 * Renders three columns per row:
 *   - Baseline (hardcoded in PLAN_LIMITS)
 *   - Override input (DB-level edit, ops-editable)
 *   - Effective (baseline merged with override)
 */

const BOOL_KEYS = new Set([
  "ai_audit_enabled",
  "ai_enabled",
  "desktop_app_enabled",
  "annotations_enabled",
  "capability_fillin_enabled",
  "approval_chains_enabled",
  "webhooks_enabled",
  "whitelabel_enabled",
  "priority_processing",
  "custom_integrations",
  "custom_profiles",
]);

const LIST_KEYS = new Set([
  "allowed_report_formats",
  "allowed_preflight_sources",
]);

function displayValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "boolean") return v ? "on" : "off";
  return String(v);
}

export default function AdminPlansPage(): React.ReactNode {
  const [data, setData] = useState<PlanLimit[] | null>(null);
  const [activePlan, setActivePlan] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch("/api/lintpdf/admin/plans");
      if (!resp.ok) {
        throw new Error(`Failed to load (${resp.status})`);
      }
      const doc = (await resp.json()) as PlanLimitList;
      setData(doc.plans);
      if (!activePlan && doc.plans.length > 0) {
        setActivePlan(doc.plans[0].plan);
      }
      setDraft({});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [activePlan]);

  useEffect(() => {
    load();
  }, [load]);

  const plan = useMemo(
    () => data?.find((p) => p.plan === activePlan) ?? null,
    [data, activePlan],
  );

  async function save() {
    if (!plan) return;
    const body: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(draft)) {
      if (v === null || v === undefined) continue;
      body[k] = v;
    }
    if (Object.keys(body).length === 0) {
      setMsg("No changes to save.");
      return;
    }
    setSaving(true);
    setError("");
    setMsg("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/plans/${encodeURIComponent(plan.plan)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ overrides: body }),
        },
      );
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`PATCH failed (${resp.status}): ${text.slice(0, 200)}`);
      }
      setMsg(`Saved ${plan.plan}.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function resetPlan() {
    if (!plan) return;
    if (
      !window.confirm(
        `Clear every DB-level override for the ${plan.plan.toUpperCase()} plan? It will revert to the hardcoded code baseline.`,
      )
    ) {
      return;
    }
    setSaving(true);
    setError("");
    setMsg("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/plans/${encodeURIComponent(plan.plan)}`,
        { method: "DELETE" },
      );
      if (!resp.ok) {
        throw new Error(`DELETE failed (${resp.status})`);
      }
      setMsg(`All ${plan.plan} overrides cleared.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !data) return <SkeletonDashboard />;

  // Union of all keys across baseline + overrides so a key added to
  // overrides (but not baseline) still gets a row to edit / clear.
  const keysUnion = new Set<string>();
  if (plan) {
    for (const k of Object.keys(plan.baseline)) keysUnion.add(k);
    for (const k of Object.keys(plan.overrides)) keysUnion.add(k);
  }
  const allKeys = [...keysUnion].sort();

  const pending: Record<string, unknown> = {
    ...(plan?.overrides ?? {}),
    ...draft,
  };

  const renderInput = (key: string) => {
    const raw = pending[key];
    if (BOOL_KEYS.has(key)) {
      return (
        <select
          value={raw === undefined ? "" : raw ? "true" : "false"}
          onChange={(e) => {
            const v = e.target.value;
            setDraft((d) => ({
              ...d,
              [key]: v === "" ? undefined : v === "true",
            }));
          }}
          className="rounded border px-2 py-1 text-xs"
        >
          <option value="">(inherit baseline)</option>
          <option value="true">force on</option>
          <option value="false">force off</option>
        </select>
      );
    }
    if (LIST_KEYS.has(key)) {
      const strVal = Array.isArray(raw) ? raw.join(", ") : "";
      return (
        <input
          type="text"
          value={strVal}
          placeholder="(inherit)"
          onChange={(e) => {
            const t = e.target.value.trim();
            if (t === "") {
              setDraft((d) => ({ ...d, [key]: undefined }));
              return;
            }
            const parts = t
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean);
            setDraft((d) => ({ ...d, [key]: parts }));
          }}
          className="w-64 rounded border px-2 py-1 text-xs"
        />
      );
    }
    // Default: numeric / freeform text.
    const strVal = raw === undefined || raw === null ? "" : String(raw);
    return (
      <input
        type="text"
        value={strVal}
        placeholder="(inherit)"
        onChange={(e) => {
          const t = e.target.value.trim();
          if (t === "") {
            setDraft((d) => ({ ...d, [key]: undefined }));
            return;
          }
          // Try numeric parse first; fall back to the raw string.
          const n = Number(t);
          setDraft((d) => ({
            ...d,
            [key]: Number.isFinite(n) && /^-?\d+$/.test(t) ? Math.trunc(n) : t,
          }));
        }}
        className="w-32 rounded border px-2 py-1 text-xs"
      />
    );
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Plan defaults</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Global entitlement defaults per plan. Ops edits here take
            effect for every tenant on the plan that doesn&apos;t have
            its own per-tenant override. Per-tenant overrides still win.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={resetPlan}
            disabled={saving || !plan}
          >
            Clear plan overrides
          </Button>
          <Button
            size="sm"
            onClick={save}
            disabled={saving || Object.keys(draft).length === 0}
          >
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </div>

      <div className="mt-4 flex gap-2 border-b">
        {data.map((p) => (
          <button
            key={p.plan}
            type="button"
            onClick={() => {
              setActivePlan(p.plan);
              setDraft({});
              setMsg("");
            }}
            className={`px-3 py-2 text-sm uppercase ${
              activePlan === p.plan
                ? "border-b-2 border-blue-500 font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {p.plan}
            {Object.keys(p.overrides).length > 0 && (
              <span className="ml-1 rounded-full bg-amber-500/20 px-1.5 text-[10px] text-amber-600">
                {Object.keys(p.overrides).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {msg && <p className="mt-4 text-sm text-green-600">{msg}</p>}

      {plan && (
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b text-xs uppercase text-muted-foreground">
              <tr>
                <th className="pb-2 font-medium">Key</th>
                <th className="pb-2 font-medium">Baseline (PLAN_LIMITS)</th>
                <th className="pb-2 font-medium">DB override</th>
                <th className="pb-2 font-medium">Effective</th>
              </tr>
            </thead>
            <tbody>
              {allKeys.map((key) => (
                <tr key={key} className="border-b border-slate-800/20">
                  <td className="py-2 text-sm">
                    <code>{key}</code>
                  </td>
                  <td className="py-2 text-xs">
                    {displayValue(plan.baseline[key])}
                  </td>
                  <td className="py-2">{renderInput(key)}</td>
                  <td className="py-2 text-xs font-semibold">
                    {displayValue(plan.effective[key])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
