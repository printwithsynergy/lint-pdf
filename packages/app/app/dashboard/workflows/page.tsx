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

  const fetchAll = useCallback(async () => {
    try {
      const [wfResp, profResp, specResp] = await Promise.all([
        fetch("/api/lintpdf/workflows"),
        fetch("/api/lintpdf/profiles").catch(() => null),
        fetch("/api/lintpdf/brand-specs").catch(() => null),
      ]);
      if (wfResp.ok) {
        const data = await wfResp.json();
        setWorkflows(data.workflows ?? data ?? []);
      }
      if (profResp && profResp.ok) {
        const data = await profResp.json();
        setProfiles(data.profiles ?? []);
      }
      if (specResp && specResp.ok) {
        const data = await specResp.json();
        setBrandSpecs(data.brand_specs ?? []);
      }
    } catch (e) {
      toast(
        `Failed to load workflows: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [toast]);

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
                  <td className="px-4 py-2 text-right">
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
    </div>
  );
}
