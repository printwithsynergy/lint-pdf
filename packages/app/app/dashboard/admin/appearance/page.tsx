"use client";

import { useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface AppearanceSettings {
  customCss: string;
  primaryColor: string;
  accentColor: string;
}

export default function AppearancePage() {
  const [settings, setSettings] = useState<AppearanceSettings>({
    customCss: "",
    primaryColor: "",
    accentColor: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/lintpdf/admin/appearance")
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load appearance settings");
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
      const resp = await fetch("/api/lintpdf/admin/appearance", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(
          (data as { error?: string }).error ?? "Failed to save",
        );
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
      <h1 className="font-display text-2xl font-bold">Appearance</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Customize colors and styling for the platform.
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="mt-6 rounded-lg border bg-card p-4 space-y-4">
        <div>
          <label
            htmlFor="primaryColor"
            className="block text-sm font-medium text-muted-foreground"
          >
            Primary Color
          </label>
          <div className="mt-1 flex items-center gap-2">
            <input
              id="primaryColor"
              type="color"
              value={settings.primaryColor || "#6366f1"}
              onChange={(e) =>
                setSettings({ ...settings, primaryColor: e.target.value })
              }
              className="h-10 w-10 cursor-pointer rounded border"
            />
            <input
              type="text"
              value={settings.primaryColor}
              onChange={(e) =>
                setSettings({ ...settings, primaryColor: e.target.value })
              }
              placeholder="#6366f1"
              className="flex-1 rounded-md border px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label
            htmlFor="accentColor"
            className="block text-sm font-medium text-muted-foreground"
          >
            Accent Color
          </label>
          <div className="mt-1 flex items-center gap-2">
            <input
              id="accentColor"
              type="color"
              value={settings.accentColor || "#8b5cf6"}
              onChange={(e) =>
                setSettings({ ...settings, accentColor: e.target.value })
              }
              className="h-10 w-10 cursor-pointer rounded border"
            />
            <input
              type="text"
              value={settings.accentColor}
              onChange={(e) =>
                setSettings({ ...settings, accentColor: e.target.value })
              }
              placeholder="#8b5cf6"
              className="flex-1 rounded-md border px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label
            htmlFor="customCss"
            className="block text-sm font-medium text-muted-foreground"
          >
            Custom CSS
          </label>
          <textarea
            id="customCss"
            value={settings.customCss}
            onChange={(e) =>
              setSettings({ ...settings, customCss: e.target.value })
            }
            rows={8}
            className="mt-1 w-full rounded-md border px-3 py-2 text-sm font-mono"
            placeholder="/* Add custom CSS overrides here */"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Appearance"}
          </button>
          {saved && (
            <span className="text-sm text-green-600">Saved successfully</span>
          )}
        </div>
      </div>
    </main>
  );
}
