"use client";

import Link from "next/link";

export default function AdminPage() {
  return (
    <>
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
          href="/dashboard/admin/audit"
          className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
        >
          <h2 className="text-lg font-semibold">Preflight Audit</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Full end-to-end visibility into every tenant&rsquo;s preflight
            inputs, outputs, and share links.
          </p>
        </Link>
        <Link
          href="/dashboard/admin/trials"
          className="rounded-lg border border-brand-200 bg-brand-50/30 p-4 hover:bg-brand-50/60 transition-colors"
        >
          <h2 className="text-lg font-semibold">Trial Submissions</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Review prospect uploads, run preflights, and send reports.
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
        <Link
          href="/dashboard/rulesets"
          className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
        >
          <h2 className="text-lg font-semibold">Rulesets</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Inspect and manage preflight rulesets across every tenant,
            grouped by tenant. Built-in rulesets are read-only templates.
          </p>
        </Link>
        <Link
          href="/dashboard/admin/webhooks"
          className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
        >
          <h2 className="text-lg font-semibold">Webhook Dead Letters</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Review deliveries whose retries have been exhausted and replay
            them against the current endpoint.
          </p>
        </Link>
        <Link
          href="/dashboard/admin/docs"
          className="rounded-lg border border-brand-200 bg-brand-50/30 p-4 hover:bg-brand-50/60 transition-colors"
        >
          <h2 className="text-lg font-semibold">Admin Documentation</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Guides for every admin panel, the admin API surface, and ops
            runbooks. Super-admin only.
          </p>
        </Link>
      </div>
    </>
  );
}
