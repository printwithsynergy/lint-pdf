"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { useToast } from "@thinkneverland/pixie-dust-ui";
import { ConfirmDialog } from "@thinkneverland/pixie-dust-ui";
import { Button, Input, Select, FormField } from "@thinkneverland/pixie-dust-ui";

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

  // Confirm dialog state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);

  const { toast } = useToast();

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
      toast(e instanceof Error ? e.message : "Failed to load profile", "error");
    }
  }

  async function cloneProfile(profile: ProfileSummary) {
    const detail = await fetch(`/api/lintpdf/profiles/${profile.profile_id}`);
    if (!detail.ok) {
      toast("Failed to load profile for cloning", "error");
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
      toast("Ruleset created successfully", "success");
      await fetchProfiles();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to create profile", "error");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(profileId: string) {
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
      toast("Ruleset deleted", "success");
      await fetchProfiles();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to delete profile", "error");
    }
  }

  if (loading) {
    return <SkeletonDashboard type="cards" />;
  }

  const builtins = profiles.filter((p) => p.is_builtin);
  const custom = profiles.filter((p) => !p.is_builtin);

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Rulesets</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Preflight profiles that define which checks run and with what
            thresholds.
          </p>
        </div>
        <Button
          onClick={() => {
            setShowCreate(!showCreate);
            if (!showCreate) {
              setNewProfileId("");
              setNewName("");
              setNewDescription("");
            }
          }}
        >
          {showCreate ? "Cancel" : "New Ruleset"}
        </Button>
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
            <FormField label="Profile ID" htmlFor="profile-id" helpText="Lowercase kebab-case (e.g. my-magazine-ads)">
              <Input
                id="profile-id"
                value={newProfileId}
                onChange={(e) => setNewProfileId(e.target.value)}
                placeholder="my-custom-profile"
              />
            </FormField>
            <FormField label="Name" htmlFor="profile-name">
              <Input
                id="profile-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Custom Profile"
              />
            </FormField>
            <div className="sm:col-span-2">
              <FormField label="Description" htmlFor="profile-desc">
                <Input
                  id="profile-desc"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Custom profile for..."
                />
              </FormField>
            </div>
            <FormField label="Workflow" htmlFor="workflow">
              <Select
                id="workflow"
                value={newWorkflow}
                onChange={(e) => setNewWorkflow(e.target.value)}
              >
                <option value="CMYK">CMYK</option>
                <option value="RGB">RGB</option>
                <option value="auto">Auto</option>
              </Select>
            </FormField>
            <FormField label="Conformance" htmlFor="conformance">
              <Select
                id="conformance"
                value={newConformance}
                onChange={(e) => setNewConformance(e.target.value)}
              >
                <option value="">None</option>
                <option value="pdfx4">PDF/X-4</option>
                <option value="pdfx1a">PDF/X-1a</option>
                <option value="pdfa">PDF/A</option>
              </Select>
            </FormField>
          </div>

          {/* Thresholds */}
          <h3 className="mt-4 text-sm font-semibold">Thresholds</h3>
          <div className="mt-2 grid gap-3 sm:grid-cols-3">
            <FormField label="Min DPI" htmlFor="min-dpi">
              <Input
                id="min-dpi"
                type="number"
                value={newThresholds.min_dpi}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    min_dpi: Number(e.target.value),
                  }))
                }
              />
            </FormField>
            <FormField label="Max DPI" htmlFor="max-dpi">
              <Input
                id="max-dpi"
                type="number"
                value={newThresholds.max_dpi}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    max_dpi: Number(e.target.value),
                  }))
                }
              />
            </FormField>
            <FormField label="TAC Limit (%)" htmlFor="tac-limit">
              <Input
                id="tac-limit"
                type="number"
                value={newThresholds.tac_limit}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    tac_limit: Number(e.target.value),
                  }))
                }
              />
            </FormField>
            <FormField label="Min Bleed (mm)" htmlFor="min-bleed">
              <Input
                id="min-bleed"
                type="number"
                step="0.5"
                value={newThresholds.min_bleed_mm}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    min_bleed_mm: Number(e.target.value),
                  }))
                }
              />
            </FormField>
            <FormField label="Hairline (pt)" htmlFor="hairline">
              <Input
                id="hairline"
                type="number"
                step="0.05"
                value={newThresholds.hairline_threshold}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    hairline_threshold: Number(e.target.value),
                  }))
                }
              />
            </FormField>
            <FormField label="Small Text (pt)" htmlFor="small-text">
              <Input
                id="small-text"
                type="number"
                step="0.5"
                value={newThresholds.small_text_threshold}
                onChange={(e) =>
                  setNewThresholds((t) => ({
                    ...t,
                    small_text_threshold: Number(e.target.value),
                  }))
                }
              />
            </FormField>
          </div>

          <Button
            onClick={handleCreate}
            disabled={!newProfileId || !newName}
            loading={creating}
            className="mt-4"
          >
            Create Ruleset
          </Button>
        </div>
      )}

      {/* Profile detail panel */}
      {selectedProfile && !showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">{selectedProfile.name}</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedProfile(null)}
            >
              Close
            </Button>
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
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => viewProfile(p.profile_id)}
                  >
                    View
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => {
                      setConfirmTarget(p.profile_id);
                      setConfirmOpen(true);
                    }}
                  >
                    Delete
                  </Button>
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
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => viewProfile(p.profile_id)}
                >
                  View
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => cloneProfile(p)}
                >
                  Clone
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => {
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        onConfirm={async () => {
          if (confirmTarget) await handleDelete(confirmTarget);
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        title="Delete ruleset?"
        description="This action cannot be undone. Any jobs using this profile will need a different ruleset."
        variant="destructive"
        confirmLabel="Delete"
      />
    </>
  );
}
