"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import {
  Button,
  Input,
  FormField,
  ColorInput,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Alert,
  AlertDescription,
} from "@thinkneverland/pixie-dust-ui";

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
      const resp = await fetch("/api/lintpdf/account");
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
      const resp = await fetch("/api/lintpdf/account", {
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
      const resp = await fetch("/api/lintpdf/account/branding", {
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
    return <SkeletonDashboard type="form" />;
  }

  return (
    <main className="p-6">
      <h1 className="text-2xl font-bold">Account Settings</h1>

      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="mt-4">
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Plan overview */}
      {account && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 text-sm sm:grid-cols-3">
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
          </CardContent>
        </Card>
      )}

      {/* Organization settings */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Organization</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Organization Name" htmlFor="org-name">
              <Input
                id="org-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </FormField>
            <FormField label="Contact Email" htmlFor="contact-email">
              <Input
                id="contact-email"
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
            </FormField>
          </div>
          <Button
            onClick={handleSaveSettings}
            disabled={saving}
            loading={saving}
            className="mt-4"
          >
            Save Settings
          </Button>
        </CardContent>
      </Card>

      {/* Branding */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Branding</CardTitle>
          <CardDescription>
            Customize how your reports and portal appear to your customers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Brand Name" htmlFor="brand-name">
              <Input
                id="brand-name"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
              />
            </FormField>
            <FormField label="Logo URL" htmlFor="logo-url">
              <Input
                id="logo-url"
                type="url"
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
                placeholder="https://..."
              />
            </FormField>
            <FormField label="Primary Color" htmlFor="primary-color">
              <ColorInput
                value={primaryColor}
                onChange={setPrimaryColor}
              />
            </FormField>
            <FormField label="Accent Color" htmlFor="accent-color">
              <ColorInput
                value={accentColor}
                onChange={setAccentColor}
              />
            </FormField>
          </div>
          <Button
            onClick={handleSaveBranding}
            disabled={saving}
            loading={saving}
            className="mt-4"
          >
            Save Branding
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
