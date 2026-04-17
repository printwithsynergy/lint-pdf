"use client";

// Admin metered-resource console: set per-tenant monthly overrides for
// AI credits + file packs, or grant packs directly without Stripe.
// Intentionally minimal — paste a tenant UUID, pick the action, submit.

import { useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";

type Kind = "credits" | "files";

export default function AdminBillingPage() {
  const [tenantId, setTenantId] = useState("");
  const [messages, setMessages] = useState<
    { tone: "ok" | "err"; text: string }[]
  >([]);

  function log(tone: "ok" | "err", text: string) {
    setMessages((prev) => [{ tone, text }, ...prev].slice(0, 10));
  }

  async function setOverride(kind: Kind, value: number | null) {
    if (!tenantId) return log("err", "Paste a tenant UUID first.");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/tenants/${tenantId}/${kind}/monthly-override`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credits: value }),
        },
      );
      const body = await resp.json();
      if (!resp.ok) throw new Error(JSON.stringify(body));
      log("ok", `${kind} override → ${value === null ? "plan default" : value}`);
    } catch (e) {
      log("err", `${kind} override failed: ${e instanceof Error ? e.message : e}`);
    }
  }

  async function grant(kind: Kind, amount: number) {
    if (!tenantId) return log("err", "Paste a tenant UUID first.");
    const path =
      kind === "credits"
        ? `/api/lintpdf/admin/tenants/${tenantId}/credits/grant`
        : `/api/lintpdf/admin/tenants/${tenantId}/files/grant`;
    const body = kind === "credits" ? { credit_amount: amount, price_paid: 0 } : { files_granted: amount, price_paid: 0 };
    try {
      const resp = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(JSON.stringify(data));
      log("ok", `${kind} grant +${amount} (pkg ${data.package_id ?? "?"})`);
    } catch (e) {
      log("err", `${kind} grant failed: ${e instanceof Error ? e.message : e}`);
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Metered Resources — Admin
        </h1>
        <p className="text-slate-600 text-sm mt-1">
          Set monthly overrides or grant prepaid packs for a specific tenant.
          Overrides take effect at the next ``invoice.paid`` webhook; direct
          grants are immediate. Super-admin only.
        </p>
      </div>

      <label className="block">
        <span className="text-sm font-medium text-slate-700">Tenant UUID</span>
        <input
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
          value={tenantId}
          placeholder="00000000-0000-0000-0000-000000000000"
          onChange={(e) => setTenantId(e.target.value.trim())}
        />
      </label>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-slate-900">Monthly overrides</h2>
        <p className="text-sm text-slate-600 mb-3">
          Replace the plan default for this tenant. Submit <code>null</code> (via
          the "Reset" button) to fall back to the plan default.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <OverrideRow
            label="Monthly AI credits"
            onSet={(v) => setOverride("credits", v)}
          />
          <OverrideRow
            label="Monthly files"
            onSet={(v) => setOverride("files", v)}
          />
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-slate-900">Direct grants</h2>
        <p className="text-sm text-slate-600 mb-3">
          Insert a free package (source=admin_grant). No Stripe charge.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <GrantRow label="Credits" onGrant={(n) => grant("credits", n)} />
          <GrantRow label="Files" onGrant={(n) => grant("files", n)} />
        </div>
      </section>

      {messages.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Recent actions
          </h3>
          <ul className="mt-2 space-y-1 text-sm font-mono">
            {messages.map((m, i) => (
              <li
                key={i}
                className={
                  m.tone === "ok"
                    ? "text-emerald-700"
                    : "text-red-700"
                }
              >
                {m.text}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function OverrideRow({
  label,
  onSet,
}: {
  label: string;
  onSet: (v: number | null) => void;
}) {
  const [v, setV] = useState("");
  return (
    <div className="flex items-end gap-2">
      <label className="flex-1">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        <input
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={v}
          onChange={(e) => setV(e.target.value)}
          placeholder="0"
          inputMode="numeric"
        />
      </label>
      <Button
        onClick={() => {
          const n = parseInt(v, 10);
          if (Number.isFinite(n)) onSet(n);
        }}
      >
        Set
      </Button>
      <Button variant="secondary" onClick={() => onSet(null)}>
        Reset
      </Button>
    </div>
  );
}

function GrantRow({
  label,
  onGrant,
}: {
  label: string;
  onGrant: (n: number) => void;
}) {
  const [v, setV] = useState("");
  return (
    <div className="flex items-end gap-2">
      <label className="flex-1">
        <span className="text-xs font-medium text-slate-500">{label}</span>
        <input
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={v}
          onChange={(e) => setV(e.target.value)}
          placeholder="1000"
          inputMode="numeric"
        />
      </label>
      <Button
        onClick={() => {
          const n = parseInt(v, 10);
          if (Number.isFinite(n) && n > 0) onGrant(n);
        }}
      >
        Grant
      </Button>
    </div>
  );
}
