"use client";

/**
 * Substrate ICC profile upload page.
 *
 * Single-active-slot per tenant. Drives the EPM-A1 substrate-aware
 * gamut path — when a profile is set, the orchestrator routes
 * through is_in_gamut_for_profile instead of the saturated-CMYK
 * heuristic. Without a profile the heuristic runs (conservative;
 * under-fires rather than false-positives).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Button, useToast } from "@thinkneverland/pixie-dust-ui";
import { SkeletonDashboard } from "@/components/skeleton";

interface IccProfileMeta {
  storage_key: string;
  size_bytes: number;
  uploaded_at: string;
  description: string | null;
}

export default function IccProfilePage() {
  const { toast } = useToast();
  const [profile, setProfile] = useState<IccProfileMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const resp = await fetch("/api/lintpdf/icc-profiles/active");
      if (!resp.ok) {
        throw new Error(`Failed to load (${resp.status})`);
      }
      const data = await resp.json();
      setProfile(data);
    } catch (e) {
      toast(
        `Couldn't load profile: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleUpload(file: File) {
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch("/api/lintpdf/icc-profiles/active", {
        method: "POST",
        body: form,
      });
      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(detail || `Upload failed (${resp.status})`);
      }
      toast("ICC profile uploaded — EPM-A1 will use it on the next preflight.", "success");
      await refresh();
    } catch (e) {
      toast(
        `Upload failed: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete() {
    if (!window.confirm("Clear the active substrate ICC profile?")) return;
    setDeleting(true);
    try {
      const resp = await fetch("/api/lintpdf/icc-profiles/active", {
        method: "DELETE",
      });
      if (!resp.ok && resp.status !== 204) {
        const detail = await resp.text();
        throw new Error(detail || `Delete failed (${resp.status})`);
      }
      toast(
        "Profile cleared — EPM-A1 falls back to the default heuristic.",
        "success",
      );
      setProfile(null);
    } catch (e) {
      toast(
        `Delete failed: ${e instanceof Error ? e.message : String(e)}`,
        "error",
      );
    } finally {
      setDeleting(false);
    }
  }

  if (loading) return <SkeletonDashboard type="cards" />;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-2xl font-bold">Substrate ICC profile</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a substrate-specific ICC output profile (.icc / .icm). The
          EPM-A1 gamut detector routes through{" "}
          <code>is_in_gamut_for_profile</code> when a profile is set,
          giving press-accurate out-of-gamut detection. Without a profile,
          the engine falls back to a conservative saturated-CMYK heuristic.
        </p>
      </header>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Active profile
        </h2>
        {profile ? (
          <div className="space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Field label="Description" value={profile.description ?? "—"} />
              <Field
                label="Size"
                value={`${(profile.size_bytes / 1024).toFixed(1)} KB`}
              />
              <Field
                label="Uploaded"
                value={new Date(profile.uploaded_at).toLocaleString()}
              />
              <Field
                label="Storage key"
                value={
                  <code className="text-xs">{profile.storage_key}</code>
                }
              />
            </div>
            <div className="pt-2">
              <Button
                variant="destructive"
                onClick={handleDelete}
                loading={deleting}
              >
                Clear profile
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No profile set. EPM-A1 uses the default heuristic.
          </p>
        )}
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Upload {profile ? "replacement" : "new"} profile
        </h2>
        <p className="mb-3 text-sm text-muted-foreground">
          Accept .icc / .icm files up to 16 MB. The first 36 bytes must
          carry the ICC <code>acsp</code> magic — otherwise the upload is
          rejected.
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".icc,.icm,application/vnd.iccprofile"
          disabled={uploading}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleUpload(f);
          }}
          className="block w-full text-sm"
        />
        {uploading && (
          <p className="mt-2 text-xs text-muted-foreground">Uploading…</p>
        )}
      </section>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 text-sm text-foreground">{value}</p>
    </div>
  );
}
