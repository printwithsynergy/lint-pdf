"use client";

import Link from "next/link";

export default function AdminPage() {
  return (
    <main className="p-8 max-w-4xl">
      <h1 className="font-display text-2xl font-bold">Site Administration</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Platform management for super administrators.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Link
          href="/dashboard/admin/tenants"
          className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
        >
          <h2 className="text-lg font-semibold">All Tenants</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            View and manage all organizations, plans, and entitlements.
          </p>
        </Link>
        <Link
          href="/dashboard/admin/jobs"
          className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
        >
          <h2 className="text-lg font-semibold">All Jobs</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse preflight jobs across all tenants.
          </p>
        </Link>
        <Link
          href="/dashboard/admin/health"
          className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
        >
          <h2 className="text-lg font-semibold">System Health</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Check engine, database, Redis, and worker status.
          </p>
        </Link>
      </div>
    </main>
  );
}
