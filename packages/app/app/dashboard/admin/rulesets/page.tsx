"use client";

/**
 * Admin "Rulesets (All Tenants)" page — super-admin cross-tenant CRUD.
 *
 * Lists every system preset (DB-backed; seeded from bundled JSON on
 * first boot) plus every tenant's custom profiles. Admins can:
 *   - Create new admin-authored system presets
 *   - Edit preset contents (flips bundled → admin-edited on first save)
 *   - Scope visibility (all / plan / tenant allowlist / combined)
 *   - Clone any system preset into a specific tenant's customs
 *   - Delete presets
 *   - Set a tenant's soft-default preset
 *
 * Backed by /api/lintpdf/admin/system-profiles + the existing
 * /api/lintpdf/admin/profiles (for the per-tenant customs block).
 */

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

type SystemSource = "bundled" | "admin";
type VisibilityMode = "all" | "plan" | "tenants" | "plan_and_tenants";

interface SystemProfileSummary {
  profile_id: string;
  name: string;
  description?: string | null;
  conformance?: string | null;
  workflow?: string | null;
  source: SystemSource;
  bundled_version?: string | null;
  visibility_mode: VisibilityMode;
  min_plan?: string | null;
  visible_tenant_ids: string[];
  created_at: string;
  updated_at: string;
}

interface SystemProfileDetail extends SystemProfileSummary {
  preflight_profile: Record<string, unknown>;
}

interface TenantCustomSummary {
  profile_id: string;
  name: string;
  description?: string | null;
  conformance?: string | null;
  workflow?: string | null;
  is_builtin: false;
}

interface TenantBlock {
  tenant_id: string;
  tenant_name: string | null;
  profiles: TenantCustomSummary[];
}

const PLAN_SLUGS = [
  "free",
  "viewer",
  "starter",
  "growth",
  "scale",
  "enterprise",
];

export default function AdminRulesetsPage() {
  const [system, setSystem] = useState<SystemProfileSummary[] | null>(null);
  const [tenants, setTenants] = useState<TenantBlock[]>([]);
  const [tenantList, setTenantList] = useState<
    { id: string; name: string | null }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [editing, setEditing] = useState<SystemProfileDetail | null>(null);
  const [editJson, setEditJson] = useState("");
  const [editBusy, setEditBusy] = useState(false);

  const [scopeFor, setScopeFor] = useState<SystemProfileSummary | null>(null);
  const [scopeMode, setScopeMode] = useState<VisibilityMode>("all");
  const [scopeMinPlan, setScopeMinPlan] = useState("");
  const [scopeTenants, setScopeTenants] = useState<string[]>([]);
  const [scopeBusy, setScopeBusy] = useState(false);

  const [cloneFor, setCloneFor] = useState<SystemProfileSummary | null>(null);
  const [cloneTenantId, setCloneTenantId] = useState("");
  const [cloneNewId, setCloneNewId] = useState("");
  const [cloneBusy, setCloneBusy] = useState(false);

  const [creating, setCreating] = useState(false);
  const [createId, setCreateId] = useState("");
  const [createJson, setCreateJson] = useState(
    JSON.stringify(
      {
        name: "New preset",
        description: "",
        version: "1.0",
        workflow: "auto",
        checks: {},
        thresholds: {},
      },
      null,
      2,
    ),
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [sysResp, legacyResp, tenResp] = await Promise.all([
        fetch("/api/lintpdf/admin/system-profiles"),
        fetch("/api/lintpdf/admin/profiles"),
        fetch("/api/lintpdf/admin/tenants?page=1&page_size=200"),
      ]);
      if (!sysResp.ok) throw new Error(`system-profiles ${sysResp.status}`);
      if (!legacyResp.ok) throw new Error(`profiles ${legacyResp.status}`);
      const sysJson = (await sysResp.json()) as {
        profiles: SystemProfileSummary[];
      };
      const legacyJson = (await legacyResp.json()) as {
        tenants: TenantBlock[];
      };
      setSystem(sysJson.profiles);
      setTenants(legacyJson.tenants ?? []);
      if (tenResp.ok) {
        const tj = (await tenResp.json()) as {
          tenants: { id: string; name: string }[];
        };
        setTenantList(
          (tj.tenants ?? []).map((t) => ({ id: t.id, name: t.name })),
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load rulesets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function openEdit(p: SystemProfileSummary) {
    setError("");
    const resp = await fetch(
      `/api/lintpdf/admin/system-profiles/${p.profile_id}`,
    );
    if (!resp.ok) {
      setError(`Failed to fetch preset: ${resp.status}`);
      return;
    }
    const detail = (await resp.json()) as SystemProfileDetail;
    setEditing(detail);
    setEditJson(JSON.stringify(detail.preflight_profile, null, 2));
  }

  async function saveEdit() {
    if (!editing) return;
    setEditBusy(true);
    setError("");
    try {
      const parsed = JSON.parse(editJson);
      const resp = await fetch(
        `/api/lintpdf/admin/system-profiles/${editing.profile_id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ preflight_profile: parsed }),
        },
      );
      if (!resp.ok) {
        const b = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(b.error ?? `Failed (${resp.status})`);
      }
      setEditing(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setEditBusy(false);
    }
  }

  async function deletePreset(p: SystemProfileSummary) {
    const warning =
      p.source === "bundled"
        ? "This was seeded from bundled JSON. Deleting it here removes it from THIS deployment only — a fresh DB install of the same engine version would recreate it."
        : "This will remove the preset from every tenant that currently sees it.";
    if (!window.confirm(`Delete system preset "${p.profile_id}"?\n\n${warning}`)) return;
    setError("");
    const resp = await fetch(
      `/api/lintpdf/admin/system-profiles/${p.profile_id}`,
      { method: "DELETE" },
    );
    if (!resp.ok && resp.status !== 204) {
      const b = (await resp.json().catch(() => ({}))) as { error?: string };
      setError(b.error ?? `Failed (${resp.status})`);
      return;
    }
    await load();
  }

  function openScope(p: SystemProfileSummary) {
    setScopeFor(p);
    setScopeMode(p.visibility_mode);
    setScopeMinPlan(p.min_plan ?? "");
    setScopeTenants(p.visible_tenant_ids);
  }

  async function saveScope() {
    if (!scopeFor) return;
    setScopeBusy(true);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/system-profiles/${scopeFor.profile_id}/visibility`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode: scopeMode,
            min_plan: scopeMinPlan || null,
            visible_tenant_ids: scopeTenants,
          }),
        },
      );
      if (!resp.ok) {
        const b = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(b.error ?? `Failed (${resp.status})`);
      }
      setScopeFor(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update scope");
    } finally {
      setScopeBusy(false);
    }
  }

  function openClone(p: SystemProfileSummary) {
    setCloneFor(p);
    setCloneTenantId("");
    setCloneNewId(`${p.profile_id}-custom`);
  }

  async function submitClone() {
    if (!cloneFor) return;
    if (!cloneTenantId) {
      setError("Pick a target tenant.");
      return;
    }
    setCloneBusy(true);
    setError("");
    try {
      const resp = await fetch(
        `/api/lintpdf/admin/system-profiles/${cloneFor.profile_id}/clone-to/${cloneTenantId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ new_profile_id: cloneNewId || null }),
        },
      );
      if (!resp.ok) {
        const b = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(b.error ?? `Failed (${resp.status})`);
      }
      setCloneFor(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to clone");
    } finally {
      setCloneBusy(false);
    }
  }

  async function createPreset() {
    if (!createId) {
      setError("profile_id required.");
      return;
    }
    setError("");
    try {
      const parsed = JSON.parse(createJson);
      const resp = await fetch(
        `/api/lintpdf/admin/system-profiles?profile_id=${encodeURIComponent(createId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ preflight_profile: parsed }),
        },
      );
      if (!resp.ok) {
        const b = (await resp.json().catch(() => ({}))) as { error?: string };
        throw new Error(b.error ?? `Failed (${resp.status})`);
      }
      setCreating(false);
      setCreateId("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create preset");
    }
  }

  async function setTenantDefault(
    tenantId: string,
    profileId: string | null,
  ) {
    setError("");
    const resp = await fetch(
      `/api/lintpdf/admin/tenants/${tenantId}/default-profile`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId }),
      },
    );
    if (!resp.ok) {
      const b = (await resp.json().catch(() => ({}))) as { error?: string };
      setError(b.error ?? `Failed (${resp.status})`);
      return;
    }
    await load();
  }

  const tenantCustomCount = useMemo(
    () => tenants.reduce((acc, t) => acc + t.profiles.length, 0),
    [tenants],
  );

  return (
    <div className="max-w-7xl">
      <h1 className="font-display text-2xl font-bold">Rulesets — All Tenants</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        System presets live in the <code className="text-xs">system_profiles</code>{" "}
        table. Bundled presets are seeded from the engine repo on first boot;
        admin edits persist across deploys. Per-tenant customs still live
        under each tenant&rsquo;s own <code className="text-xs">/dashboard/rulesets</code>.
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <SkeletonDashboard type="table" />
      ) : (
        <>
          <section className="mt-6 rounded-lg border bg-card">
            <header className="flex items-center gap-3 border-b p-3">
              <h2 className="font-semibold">System presets</h2>
              <span className="text-xs text-muted-foreground">
                {system?.length ?? 0} in DB
              </span>
              <div className="ml-auto">
                <Button size="sm" onClick={() => setCreating(true)}>
                  New system preset
                </Button>
              </div>
            </header>
            <div className="p-3">
              {!system || system.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No system presets yet — the bundled JSON seed may have
                  failed, check engine startup logs for{" "}
                  <code className="text-xs">
                    seed_system_profiles_from_bundled
                  </code>
                  .
                </p>
              ) : (
                <ul className="space-y-1">
                  {system.map((p) => (
                    <li
                      key={p.profile_id}
                      className="flex items-start justify-between gap-2 rounded-md border p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium">{p.name}</span>
                          <code className="text-xs text-muted-foreground">
                            {p.profile_id}
                          </code>
                          <SourceBadge source={p.source} />
                          <VisibilityBadge p={p} />
                        </div>
                        {p.description && (
                          <p className="truncate text-sm text-muted-foreground">
                            {p.description}
                          </p>
                        )}
                      </div>
                      <div className="flex shrink-0 flex-wrap justify-end gap-1">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openEdit(p)}
                        >
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openScope(p)}
                        >
                          Scope
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openClone(p)}
                        >
                          Clone to tenant
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => deletePreset(p)}
                        >
                          Delete
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="mt-6 rounded-lg border bg-card">
            <header className="flex items-center gap-3 border-b p-3">
              <h2 className="font-semibold">Per-tenant custom profiles</h2>
              <span className="text-xs text-muted-foreground">
                {tenantCustomCount} across {tenants.length} tenant
                {tenants.length === 1 ? "" : "s"}
              </span>
            </header>
            <div className="p-3">
              {tenants.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No tenants have authored custom profiles yet.
                </p>
              ) : (
                <div className="space-y-4">
                  {tenants.map((t) => (
                    <TenantBlockRow
                      key={t.tenant_id}
                      block={t}
                      onSetDefault={(pid) => setTenantDefault(t.tenant_id, pid)}
                    />
                  ))}
                </div>
              )}
            </div>
          </section>
        </>
      )}

      {editing && (
        <Modal title={`Edit ${editing.profile_id}`} onClose={() => setEditing(null)}>
          <p className="text-xs text-muted-foreground">
            Full PreflightProfile JSON. Saving flips{" "}
            <code className="text-xs">source</code> to{" "}
            <code className="text-xs">admin</code> on bundled rows.
          </p>
          <textarea
            value={editJson}
            onChange={(e) => setEditJson(e.target.value)}
            className="mt-2 h-72 w-full rounded-md border p-2 font-mono text-xs"
            disabled={editBusy}
          />
          <div className="mt-3 flex justify-end gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setEditing(null)}
              disabled={editBusy}
            >
              Cancel
            </Button>
            <Button size="sm" onClick={saveEdit} loading={editBusy} disabled={editBusy}>
              Save
            </Button>
          </div>
        </Modal>
      )}

      {scopeFor && (
        <Modal title={`Scope ${scopeFor.profile_id}`} onClose={() => setScopeFor(null)}>
          <label className="text-xs font-semibold uppercase text-muted-foreground">
            Visibility mode
          </label>
          <select
            value={scopeMode}
            onChange={(e) => setScopeMode(e.target.value as VisibilityMode)}
            className="mt-1 h-9 w-full rounded-md border px-2 text-sm"
            disabled={scopeBusy}
          >
            <option value="all">All tenants</option>
            <option value="plan">Plan tier gate</option>
            <option value="tenants">Specific tenants only</option>
            <option value="plan_and_tenants">Plan tier AND tenant allowlist</option>
          </select>

          {(scopeMode === "plan" || scopeMode === "plan_and_tenants") && (
            <div className="mt-3">
              <label className="text-xs font-semibold uppercase text-muted-foreground">
                Minimum plan (tenants at or above this tier see it)
              </label>
              <select
                value={scopeMinPlan}
                onChange={(e) => setScopeMinPlan(e.target.value)}
                className="mt-1 h-9 w-full rounded-md border px-2 text-sm"
                disabled={scopeBusy}
              >
                <option value="">— select —</option>
                {PLAN_SLUGS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          )}

          {(scopeMode === "tenants" || scopeMode === "plan_and_tenants") && (
            <div className="mt-3">
              <label className="text-xs font-semibold uppercase text-muted-foreground">
                Visible to tenants
              </label>
              <div className="mt-1 max-h-40 overflow-y-auto rounded-md border p-2 text-sm">
                {tenantList.length === 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Loading tenants…
                  </p>
                ) : (
                  tenantList.map((t) => (
                    <label
                      key={t.id}
                      className="flex cursor-pointer items-center gap-2"
                    >
                      <input
                        type="checkbox"
                        checked={scopeTenants.includes(t.id)}
                        onChange={(e) => {
                          setScopeTenants((prev) =>
                            e.target.checked
                              ? [...prev, t.id]
                              : prev.filter((x) => x !== t.id),
                          );
                        }}
                        disabled={scopeBusy}
                      />
                      <span>{t.name ?? t.id}</span>
                      <code className="ml-auto text-xs text-muted-foreground">
                        {t.id.slice(0, 8)}
                      </code>
                    </label>
                  ))
                )}
              </div>
            </div>
          )}

          <div className="mt-4 flex justify-end gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setScopeFor(null)}
              disabled={scopeBusy}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={saveScope}
              loading={scopeBusy}
              disabled={scopeBusy}
            >
              Save scope
            </Button>
          </div>
        </Modal>
      )}

      {cloneFor && (
        <Modal
          title={`Clone ${cloneFor.profile_id} to tenant`}
          onClose={() => setCloneFor(null)}
        >
          <p className="text-xs text-muted-foreground">
            Copies the preset JSON into the target tenant&rsquo;s{" "}
            <code className="text-xs">custom_profiles</code> table. Tenant
            owns the copy after — edits to this system preset won&rsquo;t
            propagate.
          </p>
          <label className="mt-3 block text-xs font-semibold uppercase text-muted-foreground">
            Target tenant
          </label>
          <select
            value={cloneTenantId}
            onChange={(e) => setCloneTenantId(e.target.value)}
            className="mt-1 h-9 w-full rounded-md border px-2 text-sm"
            disabled={cloneBusy}
          >
            <option value="">— pick tenant —</option>
            {tenantList.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name ?? t.id}
              </option>
            ))}
          </select>
          <label className="mt-3 block text-xs font-semibold uppercase text-muted-foreground">
            New profile_id in tenant&rsquo;s namespace
          </label>
          <input
            type="text"
            value={cloneNewId}
            onChange={(e) => setCloneNewId(e.target.value)}
            className="mt-1 h-9 w-full rounded-md border px-2 text-sm"
            disabled={cloneBusy}
          />
          <div className="mt-4 flex justify-end gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setCloneFor(null)}
              disabled={cloneBusy}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={submitClone}
              loading={cloneBusy}
              disabled={cloneBusy}
            >
              Clone
            </Button>
          </div>
        </Modal>
      )}

      {creating && (
        <Modal title="New system preset" onClose={() => setCreating(false)}>
          <label className="text-xs font-semibold uppercase text-muted-foreground">
            profile_id
          </label>
          <input
            type="text"
            value={createId}
            onChange={(e) => setCreateId(e.target.value)}
            placeholder="e.g. ecg-cmyk-admin"
            className="mt-1 h-9 w-full rounded-md border px-2 text-sm"
          />
          <label className="mt-3 block text-xs font-semibold uppercase text-muted-foreground">
            PreflightProfile JSON
          </label>
          <textarea
            value={createJson}
            onChange={(e) => setCreateJson(e.target.value)}
            className="mt-1 h-60 w-full rounded-md border p-2 font-mono text-xs"
          />
          <div className="mt-4 flex justify-end gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setCreating(false)}
            >
              Cancel
            </Button>
            <Button size="sm" onClick={createPreset}>
              Create
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function SourceBadge({ source }: { source: SystemSource }) {
  if (source === "bundled") {
    return (
      <span className="rounded bg-muted px-1.5 py-0.5 text-xs">bundled</span>
    );
  }
  return (
    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
      admin
    </span>
  );
}

function VisibilityBadge({ p }: { p: SystemProfileSummary }) {
  if (p.visibility_mode === "all") {
    return (
      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-700">
        all tenants
      </span>
    );
  }
  if (p.visibility_mode === "plan") {
    return (
      <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800">
        plan ≥ {p.min_plan ?? "?"}
      </span>
    );
  }
  if (p.visibility_mode === "tenants") {
    return (
      <span className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700">
        {p.visible_tenant_ids.length} tenant
        {p.visible_tenant_ids.length === 1 ? "" : "s"}
      </span>
    );
  }
  return (
    <span className="rounded bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700">
      plan ≥ {p.min_plan ?? "?"} + {p.visible_tenant_ids.length} tenant
      {p.visible_tenant_ids.length === 1 ? "" : "s"}
    </span>
  );
}

function TenantBlockRow({
  block,
  onSetDefault,
}: {
  block: TenantBlock;
  onSetDefault: (profileId: string | null) => void;
}) {
  return (
    <div className="rounded-lg border">
      <header className="flex items-center gap-3 border-b bg-muted/30 p-3">
        <span className="font-semibold">{block.tenant_name ?? block.tenant_id}</span>
        <code className="text-xs text-muted-foreground">{block.tenant_id}</code>
        <span className="ml-auto text-xs text-muted-foreground">
          {block.profiles.length} profile
          {block.profiles.length === 1 ? "" : "s"}
        </span>
      </header>
      <ul className="divide-y">
        {block.profiles.map((p) => (
          <li
            key={p.profile_id}
            className="flex items-center justify-between p-3"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{p.name}</span>
                <code className="text-xs text-muted-foreground">
                  {p.profile_id}
                </code>
                <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
                  custom
                </span>
              </div>
              {p.description && (
                <p className="truncate text-sm text-muted-foreground">
                  {p.description}
                </p>
              )}
            </div>
            <div className="ml-4 flex shrink-0 gap-2">
              <Link
                href={`/dashboard/rulesets?tenant=${block.tenant_id}&profile=${p.profile_id}`}
              >
                <Button variant="secondary" size="sm">
                  Edit
                </Button>
              </Link>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onSetDefault(p.profile_id)}
              >
                Set as default
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-lg border bg-card p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold">{title}</h3>
          <button
            type="button"
            className="text-sm text-muted-foreground hover:text-foreground"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
