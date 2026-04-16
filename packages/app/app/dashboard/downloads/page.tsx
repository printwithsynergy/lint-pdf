"use client";

import { useCallback, useEffect, useState } from "react";
import { SkeletonDashboard } from "@/components/skeleton";
import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@thinkneverland/pixie-dust-ui";

interface PlatformArtifact {
  filename: string;
  size: number;
  sha256: string;
  key: string;
  download_url: string | null;
}

interface DesktopManifest {
  version: string;
  released_at: string | null;
  notes_url: string | null;
  platforms: Record<string, PlatformArtifact>;
}

interface DownloadsResponse {
  entitled: boolean;
  noRelease?: boolean;
  manifest: DesktopManifest | null;
}

const PLATFORM_LABELS: Record<string, string> = {
  macos: "macOS (Universal)",
  windows: "Windows (x64)",
  linux_appimage: "Linux (AppImage)",
  linux_deb: "Linux (.deb)",
};

const PLATFORM_ORDER = ["macos", "windows", "linux_appimage", "linux_deb"];

function humanSize(bytes: number): string {
  if (!bytes) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  // `unit` is a bounded numeric index into a fixed-length array we own.
  // eslint-disable-next-line security/detect-object-injection
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`;
}

export default function DownloadsPage() {
  const [data, setData] = useState<DownloadsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetch("/api/lintpdf/downloads/desktop", {
        cache: "no-store",
      });
      if (!resp.ok) {
        setError(`Failed to load downloads (${resp.status})`);
        return;
      }
      const json = (await resp.json()) as DownloadsResponse;
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load downloads");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (loading) {
    return <SkeletonDashboard />;
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!data || !data.entitled) {
    return (
      <div>
        <h1 className="font-display text-2xl font-bold">Desktop App</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Native Hot Folders clients for macOS, Windows, and Linux.
        </p>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Desktop add-on not enabled</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Access to the LintPDF Hot Folders desktop app is a paid add-on.
              Once your account is enabled by the LintPDF team, download links
              will appear on this page.
            </p>
            <Button
              onClick={() => {
                window.location.href =
                  "mailto:sales@lintpdf.com?subject=Desktop%20App%20Access";
              }}
            >
              Contact sales
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (data.noRelease || !data.manifest) {
    return (
      <div>
        <h1 className="font-display text-2xl font-bold">Desktop App</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Native Hot Folders clients for macOS, Windows, and Linux.
        </p>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>No release available yet</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Your account has the desktop add-on enabled, but no release has
              been published yet. Please check back shortly.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const manifest = data.manifest;
  const orderedPlatforms = PLATFORM_ORDER.filter(
    (name) => manifest.platforms[name as keyof typeof manifest.platforms],
  );
  const extras = Object.keys(manifest.platforms).filter(
    (name) => !PLATFORM_ORDER.includes(name),
  );

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">Desktop App</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            LintPDF Hot Folders {manifest.version}
            {manifest.released_at
              ? ` — released ${new Date(manifest.released_at).toLocaleDateString()}`
              : ""}
          </p>
        </div>
        <Badge variant="secondary">v{manifest.version}</Badge>
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        Download links are signed and expire in 15 minutes. Click the button
        again for a fresh link.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {[...orderedPlatforms, ...extras].map((name) => {
          // `name` is a trusted key from our manifest — already validated by
          // `PLATFORM_ORDER` / `extras` filters above, so it is safe to index.
          // eslint-disable-next-line security/detect-object-injection
          const p = manifest.platforms[name];
          if (!p) return null;
          return (
            <Card key={name}>
              <CardHeader>
                <CardTitle>{PLATFORM_LABELS[name] ?? name}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="text-sm text-muted-foreground">
                  <div>{p.filename}</div>
                  <div>
                    {humanSize(p.size)}
                    {p.sha256 ? (
                      <span className="ml-2 font-mono text-xs">
                        sha256: {p.sha256.slice(0, 12)}…
                      </span>
                    ) : null}
                  </div>
                </div>
                <Button
                  disabled={!p.download_url}
                  onClick={() => {
                    if (!p.download_url) return;
                    // Forces a fresh link each click — the parent state is
                    // re-fetched below to avoid stale presigned URLs.
                    window.location.href = p.download_url;
                    // Kick a silent refresh so the next click gets a new URL.
                    void refresh();
                  }}
                >
                  Download
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {manifest.notes_url ? (
        <p className="mt-6 text-sm text-muted-foreground">
          <a
            href={manifest.notes_url}
            target="_blank"
            rel="noreferrer noopener"
            className="underline"
          >
            Release notes
          </a>
        </p>
      ) : null}
    </div>
  );
}
