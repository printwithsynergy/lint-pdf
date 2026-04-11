"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { PdfViewer } from "@/components/viewer";

interface JobData {
  jobId: string;
  tenantId: string;
  fileName: string;
  emailRequired: boolean;
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
    <div className="flex min-h-screen items-center justify-center bg-muted/30">
      <div className="w-full max-w-md rounded-xl border bg-background p-8 shadow-lg">
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

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {loading ? "Verifying..." : "View Report"}
          </button>
        </form>
      </div>
    </div>
  );
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp("(^| )" + name + "=([^;]+)"),
  );
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
    try {
      const resp = await fetch(`/api/lintpdf/viewer/public/${token}/job`);
      if (!resp.ok) {
        throw new Error("Invalid or expired link");
      }
      const data: JobData = await resp.json();
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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
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
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="font-display text-xl font-bold text-destructive">
            Unable to load report
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {error || "This link may be invalid or expired."}
          </p>
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

  // Render minimal layout with viewer
  return (
    <div className="flex min-h-screen flex-col">
      {/* Top bar */}
      <header className="flex h-14 items-center justify-between border-b bg-background px-4">
        <div className="flex items-center gap-3">
          <span className="font-display text-lg font-bold">LintPDF</span>
          <span className="text-sm text-muted-foreground">|</span>
          <span className="text-sm text-muted-foreground truncate max-w-[300px]">
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
