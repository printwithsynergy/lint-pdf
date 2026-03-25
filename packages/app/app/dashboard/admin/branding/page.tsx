"use client";

import { useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface AppSettings {
  brandName: string;
  brandLogoUrl: string;
  brandTagline: string;
  customCss: string;
}

export default function BrandingPage() {
  const [settings, setSettings] = useState<AppSettings>({
    brandName: "",
    brandLogoUrl: "",
    brandTagline: "",
    customCss: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/lintpdf/admin/branding")
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load branding settings");
        return r.json();
      })
      .then((data) => setSettings(data))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load settings"),
      )
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const resp = await fetch("/api/lintpdf/admin/branding", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error((data as { error?: string }).error ?? "Failed to save");
      }
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <SkeletonDashboard type="detail" />;

  return (
    <main className="p-8 max-w-2xl">
      <h1 className="font-display text-2xl font-bold">Branding</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Customize the platform branding visible to all users.
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="mt-6 rounded-lg border bg-card p-4 space-y-4">
        <div>
          <label
            htmlFor="brandName"
            className="block text-sm font-medium text-muted-foreground"
          >
            Brand Name
          </label>
          <input
            id="brandName"
            type="text"
            value={settings.brandName}
            onChange={(e) =>
              setSettings({ ...settings, brandName: e.target.value })
            }
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label
            htmlFor="brandLogoUrl"
            className="block text-sm font-medium text-muted-foreground"
          >
            Logo URL
          </label>
          <input
            id="brandLogoUrl"
            type="text"
            value={settings.brandLogoUrl}
            onChange={(e) =>
              setSettings({ ...settings, brandLogoUrl: e.target.value })
            }
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            placeholder="/logo.svg"
          />
        </div>
        <div>
          <label
            htmlFor="brandTagline"
            className="block text-sm font-medium text-muted-foreground"
          >
            Tagline
          </label>
          <input
            id="brandTagline"
            type="text"
            value={settings.brandTagline}
            onChange={(e) =>
              setSettings({ ...settings, brandTagline: e.target.value })
            }
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Branding"}
          </button>
          {saved && (
            <span className="text-sm text-green-600">Saved successfully</span>
          )}
        </div>
      </div>
    </main>
  );
}
