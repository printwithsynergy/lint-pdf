"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface ProfileSummary {
  profile_id: string;
  name: string;
  description: string;
  conformance: string | null;
  workflow: string;
  is_builtin: boolean;
}

interface ProfileDetail extends ProfileSummary {
  version: string;
  checks: Record<string, unknown>;
  thresholds: Record<string, unknown>;
}

export default function RulesetsPage() {
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<ProfileDetail | null>(
    null,
  );

  // Create/clone form
  const [showCreate, setShowCreate] = useState(false);
  const [newProfileId, setNewProfileId] = useState("");
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newWorkflow, setNewWorkflow] = useState("CMYK");
  const [newConformance, setNewConformance] = useState("");
  const [newThresholds, setNewThresholds] = useState({
    min_dpi: 150,
    max_dpi: 600,
    tac_limit: 300,
    min_bleed_mm: 3.0,
    hairline_threshold: 0.25,
    small_text_threshold: 6.0,
    safety_margin_mm: 3.0,
  });
  const [creating, setCreating] = useState(false);

  const fetchProfiles = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/profiles");
      if (!resp.ok) throw new Error("Failed to load profiles");
      const data = await resp.json();
      setProfiles(data.profiles ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profiles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  async function viewProfile(profileId: string) {
    try {
      const resp = await fetch(`/api/lintpdf/profiles/${profileId}`);
      if (!resp.ok) throw new Error("Failed to load profile");
      const data = await resp.json();
      setSelectedProfile(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    }
  }

  async function cloneProfile(profile: ProfileSummary) {
    const detail = await fetch(`/api/lintpdf/profiles/${profile.profile_id}`);
    if (!detail.ok) {
      setError("Failed to load profile for cloning");
      return;
    }
    const data: ProfileDetail = await detail.json();
    setNewProfileId(`${profile.profile_id}-custom`);
    setNewName(`${data.name} (Copy)`);
    setNewDescription(data.description);
    setNewWorkflow(data.workflow);
    setNewConformance(data.conformance ?? "");
    if (data.thresholds && typeof data.thresholds === "object") {
      setNewThresholds((prev) => ({
        ...prev,
        ...(data.thresholds as Record<string, number>),
      }));
    }
    setShowCreate(true);
  }

  async function handleCreate() {
    setCreating(true);
    setError("");
    try {
      const resp = await fetch("/api/lintpdf/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_id: newProfileId,
          preflight_profile: {
            name: newName,
            description: newDescription,
            version: "1.0",
            conformance: newConformance || null,
            workflow: newWorkflow,
            checks: { enabled: ["GRD_*"], disabled: [] },
            thresholds: newThresholds,
          },
        }),
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to create profile");
      }
      setShowCreate(false);
      setNewProfileId("");
      setNewName("");
      setNewDescription("");
      await fetchProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create profile");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(profileId: string) {
    if (!confirm("Are you sure you want to delete this profile?")) return;
    try {
      const resp = await fetch(`/api/lintpdf/profiles/${profileId}`, {
        method: "DELETE",
      });
      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.error ?? "Failed to delete profile");
      }
      if (selectedProfile?.profile_id === profileId) {
        setSelectedProfile(null);
      }
      await fetchProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete profile");
    }
  }

  if (loading) {
    return <SkeletonDashboard type="cards" />;
  }

  const builtins = profiles.filter((p) => p.is_builtin);
  const custom = profiles.filter((p) => !p.is_builtin);

  return (
    <main className="p-8 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Rulesets</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Preflight profiles that define which checks run and with what
            thresholds.
          </p>
        </div>
        <button
          onClick={() => {
            setShowCreate(!showCreate);
            if (!showCreate) {
              setNewProfileId("");
              setNewName("");
              setNewDescription("");
            }
          }}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showCreate ? "Cancel" : "New Ruleset"}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            dismiss
          </button>
        </div>
      )}

      {/* Create/edit form */}
      {showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">
            {newProfileId.endsWith("-custom")
              ? "Clone Profile"
              : "New Ruleset"}
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium">Profile ID</label>
              <input
                type="text"
                value={newProfileId}
                onChange={(e) => setNewProfileId(e.target.value)}
                placeholder="my-custom-profile"
                pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
              <p className="mt-0.5 text-xs text-muted-foreground">
                Lowercase kebab-case (e.g. my-magazine-ads)
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Custom Profile"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium">Description</label>
              <input
                type="text"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Custom profile for..."
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">Workflow</label>
              <select
                value={newWorkflow}
                onChange={(e) => setNewWorkflow(e.target.value)}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="CMYK">CMYK</option>
                <option value="RGB">RGB</option>
                <option value="auto">Auto</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium">Conformance</label>
              <select
                value={newConformance}
                onChange={(e) => setNewConformance(e.target.value)}
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="">None</option>
                <option value="pdfx4">PDF/X-4</option>
                <option value="pdfx1a">PDF/X-1a</option>
                <option value="pdfa">PDF/A</option>
              </select>
            </div>
          </div>

          {/* Thresholds */}
          <h3 className="mt-4 text-sm font-semibold">Thresholds</h3>
          <div className="mt-2 grid gap-3 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-medium">Min DPI</label>
              <input
                type="number"
                value={newThresholds.min_dpi}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    min_dpi: Number(e.target.value),
                  }))
                }
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Max DPI</label>
              <input
                type="number"
                value={newThresholds.max_dpi}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    max_dpi: Number(e.target.value),
                  }))
                }
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">TAC Limit (%)</label>
              <input
                type="number"
                value={newThresholds.tac_limit}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    tac_limit: Number(e.target.value),
                  }))
                }
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">
                Min Bleed (mm)
              </label>
              <input
                type="number"
                step="0.5"
                value={newThresholds.min_bleed_mm}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    min_bleed_mm: Number(e.target.value),
                  }))
                }
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">Hairline (pt)</label>
              <input
                type="number"
                step="0.05"
                value={newThresholds.hairline_threshold}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    hairline_threshold: Number(e.target.value),
                  }))
                }
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium">
                Small Text (pt)
              </label>
              <input
                type="number"
                step="0.5"
                value={newThresholds.small_text_threshold}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    small_text_threshold: Number(e.target.value),
                  }))
                }
                className="mt-1 w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
          </div>

          <button
            onClick={handleCreate}
            disabled={creating || !newProfileId || !newName}
            className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create Ruleset"}
          </button>
        </div>
      )}

      {/* Profile detail panel */}
      {selectedProfile && !showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{selectedProfile.name}</h2>
            <button
              onClick={() => setSelectedProfile(null)}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
          <p className="text-sm text-muted-foreground">
            {selectedProfile.description}
          </p>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <span className="font-medium">ID:</span>{" "}
              <code>{selectedProfile.profile_id}</code>
            </div>
            <div>
              <span className="font-medium">Workflow:</span>{" "}
              {selectedProfile.workflow}
            </div>
            <div>
              <span className="font-medium">Conformance:</span>{" "}
              {selectedProfile.conformance ?? "None"}
            </div>
          </div>
          {selectedProfile.thresholds &&
            Object.keys(selectedProfile.thresholds).length > 0 && (
              <div className="mt-3">
                <h3 className="text-sm font-semibold">Thresholds</h3>
                <div className="mt-1 grid gap-1 text-xs sm:grid-cols-3">
                  {Object.entries(
                    selectedProfile.thresholds as Record<string, unknown>,
                  ).map(([key, val]) => (
                    <div key={key}>
                      <span className="font-medium">
                        {key.replace(/_/g, " ")}:
                      </span>{" "}
                      {String(val)}
                    </div>
                  ))}
                </div>
              </div>
            )}
        </div>
      )}

      {/* Custom profiles */}
      {custom.length > 0 && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold">Custom Rulesets</h2>
          <div className="mt-2 space-y-2">
            {custom.map((p) => (
              <div
                key={p.profile_id}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div
                  className="min-w-0 flex-1 cursor-pointer"
                  onClick={() => viewProfile(p.profile_id)}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{p.name}</span>
                    <code className="text-xs text-muted-foreground">
                      {p.profile_id}
                    </code>
                  </div>
                  <p className="truncate text-sm text-muted-foreground">
                    {p.description}
                  </p>
                  <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                    <span>{p.workflow}</span>
                    {p.conformance && <span>{p.conformance}</span>}
                  </div>
                </div>
                <div className="ml-4 flex shrink-0 gap-1">
                  <button
                    onClick={() => viewProfile(p.profile_id)}
                    className="rounded border px-2 py-1 text-xs hover:bg-muted"
                  >
                    View
                  </button>
                  <button
                    onClick={() => handleDelete(p.profile_id)}
                    className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Built-in profiles */}
      <div className="mt-6">
        <h2 className="text-lg font-semibold">Built-in Rulesets</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Pre-configured profiles provided by LintPDF. Clone to customize.
        </p>
        <div className="mt-2 space-y-2">
          {builtins.map((p) => (
            <div
              key={p.profile_id}
              className="flex items-center justify-between rounded-lg border p-3"
            >
              <div
                className="min-w-0 flex-1 cursor-pointer"
                onClick={() => viewProfile(p.profile_id)}
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium">{p.name}</span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                    built-in
                  </span>
                </div>
                <p className="truncate text-sm text-muted-foreground">
                  {p.description}
                </p>
                <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
                  <span>{p.workflow}</span>
                  {p.conformance && <span>{p.conformance}</span>}
                </div>
              </div>
              <div className="ml-4 flex shrink-0 gap-1">
                <button
                  onClick={() => viewProfile(p.profile_id)}
                  className="rounded border px-2 py-1 text-xs hover:bg-muted"
                >
                  View
                </button>
                <button
                  onClick={() => cloneProfile(p)}
                  className="rounded border px-2 py-1 text-xs hover:bg-muted"
                >
                  Clone
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
