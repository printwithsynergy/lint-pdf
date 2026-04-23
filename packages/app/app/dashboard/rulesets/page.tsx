"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import { useToast } from "@thinkneverland/pixie-dust-ui";
import { ConfirmDialog } from "@thinkneverland/pixie-dust-ui";
import { Button, Input, Select, FormField } from "@thinkneverland/pixie-dust-ui";
import { RulesEditor } from "@/components/rules/RulesEditor";
import type { Profile as RulesProfile } from "@/lib/rules/profile-utils";

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

interface AdminTenantProfiles {
  tenant_id: string;
  tenant_name: string | null;
  profiles: ProfileSummary[];
}

interface AdminProfileList {
  system: ProfileSummary[];
  tenants: AdminTenantProfiles[];
}

type Mode = "tenant" | "admin";

/**
 * Group-owner key used when CRUD-ing a profile:
 * - "self"       → tenant-scoped endpoint (own customs)
 * - "system"     → built-in (read-only / clone only)
 * - "<tenantId>" → admin writes against that specific tenant
 */
type OwnerKey = "self" | "system" | string;

async function fetchDetailRaw(owner: OwnerKey, profileId: string): Promise<Response> {
  if (owner === "self") {
    return fetch(`/api/lintpdf/profiles/${profileId}`);
  }
  if (owner === "system") {
    return fetch(`/api/lintpdf/profiles/${profileId}`);
  }
  return fetch(
    `/api/lintpdf/admin/tenants/${owner}/profiles/${profileId}`,
  );
}

async function readErrorDetail(resp: Response, fallback: string): Promise<string> {
  const text = await resp.text();
  try {
    const data = JSON.parse(text);
    const detail = data?.error ?? data?.detail ?? text;
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  } catch {
    return text || fallback;
  }
}

export default function RulesetsPage() {
  const [mode, setMode] = useState<Mode>("tenant");
  const [tenantProfiles, setTenantProfiles] = useState<ProfileSummary[]>([]);
  const [adminData, setAdminData] = useState<AdminProfileList | null>(null);
  const [expandedTenants, setExpandedTenants] = useState<Set<string>>(
    () => new Set(),
  );
  const [expandSystem, setExpandSystem] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Selected profile detail (viewer panel)
  const [selectedOwner, setSelectedOwner] = useState<OwnerKey | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<ProfileDetail | null>(
    null,
  );

  // Anchor for the editor/viewer panels so View / Clone / New Ruleset can
  // scroll the user up to the panel instead of leaving it below the fold.
  const editorAnchorRef = useRef<HTMLDivElement | null>(null);
  const scrollToEditor = useCallback(() => {
    // rAF + setTimeout so the scroll happens after React commits the panel.
    requestAnimationFrame(() => {
      setTimeout(() => {
        editorAnchorRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 50);
    });
  }, []);

  // Create/edit form
  const [showCreate, setShowCreate] = useState(false);
  const [editingOwner, setEditingOwner] = useState<OwnerKey>("self");
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

  // Confirm dialog
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<{
    owner: OwnerKey;
    profileId: string;
  } | null>(null);

  const { toast } = useToast();

  const fetchProfiles = useCallback(async () => {
    setLoading(true);
    setError("");
    // Try the admin endpoint first — if it 200s, we're super-admin and get
    // the cross-tenant grouped view. On 401/403, fall back to the tenant
    // endpoint so regular members still see their own + defaults.
    try {
      const adminResp = await fetch("/api/lintpdf/admin/profiles");
      if (adminResp.ok) {
        const data: AdminProfileList = await adminResp.json();
        setMode("admin");
        setAdminData(data);
        setLoading(false);
        return;
      }
      if (adminResp.status !== 401 && adminResp.status !== 403) {
        const detail = await readErrorDetail(
          adminResp,
          `Failed to load admin profiles (${adminResp.status})`,
        );
        // Admin endpoint reachable but errored — surface and fall through to
        // tenant scope so the user still has something.
        console.warn(
          `[rulesets] admin endpoint ${adminResp.status}: ${detail}`,
        );
      }
    } catch (e) {
      console.warn("[rulesets] admin endpoint fetch threw", e);
    }

    try {
      const resp = await fetch("/api/lintpdf/profiles");
      if (!resp.ok) {
        const detail = await readErrorDetail(
          resp,
          `Failed to load profiles (${resp.status})`,
        );
        throw new Error(`Failed to load profiles (${resp.status}): ${detail}`);
      }
      const data = await resp.json();
      setMode("tenant");
      setTenantProfiles(data.profiles ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profiles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  const viewProfile = useCallback(
    async (owner: OwnerKey, profileId: string) => {
      try {
        const resp = await fetchDetailRaw(owner, profileId);
        if (!resp.ok) {
          const detail = await readErrorDetail(resp, "Failed to load profile");
          throw new Error(`(${resp.status}) ${detail}`);
        }
        const data: ProfileDetail = await resp.json();
        setSelectedOwner(owner);
        setSelectedProfile(data);
        scrollToEditor();
      } catch (e) {
        toast(
          e instanceof Error ? e.message : "Failed to load profile",
          "error",
        );
      }
    },
    [toast, scrollToEditor],
  );

  const openCreate = useCallback(
    (owner: OwnerKey) => {
      setEditingOwner(owner);
      setNewProfileId("");
      setNewName("");
      setNewDescription("");
      setNewWorkflow("CMYK");
      setNewConformance("");
      setShowCreate(true);
      scrollToEditor();
    },
    [scrollToEditor],
  );

  const cloneProfile = useCallback(
    async (owner: OwnerKey, profile: ProfileSummary, targetOwner: OwnerKey) => {
      const resp = await fetchDetailRaw(owner, profile.profile_id);
      if (!resp.ok) {
        toast("Failed to load profile for cloning", "error");
        return;
      }
      const data: ProfileDetail = await resp.json();
      setEditingOwner(targetOwner);
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
      scrollToEditor();
    },
    [toast, scrollToEditor],
  );

  async function handleCreate() {
    setCreating(true);
    const body = {
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
    };

    try {
      const url =
        editingOwner === "self" || editingOwner === "system"
          ? "/api/lintpdf/profiles"
          : `/api/lintpdf/admin/tenants/${editingOwner}/profiles/${newProfileId}`;
      const method =
        editingOwner === "self" || editingOwner === "system" ? "POST" : "PUT";

      const resp = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...body, tenant_id: editingOwner }),
      });
      if (!resp.ok) {
        const detail = await readErrorDetail(resp, "Failed to save profile");
        throw new Error(`(${resp.status}) ${detail}`);
      }
      setShowCreate(false);
      setNewProfileId("");
      setNewName("");
      setNewDescription("");
      toast("Ruleset saved", "success");
      await fetchProfiles();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to save profile", "error");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(owner: OwnerKey, profileId: string) {
    try {
      const url =
        owner === "self"
          ? `/api/lintpdf/profiles/${profileId}`
          : `/api/lintpdf/admin/tenants/${owner}/profiles/${profileId}`;
      const resp = await fetch(url, { method: "DELETE" });
      if (!resp.ok) {
        const detail = await readErrorDetail(resp, "Failed to delete profile");
        throw new Error(`(${resp.status}) ${detail}`);
      }
      if (selectedProfile?.profile_id === profileId) {
        setSelectedProfile(null);
        setSelectedOwner(null);
      }
      toast("Ruleset deleted", "success");
      await fetchProfiles();
    } catch (e) {
      toast(
        e instanceof Error ? e.message : "Failed to delete profile",
        "error",
      );
    }
  }

  const tenantBuiltins = useMemo(
    () => tenantProfiles.filter((p) => p.is_builtin),
    [tenantProfiles],
  );
  const tenantCustoms = useMemo(
    () => tenantProfiles.filter((p) => !p.is_builtin),
    [tenantProfiles],
  );

  if (loading) return <SkeletonDashboard type="cards" />;

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Rulesets</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {mode === "admin"
              ? "System rulesets plus every tenant's custom rulesets."
              : "Preflight profiles that define which checks run and with what thresholds."}
          </p>
        </div>
        {mode === "tenant" && (
          <Button
            onClick={() => {
              if (showCreate) setShowCreate(false);
              else openCreate("self");
            }}
          >
            {showCreate ? "Cancel" : "New Ruleset"}
          </Button>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
          <button
            onClick={() => setError("")}
            className="ml-2 underline"
            type="button"
          >
            dismiss
          </button>
        </div>
      )}

      {/* Editor anchor — View / Clone / New Ruleset scroll here. */}
      <div ref={editorAnchorRef} aria-hidden="true" />

      {showCreate && (
        <CreateForm
          editingOwner={editingOwner}
          newProfileId={newProfileId}
          setNewProfileId={setNewProfileId}
          newName={newName}
          setNewName={setNewName}
          newDescription={newDescription}
          setNewDescription={setNewDescription}
          newWorkflow={newWorkflow}
          setNewWorkflow={setNewWorkflow}
          newConformance={newConformance}
          setNewConformance={setNewConformance}
          newThresholds={newThresholds}
          setNewThresholds={setNewThresholds}
          creating={creating}
          onSave={handleCreate}
          onCancel={() => setShowCreate(false)}
          tenants={adminData?.tenants ?? []}
        />
      )}

      {selectedProfile && !showCreate && (
        <ProfileDetailPanel
          profile={selectedProfile}
          owner={selectedOwner ?? "self"}
          onClose={() => {
            setSelectedProfile(null);
            setSelectedOwner(null);
          }}
          onSaved={async () => {
            // Re-fetch both the list and the currently-open detail
            // so the UI reflects the persisted state (and clears
            // the dirty indicator).
            await fetchProfiles();
            if (selectedOwner) {
              await viewProfile(selectedOwner, selectedProfile.profile_id);
            }
          }}
        />
      )}

      {mode === "admin" && adminData ? (
        <>
          <section className="mt-6 rounded-lg border">
            <button
              type="button"
              onClick={() => setExpandSystem((v) => !v)}
              className="flex w-full items-center justify-between p-3 text-left hover:bg-muted/40"
            >
              <span className="text-lg font-semibold">
                System Rulesets{" "}
                <span className="text-xs text-muted-foreground">
                  ({adminData.system.length})
                </span>
              </span>
              <span>{expandSystem ? "−" : "+"}</span>
            </button>
            {expandSystem && (
              <div className="space-y-2 border-t p-3">
                {adminData.system.map((p) => (
                  <ProfileRow
                    key={p.profile_id}
                    profile={p}
                    owner="system"
                    onView={() => viewProfile("system", p.profile_id)}
                    onClone={() => cloneProfile("system", p, "self")}
                    canDelete={false}
                    canEdit={false}
                  />
                ))}
              </div>
            )}
          </section>

          {adminData.tenants.map((t) => {
            const open = expandedTenants.has(t.tenant_id);
            return (
              <section key={t.tenant_id} className="mt-4 rounded-lg border">
                <button
                  type="button"
                  onClick={() =>
                    setExpandedTenants((s) => {
                      const n = new Set(s);
                      if (n.has(t.tenant_id)) n.delete(t.tenant_id);
                      else n.add(t.tenant_id);
                      return n;
                    })
                  }
                  className="flex w-full items-center justify-between p-3 text-left hover:bg-muted/40"
                >
                  <span className="font-semibold">
                    {t.tenant_name ?? t.tenant_id.slice(0, 8)}{" "}
                    <span className="text-xs text-muted-foreground">
                      ({t.profiles.length})
                    </span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={(e: React.MouseEvent) => {
                        e.stopPropagation();
                        openCreate(t.tenant_id);
                      }}
                    >
                      New
                    </Button>
                    <span>{open ? "−" : "+"}</span>
                  </span>
                </button>
                {open && (
                  <div className="space-y-2 border-t p-3">
                    {t.profiles.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        No custom rulesets.
                      </p>
                    ) : (
                      t.profiles.map((p) => (
                        <ProfileRow
                          key={p.profile_id}
                          profile={p}
                          owner={t.tenant_id}
                          onView={() =>
                            viewProfile(t.tenant_id, p.profile_id)
                          }
                          onClone={() =>
                            cloneProfile(t.tenant_id, p, t.tenant_id)
                          }
                          onDelete={() => {
                            setConfirmTarget({
                              owner: t.tenant_id,
                              profileId: p.profile_id,
                            });
                            setConfirmOpen(true);
                          }}
                          canDelete={true}
                          canEdit={true}
                        />
                      ))
                    )}
                  </div>
                )}
              </section>
            );
          })}
        </>
      ) : (
        <>
          {tenantCustoms.length > 0 && (
            <div className="mt-6">
              <h2 className="text-lg font-semibold">Custom Rulesets</h2>
              <div className="mt-2 space-y-2">
                {tenantCustoms.map((p) => (
                  <ProfileRow
                    key={p.profile_id}
                    profile={p}
                    owner="self"
                    onView={() => viewProfile("self", p.profile_id)}
                    onClone={() => cloneProfile("self", p, "self")}
                    onDelete={() => {
                      setConfirmTarget({
                        owner: "self",
                        profileId: p.profile_id,
                      });
                      setConfirmOpen(true);
                    }}
                    canDelete={true}
                    canEdit={true}
                  />
                ))}
              </div>
            </div>
          )}

          <div className="mt-6">
            <h2 className="text-lg font-semibold">Built-in Rulesets</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Pre-configured profiles provided by LintPDF. Clone to customize.
            </p>
            <div className="mt-2 space-y-2">
              {tenantBuiltins.map((p) => (
                <ProfileRow
                  key={p.profile_id}
                  profile={p}
                  owner="system"
                  onView={() => viewProfile("self", p.profile_id)}
                  onClone={() => cloneProfile("self", p, "self")}
                  canDelete={false}
                  canEdit={false}
                />
              ))}
            </div>
          </div>
        </>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => {
          setConfirmOpen(false);
          setConfirmTarget(null);
        }}
        onConfirm={async () => {
          if (confirmTarget)
            await handleDelete(confirmTarget.owner, confirmTarget.profileId);
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

function ProfileRow({
  profile,
  owner,
  onView,
  onClone,
  onDelete,
  canEdit,
  canDelete,
}: {
  profile: ProfileSummary;
  owner: OwnerKey;
  onView: () => void;
  onClone: () => void;
  onDelete?: () => void;
  canEdit: boolean;
  canDelete: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="min-w-0 flex-1 cursor-pointer" onClick={onView}>
        <div className="flex items-center gap-2">
          <span className="font-medium">{profile.name}</span>
          <code className="text-xs text-muted-foreground">
            {profile.profile_id}
          </code>
          {profile.is_builtin && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
              built-in
            </span>
          )}
          {!profile.is_builtin && owner !== "self" && (
            <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
              custom
            </span>
          )}
        </div>
        <p className="truncate text-sm text-muted-foreground">
          {profile.description}
        </p>
        <div className="mt-1 flex gap-2 text-xs text-muted-foreground">
          <span>{profile.workflow}</span>
          {profile.conformance && <span>{profile.conformance}</span>}
        </div>
      </div>
      <div className="ml-4 flex shrink-0 gap-1">
        <Button variant="secondary" size="sm" onClick={onView}>
          View
        </Button>
        <Button variant="secondary" size="sm" onClick={onClone}>
          {canEdit ? "Edit" : "Clone"}
        </Button>
        {canDelete && onDelete && (
          <Button variant="destructive" size="sm" onClick={onDelete}>
            Delete
          </Button>
        )}
      </div>
    </div>
  );
}

function ProfileDetailPanel({
  profile,
  owner,
  onClose,
  onSaved,
}: {
  profile: ProfileDetail;
  owner: OwnerKey;
  onClose: () => void;
  onSaved?: () => void;
}) {
  // WS-16 editable panel. The RulesEditor was introduced as
  // read-only in WS-12 ("backend PATCH path that doesn't exist
  // yet"). Every path it needs is actually already live:
  //   - tenant self-edit: POST /api/v1/profiles (upsert)
  //   - admin-writes-for-tenant: PUT /api/v1/admin/tenants/{id}/profiles/{id}
  //   - built-ins: still clone-only, same as the create flow.
  const baseline = profile as unknown as RulesProfile;
  const [edited, setEdited] = useState<RulesProfile>(baseline);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  // Reset the draft whenever the parent swaps the loaded profile
  // (e.g. the user picks a different row, or we reload after save).
  useEffect(() => {
    setEdited(profile as unknown as RulesProfile);
    setSaveError(null);
    setSavedMessage(null);
  }, [profile]);

  const isBuiltIn = owner === "system" || profile.is_builtin;
  const isDirty = JSON.stringify(edited) !== JSON.stringify(baseline);

  async function handleSave() {
    if (isBuiltIn || !isDirty) return;
    setSaving(true);
    setSaveError(null);
    setSavedMessage(null);
    try {
      const url =
        owner === "self"
          ? "/api/lintpdf/profiles"
          : `/api/lintpdf/admin/tenants/${owner}/profiles/${profile.profile_id}`;
      const method = owner === "self" ? "POST" : "PUT";
      const body =
        owner === "self"
          ? {
              profile_id: profile.profile_id,
              preflight_profile: edited,
            }
          : { preflight_profile: edited };
      const resp = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const detail = await readErrorDetail(resp, "Save failed");
        throw new Error(`(${resp.status}) ${detail}`);
      }
      setSavedMessage("Changes saved. New preflight jobs using this ruleset will pick them up.");
      onSaved?.();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-6 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{profile.name}</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">{profile.description}</p>
      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
        <div>
          <span className="font-medium">ID:</span>{" "}
          <code>{profile.profile_id}</code>
        </div>
        <div>
          <span className="font-medium">Workflow:</span> {profile.workflow}
        </div>
        <div>
          <span className="font-medium">Conformance:</span>{" "}
          {profile.conformance ?? "None"}
        </div>
      </div>
      {profile.thresholds &&
        Object.keys(profile.thresholds).length > 0 && (
          <div className="mt-3">
            <h3 className="text-sm font-semibold">Thresholds</h3>
            <div className="mt-1 grid gap-1 text-xs sm:grid-cols-3">
              {Object.entries(
                profile.thresholds as Record<string, unknown>,
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
      <div className="mt-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">Rules</h3>
          {!isBuiltIn && (
            <div className="flex items-center gap-2">
              {isDirty && (
                <span className="text-xs text-amber-500">Unsaved changes</span>
              )}
              <Button
                size="sm"
                variant="primary"
                disabled={!isDirty || saving}
                onClick={handleSave}
              >
                {saving ? "Saving…" : "Save changes"}
              </Button>
            </div>
          )}
        </div>
        {isBuiltIn && (
          <p className="mt-1 text-xs text-muted-foreground">
            Built-in rulesets are read-only. Use the Clone button on the
            list above to create an editable copy.
          </p>
        )}
        {saveError && (
          <p className="mt-2 text-xs text-red-500">{saveError}</p>
        )}
        {savedMessage && (
          <p className="mt-2 text-xs text-emerald-500">{savedMessage}</p>
        )}
        <RulesEditor
          profile={edited}
          baseline={baseline}
          onChange={setEdited}
          readOnly={isBuiltIn}
        />
      </div>
    </div>
  );
}

function CreateForm(props: {
  editingOwner: OwnerKey;
  newProfileId: string;
  setNewProfileId: (v: string) => void;
  newName: string;
  setNewName: (v: string) => void;
  newDescription: string;
  setNewDescription: (v: string) => void;
  newWorkflow: string;
  setNewWorkflow: (v: string) => void;
  newConformance: string;
  setNewConformance: (v: string) => void;
  newThresholds: Record<string, number>;
  setNewThresholds: React.Dispatch<
    React.SetStateAction<{
      min_dpi: number;
      max_dpi: number;
      tac_limit: number;
      min_bleed_mm: number;
      hairline_threshold: number;
      small_text_threshold: number;
      safety_margin_mm: number;
    }>
  >;
  creating: boolean;
  onSave: () => void;
  onCancel: () => void;
  tenants: AdminTenantProfiles[];
}) {
  const {
    editingOwner,
    newProfileId,
    setNewProfileId,
    newName,
    setNewName,
    newDescription,
    setNewDescription,
    newWorkflow,
    setNewWorkflow,
    newConformance,
    setNewConformance,
    newThresholds,
    setNewThresholds,
    creating,
    onSave,
    onCancel,
    tenants,
  } = props;
  const tenantLabel =
    tenants.find((t) => t.tenant_id === editingOwner)?.tenant_name ??
    (editingOwner === "self" ? "Your tenant" : editingOwner);
  return (
    <div className="mt-6 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          New Ruleset{" "}
          <span className="text-sm font-normal text-muted-foreground">
            — {tenantLabel}
          </span>
        </h2>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <FormField
          label="Profile ID"
          htmlFor="profile-id"
          helpText="Lowercase kebab-case (e.g. my-magazine-ads)"
        >
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

      <h3 className="mt-4 text-sm font-semibold">Thresholds</h3>
      <div className="mt-2 grid gap-3 sm:grid-cols-3">
        {(
          [
            ["Min DPI", "min_dpi", "1"],
            ["Max DPI", "max_dpi", "1"],
            ["TAC Limit (%)", "tac_limit", "1"],
            ["Min Bleed (mm)", "min_bleed_mm", "0.5"],
            ["Hairline (pt)", "hairline_threshold", "0.05"],
            ["Small Text (pt)", "small_text_threshold", "0.5"],
          ] as const
        ).map(([label, key, step]) => (
          <FormField key={key} label={label} htmlFor={key}>
            <Input
              id={key}
              type="number"
              step={step}
              value={newThresholds[key]}
              onChange={(e) =>
                setNewThresholds((t) => ({
                  ...t,
                  [key]: Number(e.target.value),
                }))
              }
            />
          </FormField>
        ))}
      </div>

      <Button
        onClick={onSave}
        disabled={!newProfileId || !newName}
        loading={creating}
        className="mt-4"
      >
        Save Ruleset
      </Button>
    </div>
  );
}
