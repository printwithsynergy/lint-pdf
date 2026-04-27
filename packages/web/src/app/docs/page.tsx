import type { Metadata } from "next";
import Link from "next/link";
import { docSections } from "@/lib/doc-sections";

export const metadata: Metadata = {
  title: "Documentation — LintPDF",
  description:
    "API reference, getting started guide, and full documentation for the LintPDF PDF preflight engine.",
};

/**
 * Task-oriented entry points for first-time visitors. These are
 * editorial, not mechanical — the order + wording matters more than
 * the groups do. Keep them punchy and action-oriented.
 */
const taskCards: { label: string; href: string; description: string }[] = [
  {
    label: "Run my first preflight",
    href: "/docs/getting-started",
    description:
      "Three steps: grab an API key, POST a PDF, get a branded report.",
  },
  {
    label: "Import a PitStop / Callas / Acrobat report",
    href: "/docs/external-imports",
    description:
      "Hand us your vendor's XML or JSON and get back a LintPDF-branded preflight.",
  },
  {
    label: "Brand my reports",
    href: "/docs/branding-and-anonymous",
    description:
      "White-label every report with your logo, colours, and custom domain.",
  },
  {
    label: "Automate with webhooks",
    href: "/docs/webhooks",
    description:
      "Real-time job-state events, HMAC-signed, with retry + dead-letter replay.",
  },
  {
    label: "Browse every dashboard panel",
    href: "/docs/panels",
    description:
      "What every screen in the LintPDF dashboard does, top to bottom.",
  },
];

export default function DocsPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-brand-50/60 to-white pb-24">
      <div className="mx-auto max-w-6xl px-6 pt-16 sm:pt-24">
        {/* ──────────────── Hero ──────────────── */}
        <section className="mb-12 sm:mb-16">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-brand-900">
            LintPDF docs
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-slate-600">
            Detection-only PDF preflight with 600+ checks, AI-powered brand +
            regulatory inspections, and a full viewer — all behind a single
            REST API. Start here for the two-minute walkthrough, or jump
            straight to a topic.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/docs/getting-started"
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
            >
              Start with a 2-minute preflight
              <ArrowRight />
            </Link>
            <Link
              href="/swagger"
              className="inline-flex items-center gap-2 rounded-lg border border-brand-200 bg-white px-5 py-3 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-50"
            >
              Try the API live (Swagger)
              <ArrowRight />
            </Link>
          </div>
        </section>

        {/* ──────────────── Task cards ──────────────── */}
        <section className="mb-16 sm:mb-20">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-500">
            I want to…
          </h2>
          <ul className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {taskCards.map((card) => (
              <li key={card.href}>
                <Link
                  href={card.href}
                  className="group block h-full rounded-xl border border-slate-200 bg-white p-5 transition-all hover:border-brand-300 hover:shadow-md"
                >
                  <span className="flex items-center gap-2 text-sm font-semibold text-slate-900 group-hover:text-brand-700">
                    {card.label}
                    <ArrowRight className="h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100" />
                  </span>
                  <span className="mt-2 block text-sm leading-relaxed text-slate-500">
                    {card.description}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        {/* ──────────────── Groups ──────────────── */}
        <section>
          <h2 className="mb-6 text-2xl font-bold tracking-tight text-slate-900">
            Browse by topic
          </h2>
          <ul className="grid gap-5 md:grid-cols-2">
            {docSections.map((section) => {
              const preview = section.items.slice(0, 4);
              return (
                <li
                  key={section.key}
                  className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                >
                  <h3 className="text-lg font-semibold text-slate-900">
                    {section.heading}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">{section.blurb}</p>
                  <ul className="mt-4 space-y-1.5 text-sm">
                    {preview.map((item) => (
                      <li key={item.slug}>
                        <Link
                          href={`/docs/${item.slug}`}
                          className="text-brand-700 hover:underline"
                        >
                          {item.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                  {section.items.length > preview.length ? (
                    <Link
                      href={`/docs/${section.key}`}
                      className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-brand-700"
                    >
                      Browse all {section.items.length} pages
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  ) : (
                    <Link
                      href={`/docs/${section.key}`}
                      className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-brand-700"
                    >
                      Open section
                      <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </section>

        {/* ──────────────── Footer strip ──────────────── */}
        <section className="mt-20 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
          <div className="grid gap-6 sm:grid-cols-3">
            <FooterLink
              title="Looking for a term?"
              label="Glossary →"
              href="/docs/glossary"
            />
            <FooterLink
              title="Calling the API directly?"
              label="Postman collection →"
              href="/docs/postman"
            />
            <FooterLink
              title="Something missing?"
              label="Contact us →"
              href="/contact"
            />
          </div>
        </section>
      </div>
    </main>
  );
}

function FooterLink({
  title,
  label,
  href,
}: {
  title: string;
  label: string;
  href: string;
}) {
  return (
    <div>
      <p className="text-sm text-slate-500">{title}</p>
      <Link
        href={href}
        className="mt-1 inline-block text-sm font-semibold text-brand-700 hover:underline"
      >
        {label}
      </Link>
    </div>
  );
}

function ArrowRight({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M13 7l5 5m0 0l-5 5m5-5H6"
      />
    </svg>
  );
}
