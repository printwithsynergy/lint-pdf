"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@thinkneverland/pixie-dust-ui";
import { PdfViewer } from "@/components/viewer";
import { hostFallbackClient } from "@/lib/host-fallback-client";

interface JobData {
  jobId: string;
  tenantId: string;
  fileName: string;
  emailRequired: boolean;
  brandName?: string;
  logoUrl?: string;
  /** True when the report was minted in anonymous mode — hide all chrome. */
  anonymous?: boolean;
}

function IdentifyScreen({
  onIdentify,
  loading,
}: {
  onIdentify: (email: string, name: string) => void;
  loading: boolean;
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) {
      setError("Email is required");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Please enter a valid email address");
      return;
    }
    setError("");
    onIdentify(email.trim(), name.trim());
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4 sm:p-6">
      {/* Outer padding keeps the card off the screen edges on mobile;
          inner padding stays roomy on tablet/desktop. */}
      <div className="w-full max-w-md rounded-xl border bg-background p-6 shadow-lg sm:p-8">
        <div className="mb-6 text-center">
          <h1 className="font-display text-2xl font-bold">
            Who&apos;s viewing?
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Enter your details to access this preflight report.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-sm font-medium"
            >
              Email <span className="text-destructive">*</span>
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
              autoFocus
              required
            />
          </div>

          <div>
            <label
              htmlFor="name"
              className="mb-1 block text-sm font-medium"
            >
              Name <span className="text-muted-foreground">(optional)</span>
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <Button
            type="submit"
            disabled={loading}
            loading={loading}
            className="w-full"
          >
            View Report
          </Button>
        </form>
      </div>
    </div>
  );
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  // name is a cookie name supplied by app code, not user input; escape regex metachars defensively.
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // eslint-disable-next-line security/detect-non-literal-regexp
  const match = document.cookie.match(new RegExp("(^| )" + escaped + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]!) : null;
}

function setCookie(name: string, value: string, days: number) {
  const expires = new Date(Date.now() + days * 86400000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires};path=/;SameSite=Lax`;
}

export default function PublicViewerPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const [jobData, setJobData] = useState<JobData | null>(null);
  const [identified, setIdentified] = useState(false);
  const [loading, setLoading] = useState(true);
  const [identifyLoading, setIdentifyLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchJobData = useCallback(async () => {
    // Distinguish between "bad URL / revoked", "expired", "auth needed"
    // and "transient network error" so the user sees a message that maps
    // to an actual next step. The previous single "Invalid or expired
    // link" string was a false positive on legitimate tokens whenever an
    // edge/middleware/caching layer briefly blipped — users couldn't tell
    // whether the link was really dead or just needed a reload.
    const doFetch = async (
      attempt: number,
    ): Promise<{ ok: true; data: JobData } | { ok: false; message: string }> => {
      try {
        const resp = await fetch(`/api/lintpdf/viewer/public/${token}/job`);
        if (resp.ok) {
          const data = (await resp.json()) as JobData;
          return { ok: true, data };
        }
        if (resp.status === 404) {
          return {
            ok: false,
            message: "This link does not exist or has been revoked.",
          };
        }
        if (resp.status === 410) {
          return { ok: false, message: "This link has expired." };
        }
        if (resp.status === 401 || resp.status === 403) {
          return {
            ok: false,
            message: "This link requires you to sign in.",
          };
        }
        if (resp.status >= 500 && attempt === 0) {
          // One retry after 1.5s for transient 5xx so a brief edge blip
          // doesn't force the user to reload manually.
          await new Promise((r) => setTimeout(r, 1500));
          return doFetch(attempt + 1);
        }
        return {
          ok: false,
          message: `Server error ${resp.status}. Try reloading in a moment.`,
        };
      } catch (e) {
        if (attempt === 0) {
          await new Promise((r) => setTimeout(r, 1500));
          return doFetch(attempt + 1);
        }
        return {
          ok: false,
          message:
            e instanceof Error
              ? `Network error: ${e.message}. Check your connection and reload.`
              : "Network error. Check your connection and reload.",
        };
      }
    };

    const result = await doFetch(0);
    if (!result.ok) {
      setError(result.message);
      setLoading(false);
      return;
    }
    const data = result.data;
    setJobData(data);

    // Check if we already have a saved email cookie
    const savedEmail = getCookie("lintpdf-viewer-email");
    if (!data.emailRequired || savedEmail) {
      setIdentified(true);
      // If we have a saved email, auto-identify
      if (savedEmail && data.emailRequired) {
        const savedName = getCookie("lintpdf-viewer-name") ?? "";
        // Fire and forget identify call to record the view
        fetch(`/api/lintpdf/viewer/public/${token}/identify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: savedEmail, name: savedName }),
        }).catch(() => {});
      }
    }
    setLoading(false);
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchJobData();
    }
  }, [token, fetchJobData]);

  async function handleIdentify(email: string, name: string) {
    setIdentifyLoading(true);
    try {
      const resp = await fetch(
        `/api/lintpdf/viewer/public/${token}/identify`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, name }),
        },
      );
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.error ?? "Identification failed");
      }
      // Save email in cookie so they don't have to re-enter
      setCookie("lintpdf-viewer-email", email, 30);
      if (name) {
        setCookie("lintpdf-viewer-name", name, 30);
      }
      setIdentified(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to identify");
    } finally {
      setIdentifyLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading report...</div>
      </div>
    );
  }

  if (error || !jobData) {
    // If we have a specific error message from the discriminated
    // fetcher (404/410/401/5xx/network), render that. If we somehow
    // reached here without an error AND without jobData, it's a
    // genuine empty-response case — rarer than the old codepath
    // implied, so word it plainly rather than guessing.
    const msg =
      error ||
      "The server didn't return report data. Try reloading in a moment.";
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="font-display text-xl font-bold text-destructive">
            Unable to load report
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">{msg}</p>
        </div>
      </div>
    );
  }

  // Show email gate if required and not yet identified
  if (jobData.emailRequired && !identified) {
    return (
      <IdentifyScreen
        onIdentify={handleIdentify}
        loading={identifyLoading}
      />
    );
  }

  // Anonymous share links hide all tenant + LintPDF chrome. The viewer
  // itself also honors `anonymous` from its config (see ViewerToolbar /
  // MobileDrawer), so all we need here is to suppress the header wrapper
  // and use neutral copy for anything the share page contributes.
  if (jobData.anonymous) {
    return (
      <div className="flex min-h-screen flex-col">
        <header className="flex h-10 items-center justify-between border-b bg-background px-4">
          <span className="text-sm font-medium text-muted-foreground">
            Preflight Report
          </span>
        </header>
        <main className="flex-1">
          <PdfViewer jobId={jobData.jobId} publicToken={token} />
        </main>
      </div>
    );
  }

  // Render minimal layout with viewer
  const brandFallback = hostFallbackClient();
  const isCustomDomain = brandFallback !== "LintPDF";
  const brandName = jobData.brandName || brandFallback;
  // On custom domains, suppress the default LintPDF logo entirely — only
  // show a logo if the tenant set their own. The hostname text still reads.
  const logoSrc = jobData.logoUrl || (isCustomDomain ? null : "/logo.svg");
  return (
    <div className="flex min-h-screen flex-col">
      {/* Top bar */}
      <header className="flex h-14 items-center justify-between border-b bg-background px-4">
        <div className="flex items-center gap-3">
          {logoSrc && (
            <img
              src={logoSrc}
              alt={brandName}
              className="h-7 w-auto"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
          <span className="font-display text-lg font-bold">{brandName}</span>
          <span className="hidden text-sm text-muted-foreground sm:inline">|</span>
          <span className="hidden text-sm text-muted-foreground truncate max-w-[300px] sm:inline">
            {jobData.fileName}
          </span>
        </div>
      </header>

      {/* Viewer */}
      <main className="flex-1">
        <PdfViewer jobId={jobData.jobId} publicToken={token} />
      </main>
    </div>
  );
}
