"use client";

import { useCallback, useEffect, useState } from "react";

interface AccountInfo {
  id: string;
  name: string;
  contact_email: string;
  plan: string;
  status: string;
  branding?: {
    name?: string;
    logo_url?: string;
    primary_color?: string;
    accent_color?: string;
    custom_domain?: string;
  };
  rate_limit_daily?: number;
  max_file_size_mb?: number;
  overage_enabled?: boolean;
  overage_cap_cents?: number;
}

export default function AccountPage() {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");

  // Editable fields
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");

  // Branding
  const [brandName, setBrandName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#000000");
  const [accentColor, setAccentColor] = useState("#0066FF");

  const fetchAccount = useCallback(async () => {
    try {
      const resp = await fetch("/api/grounded/account");
      if (!resp.ok) throw new Error("Failed to load account");
      const data = await resp.json();
      setAccount(data);
      setName(data.name ?? "");
      setContactEmail(data.contact_email ?? "");
      setBrandName(data.branding?.name ?? data.name ?? "");
      setLogoUrl(data.branding?.logo_url ?? "");
      setPrimaryColor(data.branding?.primary_color ?? "#000000");
      setAccentColor(data.branding?.accent_color ?? "#0066FF");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load account");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAccount();
  }, [fetchAccount]);

  async function handleSaveSettings() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const resp = await fetch("/api/grounded/account", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, contact_email: contactEmail }),
      });
      if (!resp.ok) throw new Error("Failed to update settings");
      setSuccess("Settings saved");
      await fetchAccount();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update settings");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveBranding() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const resp = await fetch("/api/grounded/account/branding", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: brandName,
          logo_url: logoUrl,
          primary_color: primaryColor,
          accent_color: accentColor,
        }),
      });
      if (!resp.ok) throw new Error("Failed to update branding");
      setSuccess("Branding saved");
      await fetchAccount();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update branding");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="p-8">
        <h1 className="font-display text-2xl font-bold">Account</h1>
        <p className="mt-4 text-muted-foreground">Loading...</p>
      </main>
    );
  }

  return (
    <main className="p-8 max-w-4xl">
      <h1 className="font-display text-2xl font-bold">Account Settings</h1>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}
      {success && (
        <div className="mt-4 rounded-md bg-green-50 p-3 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Plan overview */}
      {account && (
        <div className="mt-6 rounded-lg border p-4">
          <h2 className="text-lg font-semibold">Plan</h2>
          <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <span className="text-muted-foreground">Current Plan:</span>{" "}
              <span className="font-medium uppercase">{account.plan}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Status:</span>{" "}
              <span className="font-medium">{account.status}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Daily Limit:</span>{" "}
              <span className="font-medium">
                {account.rate_limit_daily?.toLocaleString() ?? "N/A"} jobs
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Max File Size:</span>{" "}
              <span className="font-medium">
                {account.max_file_size_mb ?? "N/A"} MB
              </span>
            </div>
            {account.overage_enabled && (
              <div>
                <span className="text-muted-foreground">Overage Cap:</span>{" "}
                <span className="font-medium">
                  ${((account.overage_cap_cents ?? 0) / 100).toFixed(2)}/day
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Organization settings */}
      <div className="mt-6 rounded-lg border p-4">
        <h2 className="text-lg font-semibold">Organization</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium">
              Organization Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Contact Email</label>
            <input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
        </div>
        <button
          onClick={handleSaveSettings}
          disabled={saving}
          className="mt-3 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>

      {/* Branding */}
      <div className="mt-6 rounded-lg border p-4">
        <h2 className="text-lg font-semibold">Branding</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Customize how your reports and portal appear to your customers.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium">Brand Name</label>
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Logo URL</label>
            <input
              type="url"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              placeholder="https://..."
              className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Primary Color</label>
            <div className="mt-1 flex gap-2">
              <input
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="h-9 w-12 rounded border"
              />
              <input
                type="text"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="flex-1 rounded-md border px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium">Accent Color</label>
            <div className="mt-1 flex gap-2">
              <input
                type="color"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                className="h-9 w-12 rounded border"
              />
              <input
                type="text"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                className="flex-1 rounded-md border px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
        <button
          onClick={handleSaveBranding}
          disabled={saving}
          className="mt-3 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Branding"}
        </button>
      </div>
    </main>
  );
}
