"use client";

/**
 * Workflows page (Phase 0.7 substrate).
 *
 * Replaces the legacy CustomEndpoint surface (/dashboard/endpoints).
 * A Workflow pins a name + profile_id + brand_spec_id + per-call
 * ToggleOverride defaults so tenants can submit jobs against a curated
 * configuration without re-specifying every field.
 */

import { useCallback, useEffect, useState } from "react";
import {
  Button,
  EmptyState,
  Input,
  FormField,
  useToast,
} from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface Workflow {
  id: string;
  name: string;
  profile_id: string;
  brand_spec_id: string | null;
  created_at?: string;
  updated_at?: string;
}

interface ProfileSummary {
  profile_id: string;
  name: string;
}

interface BrandSpecSummary {
  id: string;
  name: string;
}

interface ToggleRegistryRow {
  id: string;
  category: string;
  human_name: string;
  type: "bool" | "int" | "float" | "string" | "enum" | "json";
  default_value: unknown;
  override_at: string[];
  description: string | null;
  deprecated: boolean;
}

interface WorkflowOverrideRow {
  workflow_id: string;
  toggle_id: string;
  value: unknown;
}

export default function WorkflowsPage() {
  const { toast } = useToast();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [brandSpecs, setBrandSpecs] = useState<BrandSpecSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const [newName, setNewName] = useState("");
  const [newProfileId, setNewProfileId] = useState("");
  const [newBrandSpecId, setNewBrandSpecId] = useState("");

  // Per-workflow override editor state. Only one editor open at a time;
  // ``editorWorkflowId`` is the workflow whose defaults are being edited.
  const [editorWorkflowId, setEditorWorkflowId] = useState<string | null>(null);
  const [registry, setRegistry] = useState<ToggleRegistryRow[]>([]);
  const [overrides, setOverrides] = useState<WorkflowOverrideRow[]>([]);
  const [editorLoading, setEditorLoading] = useState(false);

  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setFetchError(null);
    try {
      const [wfResp, profResp, specResp] = await Promise.all([
        fetch("/api/lintpdf/workflows").catch((e) => {
          console.error("[workflows] fetch threw", e);
          return null;
        }),
        fetch("/api/lintpdf/profiles").catch(() => null),
        fetch("/api/lintpdf/brand-specs").catch(() => null),
      ]);
      if (wfResp && wfResp.ok) {
        const data = await wfResp.json().catch(() => ({}));
        const list = Array.isArray(data)
          ? data
          : Array.isArray(data?.workflows)
            ? data.workflows
            : [];
        setWorkflows(list);
      } else if (wfResp) {
        const detail = await wfResp.text().catch(() => "");
        setFetchError(
          `Workflows API returned ${wfResp.status}${detail ? `: ${detail.slice(0, 200)}` : ""}`,
        );
      } else {
        setFetchError("Workflows API unreachable");
      }
      if (profResp && profResp.ok) {
        const data = await profResp.json().catch(() => ({}));
        setProfiles(Array.isArray(data?.profiles) ? data.profiles : []);
      }
      if (specResp && specResp.ok) {
        const data = await specResp.json().catch(() => ({}));
        setBrandSpecs(
          Array.isArray(data?.brand_specs) ? data.brand_specs : [],
        );
      }
    } catch (e) {
      console.error("[workflows] fetchAll threw", e);
      setFetchError(e instanceof Error ? e.message : "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  async function handleCreate() {
    if (!newName.trim() || !newProfileId) return;
    setCreating(true);
    try {
      const body: Record<string, string | null> = {
        name: newName.trim(),
        profile_id: newProfileId,
      };
      if (newBrandSpecId) body.brand_spec_id = newBrandSpecId;
      const resp = await fetch("/api/lintpdf/workflows", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || `Create failed (${resp.status})`);
      }
      setNewName("");
      setNewProfileId("");
      setNewBrandSpecId("");
      toast("Workflow created", "success");
      await fetchAll();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to create", "error");
    } finally {
      setCreating(false);
    }
  }

  async function openEditor(workflowId: string) {
    setEditorWorkflowId(workflowId);
    setEditorLoading(true);
    try {
      const [regResp, ovResp] = await Promise.all([
        fetch("/api/lintpdf/toggles"),
        fetch(`/api/lintpdf/workflows/${workflowId}/toggles`),
      ]);
      if (regResp.ok) {
        const data = await regResp.json();
        const items: ToggleRegistryRow[] = (data.items ?? []).filter(
          (t: ToggleRegistryRow) =>
            (t.override_at ?? []).includes("WORKFLOW") && !t.deprecated,
        );
        setRegistry(items);
      }
      if (ovResp.ok) {
        const data = await ovResp.json();
        setOverrides(data.items ?? []);
      }
    } catch (e) {
      toast(
        e instanceof Error ? e.message : "Failed to load defaults",
        "error",
      );
    } finally {
      setEditorLoading(false);
    }
  }

  function closeEditor() {
    setEditorWorkflowId(null);
    setRegistry([]);
    setOverrides([]);
  }

  async function setOverride(toggleId: string, raw: string, type: string) {
    if (!editorWorkflowId) return;
    let parsed: unknown = raw;
    try {
      if (type === "bool") parsed = raw === "true" || raw === "1";
      else if (type === "int") parsed = parseInt(raw, 10);
      else if (type === "float") parsed = parseFloat(raw);
      else if (type === "json") parsed = JSON.parse(raw);
    } catch {
      toast(`Invalid ${type} value for ${toggleId}`, "error");
      return;
    }
    try {
      const resp = await fetch(
        `/api/lintpdf/workflows/${editorWorkflowId}/toggles/${encodeURIComponent(toggleId)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: parsed }),
        },
      );
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || `Save failed (${resp.status})`);
      }
      const body = await resp.json();
      setOverrides((prev) => {
        const others = prev.filter((o) => o.toggle_id !== toggleId);
        return [...others, body];
      });
      toast(`${toggleId} saved`, "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to save", "error");
    }
  }

  async function clearOverride(toggleId: string) {
    if (!editorWorkflowId) return;
    try {
      const resp = await fetch(
        `/api/lintpdf/workflows/${editorWorkflowId}/toggles/${encodeURIComponent(toggleId)}`,
        { method: "DELETE" },
      );
      if (!resp.ok && resp.status !== 204) {
        const detail = await resp.text();
        throw new Error(detail || `Clear failed (${resp.status})`);
      }
      setOverrides((prev) => prev.filter((o) => o.toggle_id !== toggleId));
      toast(`${toggleId} cleared`, "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to clear", "error");
    }
  }

  async function handleDelete(id: string) {
    try {
      const resp = await fetch(`/api/lintpdf/workflows/${id}`, {
        method: "DELETE",
      });
      if (!resp.ok && resp.status !== 204) {
        const detail = await resp.text();
        throw new Error(detail || `Delete failed (${resp.status})`);
      }
      toast("Workflow deleted", "success");
      await fetchAll();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to delete", "error");
    }
  }

  if (loading) return <SkeletonDashboard type="cards" />;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-2xl font-bold">Workflows</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          A workflow pins a profile + brand spec + per-call override
          defaults so jobs can be submitted with a single named handle.
          Replaces the legacy <code>/dashboard/endpoints</code> surface
          from the Phase 0.7 unified-config substrate rollout.
        </p>
      </header>

      {fetchError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {fetchError}
        </div>
      )}

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Create workflow
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <FormField label="Name">
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Coated stock"
            />
          </FormField>
          <FormField label="Profile">
            <select
              value={newProfileId}
              onChange={(e) => setNewProfileId(e.target.value)}
              className="w-full rounded border border-border bg-background px-2 py-1.5"
            >
              <option value="">— select profile —</option>
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.name} ({p.profile_id})
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Brand spec (optional)">
            <select
              value={newBrandSpecId}
              onChange={(e) => setNewBrandSpecId(e.target.value)}
              className="w-full rounded border border-border bg-background px-2 py-1.5"
            >
              <option value="">— none —</option>
              {brandSpecs.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </FormField>
        </div>
        <div className="mt-3">
          <Button
            onClick={handleCreate}
            loading={creating}
            disabled={!newName.trim() || !newProfileId}
          >
            Create workflow
          </Button>
        </div>
      </section>

      {workflows.length === 0 ? (
        <EmptyState
          title="No workflows yet"
          description="Create one above. Workflows replace the legacy custom endpoints."
        />
      ) : (
        <section className="rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/40 text-left">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Profile</th>
                <th className="px-4 py-2 font-medium">Brand spec</th>
                <th className="px-4 py-2 font-medium">Created</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {workflows.map((wf) => (
                <tr key={wf.id} className="border-t border-border">
                  <td className="px-4 py-2">{wf.name}</td>
                  <td className="px-4 py-2">
                    <code className="text-xs">{wf.profile_id}</code>
                  </td>
                  <td className="px-4 py-2">
                    {wf.brand_spec_id ? (
                      <code className="text-xs">{wf.brand_spec_id}</code>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-muted-foreground">
                    {wf.created_at ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <Button
                      variant="ghost"
                      onClick={() => openEditor(wf.id)}
                    >
                      Manage defaults
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => handleDelete(wf.id)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {editorWorkflowId && (
        <section className="rounded-lg border border-border bg-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Toggle defaults
              </h2>
              <p className="text-xs text-muted-foreground">
                Workflow {editorWorkflowId}. Setting a value here pins the
                default for every job submitted against this workflow; jobs
                can still override per-call.
              </p>
            </div>
            <Button variant="ghost" onClick={closeEditor}>
              Close
            </Button>
          </div>
          {editorLoading ? (
            <p className="text-sm text-muted-foreground">Loading registry…</p>
          ) : registry.length === 0 ? (
            <EmptyState
              title="No overridable toggles"
              description="No registry rows allow WORKFLOW-scope overrides."
            />
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-muted/40 text-left">
                <tr>
                  <th className="px-3 py-2 font-medium">Toggle</th>
                  <th className="px-3 py-2 font-medium">Type</th>
                  <th className="px-3 py-2 font-medium">Default</th>
                  <th className="px-3 py-2 font-medium">Workflow value</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {registry.map((t) => {
                  const ov = overrides.find((o) => o.toggle_id === t.id);
                  const display =
                    ov !== undefined ? JSON.stringify(ov.value) : "";
                  return (
                    <tr key={t.id} className="border-t border-border">
                      <td className="px-3 py-2 align-top">
                        <div className="font-mono text-xs">{t.id}</div>
                        <div className="text-xs text-muted-foreground">
                          {t.human_name}
                        </div>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <code className="text-xs">{t.type}</code>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <code className="text-xs text-muted-foreground">
                          {JSON.stringify(t.default_value)}
                        </code>
                      </td>
                      <td className="px-3 py-2 align-top">
                        <Input
                          defaultValue={display}
                          placeholder="(unset)"
                          onBlur={(e) => {
                            const v = e.currentTarget.value.trim();
                            if (v === "" && ov === undefined) return;
                            if (v === display) return;
                            void setOverride(t.id, v, t.type);
                          }}
                        />
                      </td>
                      <td className="px-3 py-2 align-top text-right">
                        {ov !== undefined && (
                          <Button
                            variant="ghost"
                            onClick={() => clearOverride(t.id)}
                          >
                            Clear
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
