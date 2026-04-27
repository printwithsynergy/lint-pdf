"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface CustomEndpoint {
  id: string;
  slug: string;
  profile_id: string;
  description: string;
  is_active: boolean;
  created_at: string;
  default_brand_spec_id: string | null;
}

interface ProfileSummary {
  profile_id: string;
  name: string;
  is_builtin: boolean;
}

interface BrandSpecSummary {
  id: string;
  name: string;
  customer_name: string | null;
  is_default: boolean;
}

export default function EndpointsPage() {
  const [endpoints, setEndpoints] = useState<CustomEndpoint[]>([]);
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [brandSpecs, setBrandSpecs] = useState<BrandSpecSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newSlug, setNewSlug] = useState("");
  const [newProfileId, setNewProfileId] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newBrandSpecId, setNewBrandSpecId] = useState("");
  const [creating, setCreating] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editSlug, setEditSlug] = useState("");
  const [editProfileId, setEditProfileId] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editBrandSpecId, setEditBrandSpecId] = useState("");

  const apiBaseUrl = process.env.NEXT_PUBLIC_LINTPDF_API_URL ?? "";

  const fetchData = useCallback(async () => {
    try {
      const [epResp, profResp, specResp] = await Promise.all([
        fetch("/api/lintpdf/endpoints"),
        fetch("/api/lintpdf/profiles"),
        fetch("/api/lintpdf/brand-specs"),
      ]);
      if (epResp.ok) {
        const data = await epResp.json();
        setEndpoints(data.endpoints ?? []);
      }
      if (profResp.ok) {
        const data = await profResp.json();
        setProfiles(data.profiles ?? []);
      }
      if (specResp.ok) {
        const data = await specResp.json();
        // The list route returns ``brand_specs``; tolerate an
        // outage by leaving the dropdown empty so the endpoint
        // picker still works without brand specs.
        setBrandSpecs(data.brand_specs ?? []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleCreate() {
    setCreating(true);
    setError("");
    try {
      const resp = await fetch("/api/lintpdf/endpoints", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug: newSlug,
          profile_id: newProfileId,
          description: newDescription,
          default_brand_spec_id: newBrandSpecId || null,
        }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to create endpoint");
      }
      setNewSlug("");
      setNewProfileId("");
      setNewDescription("");
      setNewBrandSpecId("");
      setShowCreate(false);
      await fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create endpoint");
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdate(id: string) {
    setError("");
    try {
      const resp = await fetch(`/api/lintpdf/endpoints/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug: editSlug,
          profile_id: editProfileId,
          description: editDescription,
          // Empty string → "null" sentinel so the server
          // clears the FK (Pydantic validator on the route
          // accepts that string as "unset this").
          default_brand_spec_id: editBrandSpecId || "null",
        }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to update endpoint");
      }
      setEditingId(null);
      await fetchData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update endpoint");
    }
  }

  async function handleToggle(id: string, isActive: boolean) {
    try {
      await fetch(`/api/lintpdf/endpoints/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !isActive }),
      });
      await fetchData();
    } catch {
      setError("Failed to toggle endpoint");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this custom endpoint?")) return;
    try {
      await fetch(`/api/lintpdf/endpoints/${id}`, { method: "DELETE" });
      await fetchData();
    } catch {
      setError("Failed to delete endpoint");
    }
  }

  if (loading) {
    return <SkeletonDashboard type="table" />;
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">
            Custom API Endpoints
            <span className="ml-2 rounded bg-warning/15 px-2 py-0.5 align-middle text-xs font-semibold text-warning">
              Deprecated
            </span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Create vanity URL slugs bound to specific profiles for simplified
            integrations.
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "Cancel" : "New Endpoint"}
        </Button>
      </div>

      <div className="mt-4 rounded-lg border-l-4 border-l-warning bg-warning/5 p-3 text-sm">
        <strong>Endpoints are deprecated.</strong> The Phase 0.7
        unified-config substrate replaces this surface with{" "}
        <Link
          href="/dashboard/workflows"
          className="font-medium text-primary underline"
        >
          Workflows
        </Link>
        , which pin a profile + brand spec + per-call overrides under a
        single name. New integrations should target Workflows; existing
        Endpoints continue to work but will be hard-removed in a future
        release once telemetry shows zero traffic.
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">New Custom Endpoint</h2>
          <div className="mt-3 space-y-3">
            <div>
              <label className="block text-sm font-medium">URL Slug</label>
              <input
                type="text"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                placeholder="my-magazine-check"
                pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
              <p className="mt-0.5 text-xs text-muted-foreground">
                URL:{" "}
                <code>
                  {apiBaseUrl}/api/v1/e/{newSlug || "your-slug"}
                </code>
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium">Profile</label>
              <select
                value={newProfileId}
                onChange={(e) => setNewProfileId(e.target.value)}
                className="mt-1 h-10 w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="">Select a profile...</option>
                {profiles.map((p) => (
                  <option key={p.profile_id} value={p.profile_id}>
                    {p.name} ({p.profile_id}){p.is_builtin ? " [built-in]" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium">Description</label>
              <input
                type="text"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Optional description"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">
                Default brand spec
              </label>
              <select
                value={newBrandSpecId}
                onChange={(e) => setNewBrandSpecId(e.target.value)}
                className="mt-1 h-10 w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="">
                  None (fall back to tenant default)
                </option>
                {brandSpecs.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                    {s.customer_name ? ` — ${s.customer_name}` : ""}
                    {s.is_default ? " (tenant default)" : ""}
                  </option>
                ))}
              </select>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Applied to every submission through this endpoint unless the
                caller supplies <code>brand_spec_id</code>.
              </p>
            </div>
            <Button
              onClick={handleCreate}
              disabled={creating || !newSlug || !newProfileId}
              loading={creating}
            >
              Create Endpoint
            </Button>
          </div>
        </div>
      )}

      {/* Endpoints list */}
      <div className="mt-6 space-y-3">
        {endpoints.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
            No custom endpoints yet. Create one to simplify your API
            integrations.
          </div>
        ) : (
          endpoints.map((ep) => (
            <div key={ep.id} className="rounded-lg border p-4">
              {editingId === ep.id ? (
                <div className="space-y-3">
                  <input
                    type="text"
                    value={editSlug}
                    onChange={(e) => setEditSlug(e.target.value)}
                    className="w-full rounded-md border px-3 py-2 text-sm"
                  />
                  <select
                    value={editProfileId}
                    onChange={(e) => setEditProfileId(e.target.value)}
                    className="h-10 w-full rounded-md border px-3 py-2 text-sm"
                  >
                    {profiles.map((p) => (
                      <option key={p.profile_id} value={p.profile_id}>
                        {p.name} ({p.profile_id})
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className="w-full rounded-md border px-3 py-2 text-sm"
                  />
                  <select
                    value={editBrandSpecId}
                    onChange={(e) => setEditBrandSpecId(e.target.value)}
                    className="h-10 w-full rounded-md border px-3 py-2 text-sm"
                  >
                    <option value="">
                      No default brand spec (fall back to tenant default)
                    </option>
                    {brandSpecs.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                        {s.customer_name ? ` — ${s.customer_name}` : ""}
                        {s.is_default ? " (tenant default)" : ""}
                      </option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdate(ep.id)}
                      className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="rounded-md border px-3 py-1.5 text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-block h-2 w-2 rounded-full ${ep.is_active ? "bg-green-500" : "bg-gray-300"}`}
                      />
                      <code className="font-medium">/api/v1/e/{ep.slug}</code>
                    </div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      Profile: <code>{ep.profile_id}</code>
                      {ep.default_brand_spec_id ? (
                        <>
                          {" · "}
                          Brand spec:{" "}
                          <code>
                            {brandSpecs.find((s) => s.id === ep.default_brand_spec_id)
                              ?.name ?? ep.default_brand_spec_id}
                          </code>
                        </>
                      ) : (
                        <>{" · "}No brand spec override</>
                      )}
                    </div>
                    {ep.description && (
                      <p className="mt-0.5 text-sm text-muted-foreground">
                        {ep.description}
                      </p>
                    )}
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Created {new Date(ep.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="ml-4 flex shrink-0 gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setEditingId(ep.id);
                        setEditSlug(ep.slug);
                        setEditProfileId(ep.profile_id);
                        setEditDescription(ep.description);
                        setEditBrandSpecId(ep.default_brand_spec_id ?? "");
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleToggle(ep.id, ep.is_active)}
                    >
                      {ep.is_active ? "Disable" : "Enable"}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(ep.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );
}
