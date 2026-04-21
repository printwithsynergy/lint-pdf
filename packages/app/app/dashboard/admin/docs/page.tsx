import type { Metadata } from "next";
import Link from "next/link";
import { adminDocSections } from "@/lib/admin-doc-sections";

export const metadata: Metadata = {
  title: "Admin docs — LintPDF",
  description:
    "Super-admin documentation for panels, APIs, and ops runbooks.",
};

/**
 * Admin-docs landing page. Gated by `/dashboard/admin/layout.tsx` which
 * already enforces super-admin + valid session. Non-super-admin users
 * are redirected to `/dashboard` before this component ever renders.
 */
export default function AdminDocsHome() {
  return (
    <div className="max-w-5xl">
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold">Admin documentation</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Documentation for the super-admin surface: panels, APIs, and
          operator runbooks. Not linked from the marketing site — everything
          here is only reachable from the authenticated admin dashboard.
        </p>
      </header>

      <ul className="grid gap-4 md:grid-cols-2">
        {adminDocSections.map((section) => (
          <li
            key={section.key}
            className="rounded-xl border border-border bg-card p-5"
          >
            <h2 className="text-lg font-semibold">{section.heading}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {section.blurb}
            </p>
            <ul className="mt-3 space-y-1 text-sm">
              {section.items.slice(0, 5).map((item) => (
                <li key={item.slug}>
                  <Link
                    href={`/dashboard/admin/docs/${item.slug}`}
                    className="text-brand-700 hover:underline"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
            {section.items.length > 5 ? (
              <p className="mt-3 text-xs text-muted-foreground">
                + {section.items.length - 5} more below
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
