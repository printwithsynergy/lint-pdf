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
      <div className="flex items-center justify-between">
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
