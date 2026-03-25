"use client";

import { useCallback, useEffect, useState } from "react";

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
    setError("");
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
      await fetchProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this brand profile?")) return;
    try {
      const resp = await fetch(`/api/lintpdf/branding/profiles/${id}`, {
        method: "DELETE",
      });
      if (!resp.ok) throw new Error("Failed to delete");
      await fetchProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete");
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
      await fetchProfiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to set default");
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
        <button
          onClick={() => {
            if (showCreate) {
              setShowCreate(false);
              resetForm();
            } else {
              resetForm();
              setShowCreate(true);
            }
          }}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {showCreate ? "Cancel" : "New Profile"}
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

      {/* Create/Edit form */}
      {showCreate && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">
            {editingId ? "Edit Profile" : "New Brand Profile"}
          </h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium">Profile Name</label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Client Reports"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">Profile Type</label>
              <select
                value={formType}
                onChange={(e) =>
                  setFormType(
                    e.target.value as "custom" | "lintpdf" | "none",
                  )
                }
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="custom">Custom Branding</option>
                <option value="lintpdf">LintPDF Default</option>
                <option value="none">Blind (No Branding)</option>
              </select>
            </div>
          </div>

          {formType === "custom" && (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium">Brand Name</label>
                <input
                  type="text"
                  value={formBrandName}
                  onChange={(e) => setFormBrandName(e.target.value)}
                  placeholder="Your Company Name"
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Logo URL</label>
                <input
                  type="url"
                  value={formLogoUrl}
                  onChange={(e) => setFormLogoUrl(e.target.value)}
                  placeholder="https://..."
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium">
                  Primary Color
                </label>
                <div className="mt-1 flex items-center gap-2">
                  <input
                    type="color"
                    value={formPrimaryColor}
                    onChange={(e) => setFormPrimaryColor(e.target.value)}
                    className="h-8 w-8 cursor-pointer rounded border"
                  />
                  <input
                    type="text"
                    value={formPrimaryColor}
                    onChange={(e) => setFormPrimaryColor(e.target.value)}
                    className="w-24 rounded-md border px-2 py-1 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium">
                  Accent Color
                </label>
                <div className="mt-1 flex items-center gap-2">
                  <input
                    type="color"
                    value={formAccentColor}
                    onChange={(e) => setFormAccentColor(e.target.value)}
                    className="h-8 w-8 cursor-pointer rounded border"
                  />
                  <input
                    type="text"
                    value={formAccentColor}
                    onChange={(e) => setFormAccentColor(e.target.value)}
                    className="w-24 rounded-md border px-2 py-1 text-sm"
                  />
                </div>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium">
                  Footer Text
                </label>
                <input
                  type="text"
                  value={formFooterText}
                  onChange={(e) => setFormFooterText(e.target.value)}
                  placeholder="Powered by Your Company"
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                />
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

          <button
            onClick={handleSave}
            disabled={saving || !formName}
            className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? "Saving..." : editingId ? "Update Profile" : "Create Profile"}
          </button>
        </div>
      )}

      {/* Profiles list */}
      <div className="mt-6 space-y-3">
        {profiles.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No brand profiles yet. Create one to customize your report
            appearance.
          </p>
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
                <span className="rounded bg-muted px-2 py-0.5 text-xs">
                  {PROFILE_TYPE_LABELS[p.profile_type]}
                </span>
                {p.is_default && (
                  <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    Default
                  </span>
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
                <button
                  onClick={() => handleSetDefault(p.id)}
                  className="rounded border px-2 py-1 text-xs hover:bg-muted"
                >
                  Set Default
                </button>
              )}
              <button
                onClick={() => editProfile(p)}
                className="rounded border px-2 py-1 text-xs hover:bg-muted"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(p.id)}
                className="rounded border border-destructive/30 px-2 py-1 text-xs text-destructive hover:bg-destructive/10"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
