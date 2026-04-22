"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@thinkneverland/pixie-dust-ui";

import { SkeletonDashboard } from "@/components/skeleton";

interface EntitlementsResponse {
  plan: string;
  plan_defaults: Record<string, unknown>;
  overrides: Record<string, unknown>;
  effective: Record<string, unknown>;
}

/**
 * Full per-tenant entitlements editor.
 *
 * Shows every field on `TenantEntitlements` — plan default, current
 * override (if any), and the effective merged value. Each field has
 * an input so ops can type an override; unchecking / clearing sends
 * `null` which the engine interprets as "remove this override entry"
 * (via the PATCH body) or "use the reset-all endpoint". Plan defaults
 * come straight from `PLAN_LIMITS`; editing them globally requires a
 * separate tier editor (not yet shipped — use this page for per-tenant
 * deltas in the meantime).
 */

// Keep the field ordering stable so ops can scan the same shape
// across tenants. Split by type so the renderer can pick the right
// input widget per row.
const BOOL_FIELDS: readonly [string, string][] = [
  ["ai_audit_enabled", "AI Accuracy Audit"],
  ["ai_enabled", "AI Preflight"],
  ["desktop_app_enabled", "Desktop App"],
  ["annotations_enabled", "Viewer Annotations"],
  ["capability_fillin_enabled", "On-demand Capability Fill"],
  ["approval_chains_enabled", "Approval Chains"],
  ["webhooks_enabled", "Webhooks"],
  ["whitelabel_enabled", "White-label branding"],
  ["priority_processing", "Priority Celery queue"],
  ["custom_integrations", "Custom Integrations"],
  ["custom_profiles", "Custom Profiles / Endpoints"],
];

const INT_FIELDS: readonly [string, string][] = [
  ["rate_limit_daily", "Daily job limit"],
  ["max_file_size_mb", "Max upload MB"],
  ["monthly_files_included", "Monthly files included"],
  ["monthly_ai_credits", "Monthly AI credits"],
  ["report_storage_mb", "Report storage MB"],
  ["report_default_expiry_days", "Report default expiry (days)"],
  ["overage_rate_cents", "Overage rate (¢ / job)"],
  ["max_webhooks", "Max webhooks"],
  ["max_custom_profiles", "Max custom profiles"],
  ["max_approval_templates", "Max approval templates"],
];

const LIST_FIELDS: readonly [string, string][] = [
  ["allowed_report_formats", "Allowed report formats (comma-sep)"],
  ["allowed_preflight_sources", "Allowed preflight sources (comma-sep)"],
];

function displayValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "boolean") return v ? "on" : "off";
  return String(v);
}

export default function TenantEntitlementsPage(): React.ReactNode {
  const params = useParams<{ tenantId: string }>();
  const tenantId = params.tenantId;
  const [data, setData] = useState<EntitlementsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  // Local staged edits. Keys that aren't here inherit from the
  // stored overrides; setting a key to null removes that override.
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${tenantId}/entitlements`,
      );
      if (!resp.ok) {
        throw new Error(`Failed to load (${resp.status})`);
      }
      const doc = (await resp.json()) as EntitlementsResponse;
      setData(doc);
      setDraft({});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    load();
  }, [load]);

  async function save() {
    if (!data) return;
    // Drop `null` values from the PATCH body — the engine's schema
    // treats them as "ignore" rather than "clear". Deletions go
    // through the dedicated reset-all endpoint for now.
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
        `/api/lintpdf/admin/tenants/${tenantId}/entitlements`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`PATCH failed (${resp.status}): ${text.slice(0, 200)}`);
      }
      setMsg("Saved. Effective entitlements refreshed below.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function resetAll() {
    if (
      !window.confirm(
        "Remove ALL entitlement overrides for this tenant? They will revert to plan defaults.",
      )
    ) {
      return;
    }
    setSaving(true);
    setError("");
    setMsg("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${tenantId}/entitlements`,
        { method: "DELETE" },
      );
      if (!resp.ok) {
        throw new Error(`DELETE failed (${resp.status})`);
      }
      setMsg("All overrides cleared — now inheriting plan defaults.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !data) return <SkeletonDashboard />;

  const overrides = data.overrides ?? {};
  const effective = data.effective ?? {};
  const defaults = data.plan_defaults ?? {};

  // Merge current override + local draft so the field inputs
  // reflect both saved state and pending edits.
  const pending: Record<string, unknown> = { ...overrides, ...draft };

  const renderBool = (key: string, label: string) => {
    const overrideVal = pending[key] as boolean | undefined;
    const planDefault = defaults[key] as boolean | undefined;
    const effectiveVal = effective[key] as boolean | undefined;
    return (
      <tr key={key} className="border-b border-slate-800/20">
        <td className="py-2 text-sm">{label}</td>
        <td className="py-2 text-xs text-muted-foreground">
          <code>{key}</code>
        </td>
        <td className="py-2 text-xs">
          {planDefault === undefined ? "—" : planDefault ? "on" : "off"}
        </td>
        <td className="py-2">
          <select
            value={overrideVal === undefined ? "" : overrideVal ? "true" : "false"}
            onChange={(e) => {
              const v = e.target.value;
              setDraft((d) => ({
                ...d,
                [key]: v === "" ? undefined : v === "true",
              }));
            }}
            className="rounded border px-2 py-1 text-xs"
          >
            <option value="">(inherit)</option>
            <option value="true">force on</option>
            <option value="false">force off</option>
          </select>
        </td>
        <td className="py-2 text-xs font-semibold">{displayValue(effectiveVal)}</td>
      </tr>
    );
  };

  const renderInt = (key: string, label: string) => {
    const raw = pending[key];
    const strVal =
      raw === undefined || raw === null ? "" : String(raw);
    return (
      <tr key={key} className="border-b border-slate-800/20">
        <td className="py-2 text-sm">{label}</td>
        <td className="py-2 text-xs text-muted-foreground">
          <code>{key}</code>
        </td>
        <td className="py-2 text-xs">{displayValue(defaults[key])}</td>
        <td className="py-2">
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
              const n = Number(t);
              if (!Number.isFinite(n)) return;
              setDraft((d) => ({ ...d, [key]: Math.trunc(n) }));
            }}
            className="w-24 rounded border px-2 py-1 text-xs"
          />
        </td>
        <td className="py-2 text-xs font-semibold">{displayValue(effective[key])}</td>
      </tr>
    );
  };

  const renderList = (key: string, label: string) => {
    const raw = pending[key] as string[] | undefined;
    const strVal = Array.isArray(raw) ? raw.join(", ") : "";
    return (
      <tr key={key} className="border-b border-slate-800/20">
        <td className="py-2 text-sm">{label}</td>
        <td className="py-2 text-xs text-muted-foreground">
          <code>{key}</code>
        </td>
        <td className="py-2 text-xs">{displayValue(defaults[key])}</td>
        <td className="py-2">
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
        </td>
        <td className="py-2 text-xs font-semibold">
          {displayValue(effective[key])}
        </td>
      </tr>
    );
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/dashboard/admin/tenants"
            className="text-xs text-muted-foreground underline"
          >
            ← All tenants
          </Link>
          <h1 className="font-display text-2xl font-bold">
            Entitlements · <code className="text-lg">{tenantId.slice(0, 8)}</code>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Plan: <strong>{data.plan.toUpperCase()}</strong>. Per-tenant
            overrides win over plan defaults. Leave a field on
            <em> (inherit)</em> to use the plan value. Effective column
            shows what the engine actually applies.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={resetAll}
            disabled={saving}
          >
            Reset all overrides
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

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {msg && <p className="mt-4 text-sm text-green-600">{msg}</p>}

      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-left">
          <thead className="border-b text-xs uppercase text-muted-foreground">
            <tr>
              <th className="pb-2 font-medium">Field</th>
              <th className="pb-2 font-medium">Key</th>
              <th className="pb-2 font-medium">Plan default</th>
              <th className="pb-2 font-medium">Override</th>
              <th className="pb-2 font-medium">Effective</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={5} className="pt-4 text-xs uppercase text-muted-foreground">
                Feature gates
              </td>
            </tr>
            {BOOL_FIELDS.map(([k, l]) => renderBool(k, l))}
            <tr>
              <td colSpan={5} className="pt-4 text-xs uppercase text-muted-foreground">
                Limits + counts
              </td>
            </tr>
            {INT_FIELDS.map(([k, l]) => renderInt(k, l))}
            <tr>
              <td colSpan={5} className="pt-4 text-xs uppercase text-muted-foreground">
                List gates
              </td>
            </tr>
            {LIST_FIELDS.map(([k, l]) => renderList(k, l))}
          </tbody>
        </table>
      </div>
    </>
  );
}
