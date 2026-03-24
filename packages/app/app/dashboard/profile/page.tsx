"use client";

import { useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";

interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  avatarUrl: string | null;
  isSuperAdmin: boolean;
  tenants: { id: string; name: string; slug: string; role: string }[];
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/auth/me")
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load profile");
        return r.json();
      })
      .then((data) => {
        setProfile(data.user);
        setName(data.user.name ?? "");
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load profile"),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SkeletonDashboard type="detail" />;

  return (
    <main className="p-8 max-w-2xl">
      <h1 className="font-display text-2xl font-bold">Profile</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Manage your personal account settings.
      </p>

      {error && (
        <div className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {profile && (
        <div className="mt-6 space-y-6">
          <div className="rounded-lg border bg-card p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground">
                Email
              </label>
              <p className="mt-1 text-sm">{profile.email}</p>
            </div>
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-muted-foreground"
              >
                Display Name
              </label>
              <div className="mt-1 flex gap-2">
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setSaved(false);
                  }}
                  className="flex-1 rounded-md border px-3 py-2 text-sm"
                  placeholder="Your name"
                />
                <button
                  onClick={async () => {
                    setSaving(true);
                    try {
                      const resp = await fetch("/api/auth/me", {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ name }),
                      });
                      if (resp.ok) setSaved(true);
                    } catch {
                      setError("Failed to update name");
                    } finally {
                      setSaving(false);
                    }
                  }}
                  disabled={saving}
                  className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {saving ? "Saving..." : saved ? "Saved" : "Save"}
                </button>
              </div>
            </div>
            {profile.isSuperAdmin && (
              <div className="rounded bg-violet-50 px-3 py-2 text-sm text-violet-700">
                You are a Super Admin.
              </div>
            )}
          </div>

          {profile.tenants.length > 0 && (
            <div className="rounded-lg border bg-card p-4">
              <h2 className="text-sm font-semibold">Your Organizations</h2>
              <div className="mt-2 space-y-2">
                {profile.tenants.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span>{t.name}</span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                      {t.role}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
