"use client";

import { useCallback, useEffect, useState } from "react";
import { EmptyState } from "@thinkneverland/pixie-dust-ui";
import { useToast } from "@thinkneverland/pixie-dust-ui";
import { ConfirmDialog } from "@thinkneverland/pixie-dust-ui";
import { Badge } from "@thinkneverland/pixie-dust-ui";
import { Button, Input, Select, FormField, ColorInput } from "@thinkneverland/pixie-dust-ui";

interface BrandProfile {
  id: string;
  name: string;
  profile_type: "custom" | "lintpdf" | "none";
  brand_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
  accent_color: string | null;
  footer_text: string | null;
  hide_footer: boolean;
  is_default: boolean;
  created_at: string;
}

const PROFILE_TYPE_LABELS: Record<string, string> = {
  custom: "Custom Branding",
  lintpdf: "LintPDF Default",
  none: "Blind (No Branding)",
};

const PROFILE_TYPE_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  custom: "default",
  lintpdf: "secondary",
  none: "outline",
};

export default function BrandingPage() {
  const [profiles, setProfiles] = useState<BrandProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form state
  const [formName, setFormName] = useState("");
  const [formType, setFormType] = useState<"custom" | "lintpdf" | "none">(
    "custom",
  );
  const [formBrandName, setFormBrandName] = useState("");
  const [formLogoUrl, setFormLogoUrl] = useState("");
  const [formPrimaryColor, setFormPrimaryColor] = useState("#1a3a7a");
  const [formAccentColor, setFormAccentColor] = useState("#2563eb");
  const [formFooterText, setFormFooterText] = useState("Powered by LintPDF");
  const [formHideFooter, setFormHideFooter] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Confirm dialog state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);

  const { toast } = useToast();

  const fetchProfiles = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/branding/profiles");
      if (!resp.ok) throw new Error("Failed to load brand profiles");
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

  function resetForm() {
    setFormName("");
    setFormType("custom");
    setFormBrandName("");
    setFormLogoUrl("");
    setFormPrimaryColor("#1a3a7a");
    setFormAccentColor("#2563eb");
    setFormFooterText("Powered by LintPDF");
    setFormHideFooter(false);
    setEditingId(null);
  }

  function editProfile(p: BrandProfile) {
    setFormName(p.name);
    setFormType(p.profile_type);
    setFormBrandName(p.brand_name ?? "");
    setFormLogoUrl(p.logo_url ?? "");
    setFormPrimaryColor(p.primary_color ?? "#1a3a7a");
    setFormAccentColor(p.accent_color ?? "#2563eb");
    setFormFooterText(p.footer_text ?? "");
    setFormHideFooter(p.hide_footer);
    setEditingId(p.id);
    setShowCreate(true);
  }

  async function handleSave() {
    setSaving(true);
    try {
      const body = {
        name: formName,
        profile_type: formType,
        brand_name: formBrandName || null,
        logo_url: formLogoUrl || null,
        primary_color: formPrimaryColor || null,
        accent_color: formAccentColor || null,
        footer_text: formFooterText || null,
        hide_footer: formHideFooter,
      };
      const url = editingId
        ? `/api/lintpdf/branding/profiles/${editingId}`
        : "/api/lintpdf/branding/profiles";
      const method = editingId ? "PUT" : "POST";
      const resp = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error("Failed to save profile");
      setShowCreate(false);
      resetForm();
      toast(editingId ? "Profile updated" : "Profile created", "success");
      await fetchProfiles();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to save", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      const resp = await fetch(`/api/lintpdf/branding/profiles/${id}`, {
        method: "DELETE",
      });
      if (!resp.ok) throw new Error("Failed to delete");
      toast("Brand profile deleted", "success");
      await fetchProfiles();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to delete", "error");
    }
  }

  async function handleSetDefault(id: string) {
    try {
      const resp = await fetch("/api/lintpdf/branding/default", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brand_profile_id: id }),
      });
      if (!resp.ok) throw new Error("Failed to set default");
      toast("Default profile updated", "success");
      await fetchProfiles();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to set default", "error");
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="animate-pulse text-muted-foreground">Loading...</span>
      </div>
    );
  }

  return (
    <main className="max-w-4xl p-8">
      <CustomReportDomainCard />
      <DefaultOutputBrandingCard
        profiles={profiles}
        onError={setError}
      />
      <div className="mt-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Brand Profiles</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Control how reports appear to your customers. Create custom branding,
            use LintPDF defaults, or go completely blind.
          </p>
        </div>
        <Button
          onClick={() => {
            if (showCreate) {
              setShowCreate(false);
              resetForm();
            } else {
              resetForm();
              setShowCreate(true);
            }
          }}
        >
          {showCreate ? "Cancel" : "New Profile"}
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

      {/* Create/Edit form */}
      {showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">
            {editingId ? "Edit Profile" : "New Brand Profile"}
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <FormField label="Profile Name" htmlFor="profile-name">
              <Input
                id="profile-name"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Client Reports"
              />
            </FormField>
            <FormField label="Profile Type" htmlFor="profile-type">
              <Select
                id="profile-type"
                value={formType}
                onChange={(e) =>
                  setFormType(
                    e.target.value as "custom" | "lintpdf" | "none",
                  )
                }
              >
                <option value="custom">Custom Branding</option>
                <option value="lintpdf">LintPDF Default</option>
                <option value="none">Blind (No Branding)</option>
              </Select>
            </FormField>
          </div>

          {formType === "custom" && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <FormField label="Brand Name" htmlFor="brand-name">
                <Input
                  id="brand-name"
                  value={formBrandName}
                  onChange={(e) => setFormBrandName(e.target.value)}
                  placeholder="Your Company Name"
                />
              </FormField>
              <FormField label="Logo URL" htmlFor="logo-url">
                <Input
                  id="logo-url"
                  type="url"
                  value={formLogoUrl}
                  onChange={(e) => setFormLogoUrl(e.target.value)}
                  placeholder="https://..."
                />
              </FormField>
              <FormField label="Primary Color" htmlFor="primary-color">
                <ColorInput
                  value={formPrimaryColor}
                  onChange={setFormPrimaryColor}
                />
              </FormField>
              <FormField label="Accent Color" htmlFor="accent-color">
                <ColorInput
                  value={formAccentColor}
                  onChange={setFormAccentColor}
                />
              </FormField>
              <div className="sm:col-span-2">
                <FormField label="Footer Text" htmlFor="footer-text">
                  <Input
                    id="footer-text"
                    value={formFooterText}
                    onChange={(e) => setFormFooterText(e.target.value)}
                    placeholder="Powered by Your Company"
                  />
                </FormField>
              </div>
              <div className="sm:col-span-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formHideFooter}
                    onChange={(e) => setFormHideFooter(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Hide footer completely
                </label>
              </div>
            </div>
          )}

          <Button
            onClick={handleSave}
            disabled={!formName}
            loading={saving}
            className="mt-4"
          >
            {editingId ? "Update Profile" : "Create Profile"}
          </Button>
        </div>
      )}

      {/* Profiles list */}
      <div className="mt-6 space-y-3">
        {profiles.length === 0 && (
          <EmptyState
            icon="Palette"
            title="No brand profiles yet"
            description="Create one to customize your report appearance."
            action={
              <Button
                onClick={() => {
                  resetForm();
                  setShowCreate(true);
                }}
              >
                New Profile
              </Button>
            }
          />
        )}
        {profiles.map((p) => (
          <div
            key={p.id}
            className={`flex items-center justify-between rounded-lg border p-4 ${
              p.is_default ? "border-primary bg-primary/5" : ""
            }`}
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{p.name}</span>
                <Badge variant={PROFILE_TYPE_VARIANT[p.profile_type] ?? "outline"}>
                  {PROFILE_TYPE_LABELS[p.profile_type]}
                </Badge>
                {p.is_default && (
                  <Badge variant="success">Default</Badge>
                )}
              </div>
              {p.profile_type === "custom" && p.brand_name && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {p.brand_name}
                  {p.primary_color && (
                    <span
                      className="ml-2 inline-block h-3 w-3 rounded-full border"
                      style={{ backgroundColor: p.primary_color }}
                    />
                  )}
                </p>
              )}
            </div>
            <div className="ml-4 flex shrink-0 gap-1">
              {!p.is_default && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleSetDefault(p.id)}
                >
                  Set Default
                </Button>
              )}
              <Button
                variant="secondary"
                size="sm"
                onClick={() => editProfile(p)}
              >
                Edit
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  setConfirmTarget(p.id);
                  setConfirmOpen(true);
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        ))}
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
        title="Delete brand profile?"
        description="This action cannot be undone. Reports using this profile will fall back to the default."
        variant="destructive"
        confirmLabel="Delete"
      />
    </main>
  );
}


// ----------------------------------------------------------------------
// White-label custom report domain card (self-service)
// ----------------------------------------------------------------------

interface CustomDomainState {
  tenant_id: string;
  domain: string | null;
  verified: boolean;
  requested_at: string | null;
  plan_allows_whitelabel: boolean;
  dns_target: string;
}

function CustomReportDomainCard() {
  const { toast } = useToast();
  const [state, setState] = useState<CustomDomainState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formDomain, setFormDomain] = useState("");
  const [editMode, setEditMode] = useState(false);

  const fetchState = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/branding/custom-domain");
      if (!resp.ok) {
        if (resp.status === 403) {
          // Plan doesn't allow — still show the upsell card.
          // ``dns_target`` fallback points at the Caddy edge
          // (``edge.lintpdf.com``) which is where BYO customers CNAME
          // to. Used only in the locked-out preview; real tenants on
          // Scale/Enterprise get the live value from the API.
          setState({
            tenant_id: "",
            domain: null,
            verified: false,
            requested_at: null,
            plan_allows_whitelabel: false,
            dns_target: "edge.lintpdf.com",
          });
        }
        return;
      }
      const data = (await resp.json()) as CustomDomainState;
      setState(data);
      setFormDomain(data.domain ?? "");
    } catch {
      // ignore — card just stays empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchState();
  }, [fetchState]);

  async function handleSave() {
    setSaving(true);
    try {
      const resp = await fetch("/api/lintpdf/branding/custom-domain", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: formDomain.trim() || null }),
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => ({}))) as {
          error?: string;
          detail?: string;
        };
        throw new Error(err.detail ?? err.error ?? "Failed to save");
      }
      toast("Custom domain saved", "success");
      setEditMode(false);
      await fetchState();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to save", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleClear() {
    setSaving(true);
    try {
      const resp = await fetch("/api/lintpdf/branding/custom-domain", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: null }),
      });
      if (!resp.ok) throw new Error("Failed to remove domain");
      toast("Custom domain removed", "success");
      setFormDomain("");
      setEditMode(false);
      await fetchState();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed to remove", "error");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return null;
  }
  if (!state) return null;

  // Gate: plan doesn't include white-label
  if (!state.plan_allows_whitelabel) {
    return (
      <div className="rounded-lg border bg-muted/30 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">White-Label Custom Report Domain</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Host your reports at your own domain (e.g. <code>reports.yourcompany.com</code>) so
              clients never see a LintPDF URL. Available on Scale and Enterprise plans.
            </p>
          </div>
          <Badge variant="outline">Upgrade required</Badge>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">White-Label Custom Report Domain</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Serve hosted reports at your own subdomain. All <code>/r/&lt;token&gt;</code> links
            returned by the API will use this host after verification.
          </p>
        </div>
        {state.domain && state.verified && <Badge variant="success">Active</Badge>}
        {state.domain && !state.verified && <Badge variant="outline">Pending</Badge>}
        {!state.domain && <Badge variant="secondary">Not set</Badge>}
      </div>

      {/* Read mode */}
      {!editMode && (
        <div className="mt-4 space-y-3">
          {state.domain ? (
            <div className="rounded-md bg-muted/40 p-3 font-mono text-sm">
              https://{state.domain}/r/&lt;token&gt;
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No custom domain configured.</p>
          )}

          {state.domain && !state.verified && (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/30 dark:text-amber-100">
              <p className="font-semibold">Next step: one DNS record</p>
              <ol className="ml-5 mt-2 list-decimal space-y-1">
                <li>
                  In your DNS provider, add this CNAME:
                  <div className="mt-1 rounded bg-amber-100/60 p-2 font-mono text-xs dark:bg-amber-900/30">
                    {state.domain} &nbsp;CNAME&nbsp; {state.dns_target}
                  </div>
                </li>
                <li>
                  That&apos;s it. LintPDF&apos;s edge handles TLS, certificate renewal, and
                  path-routing to the right backend automatically. No ACME TXT records,
                  no cert installation on your side.
                </li>
                <li>
                  Your first HTTPS request to <code>{state.domain}</code> will take
                  ~5&ndash;30 seconds while we issue a Let&apos;s Encrypt certificate.
                  Every request after that is instant.
                </li>
              </ol>
              <p className="mt-3">
                Reports keep using the default LintPDF URL until your DNS propagates
                (usually 1&ndash;5 minutes). You&apos;ll see <code>verified: true</code> here
                once the first request has succeeded.
              </p>
            </div>
          )}

          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setEditMode(true)}>
              {state.domain ? "Change domain" : "Set custom domain"}
            </Button>
            {state.domain && (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleClear}
                disabled={saving}
              >
                Remove
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Edit mode */}
      {editMode && (
        <div className="mt-4 space-y-3">
          <FormField label="Custom domain">
            <Input
              placeholder="reports.yourcompany.com"
              value={formDomain}
              onChange={(e) => setFormDomain(e.target.value)}
              disabled={saving}
            />
          </FormField>
          <p className="text-xs text-muted-foreground">
            Enter a bare hostname — no scheme, no path, no port. Setting a new value resets
            verification and requires DNS to be re-pointed.
          </p>
          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={saving || !formDomain.trim()}>
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setEditMode(false);
                setFormDomain(state.domain ?? "");
              }}
              disabled={saving}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}


// ----------------------------------------------------------------------
// Default output branding card — controls the tenant-wide default
// (anonymous / specific profile / LintPDF). Brokers flip this to
// "Anonymous" when they routinely forward reports to distributors who
// shouldn't know which broker ran the preflight.
// ----------------------------------------------------------------------

interface BrandingDefaults {
  mode: "anonymous" | "profile" | "lintpdf";
  unbranded_by_default: boolean;
  default_brand_profile_id: string | null;
}

function DefaultOutputBrandingCard({
  profiles,
  onError,
}: {
  profiles: BrandProfile[];
  onError: (msg: string) => void;
}) {
  const { toast } = useToast();
  const [defaults, setDefaults] = useState<BrandingDefaults | null>(null);
  const [saving, setSaving] = useState(false);
  const [pendingMode, setPendingMode] = useState<BrandingDefaults["mode"]>(
    "lintpdf",
  );
  const [pendingProfileId, setPendingProfileId] = useState<string>("");

  const fetchDefaults = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/branding/defaults");
      if (!resp.ok) return;
      const data = (await resp.json()) as BrandingDefaults;
      setDefaults(data);
      setPendingMode(data.mode);
      setPendingProfileId(data.default_brand_profile_id ?? "");
    } catch {
      // silent — card just stays hidden
    }
  }, []);

  useEffect(() => {
    void fetchDefaults();
  }, [fetchDefaults]);

  async function save() {
    setSaving(true);
    try {
      const body: { mode: string; brand_profile_id?: string } = {
        mode: pendingMode,
      };
      if (pendingMode === "profile") {
        if (!pendingProfileId) {
          throw new Error("Choose a brand profile to use as the default.");
        }
        body.brand_profile_id = pendingProfileId;
      }
      const resp = await fetch("/api/lintpdf/branding/defaults", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = (await resp.json().catch(() => ({}))) as {
          detail?: string;
          error?: string;
        };
        throw new Error(err.detail ?? err.error ?? "Failed to save");
      }
      const data = (await resp.json()) as BrandingDefaults;
      setDefaults(data);
      toast("Default output branding updated", "success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to save";
      onError(msg);
      toast(msg, "error");
    } finally {
      setSaving(false);
    }
  }

  if (!defaults) return null;

  const customProfiles = profiles.filter((p) => p.profile_type === "custom");

  return (
    <div className="mt-6 rounded-lg border p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Default Output Branding</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            What brand appears on reports, viewer chrome, and share links by
            default? Per-job overrides are always available at submit time.
          </p>
        </div>
        {defaults.mode === "anonymous" && (
          <Badge variant="outline">Anonymous</Badge>
        )}
        {defaults.mode === "profile" && <Badge>Branded</Badge>}
        {defaults.mode === "lintpdf" && (
          <Badge variant="secondary">LintPDF default</Badge>
        )}
      </div>

      <div className="mt-4 space-y-3">
        <label className="flex gap-3">
          <input
            type="radio"
            name="branding-default"
            className="mt-1"
            checked={pendingMode === "profile"}
            onChange={() => setPendingMode("profile")}
          />
          <div className="flex-1">
            <div className="text-sm font-medium">Branded (specific profile)</div>
            <p className="text-xs text-muted-foreground">
              Use one of your configured brand profiles.
            </p>
            {pendingMode === "profile" && (
              <div className="mt-2">
                <Select
                  value={pendingProfileId}
                  onChange={(e) => setPendingProfileId(e.target.value)}
                  disabled={customProfiles.length === 0}
                >
                  <option value="">Choose a brand profile…</option>
                  {customProfiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </Select>
                {customProfiles.length === 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Create a custom brand profile below to enable this option.
                  </p>
                )}
              </div>
            )}
          </div>
        </label>

        <label className="flex gap-3">
          <input
            type="radio"
            name="branding-default"
            className="mt-1"
            checked={pendingMode === "anonymous"}
            onChange={() => setPendingMode("anonymous")}
          />
          <div>
            <div className="text-sm font-medium">Anonymous (recommended for brokers)</div>
            <p className="text-xs text-muted-foreground">
              Strips your brand, LintPDF&apos;s brand, and identifying PDF
              metadata from every output. Use when forwarding reports to
              distributors who shouldn&apos;t know you generated them.
            </p>
          </div>
        </label>

        <label className="flex gap-3">
          <input
            type="radio"
            name="branding-default"
            className="mt-1"
            checked={pendingMode === "lintpdf"}
            onChange={() => setPendingMode("lintpdf")}
          />
          <div>
            <div className="text-sm font-medium">LintPDF default</div>
            <p className="text-xs text-muted-foreground">
              Use LintPDF&apos;s own branding on reports and the viewer.
            </p>
          </div>
        </label>
      </div>

      <div className="mt-4 flex gap-2">
        <Button onClick={save} disabled={saving}>
          {saving ? "Saving..." : "Save default"}
        </Button>
      </div>
    </div>
  );
}
