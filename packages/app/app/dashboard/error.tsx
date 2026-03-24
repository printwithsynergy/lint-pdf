"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <main className="p-8">
      <div className="mx-auto max-w-md rounded-lg border border-destructive/20 bg-destructive/5 p-8 text-center">
        <h2 className="font-display text-xl font-bold text-destructive">
          Dashboard Error
        </h2>
        <p className="mt-3 text-sm text-muted-foreground">
          Something went wrong loading this page. Your data is safe.
        </p>
        {error.digest && (
          <p className="mt-2 text-xs text-muted-foreground">
            Error ID: {error.digest}
          </p>
        )}
        <div className="mt-6 flex justify-center gap-3">
          <button
            onClick={reset}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Try Again
          </button>
          <Link
            href="/dashboard"
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
          >
            Back to Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
