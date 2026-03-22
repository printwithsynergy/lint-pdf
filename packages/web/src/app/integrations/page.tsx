import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Integrations — LintPDF",
  description:
    "Connect LintPDF to prepress workflow engines, print ERP/MIS systems, and no-code automation platforms. API-first architecture for any workflow.",
};

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

interface Integration {
  title: string;
  description: string;
  href: string;
}

const prepressIntegrations: Integration[] = [
  {
    title: "Enfocus Switch",
    description:
      "Call LintPDF from any Switch flow using the HTTP Request element or Scripter.",
    href: "/docs/integrations-enfocus-switch",
  },
  {
    title: "Esko Automation Engine",
    description:
      "Preflight files using the Interact with Web Service task with full SmartName support.",
    href: "/docs/integrations-esko-ae",
  },
  {
    title: "Hybrid CLOUDFLOW",
    description:
      "Embed LintPDF in your CLOUDFLOW workflow via REST API or custom workflow node.",
    href: "/docs/integrations-hybrid-cloudflow",
  },
];

const erpIntegrations: Integration[] = [
  {
    title: "Label Traxx",
    description:
      "Direct API integration via Cloud API or indirect via Esko AE / CLOUDFLOW.",
    href: "/docs/integrations-label-traxx",
  },
  {
    title: "CERM",
    description:
      "JDF integration through Esko or Hybrid workflow engines.",
    href: "/docs/integrations-cerm",
  },
  {
    title: "EFI Pace",
    description:
      "API or JDF/Fiery workflow integration via PaceConnect.",
    href: "/docs/integrations-efi-pace",
  },
  {
    title: "Tharstern",
    description:
      "Integrate via Esko Automation Engine or direct web services.",
    href: "/docs/integrations-tharstern",
  },
  {
    title: "PrintVis",
    description:
      "Direct via Microsoft Dynamics 365 APIs and Power Automate — no code required.",
    href: "/docs/integrations-printvis",
  },
];

const genericIntegrations: Integration[] = [
  {
    title: "Zapier / Make / n8n",
    description:
      "Webhook-driven, no-code integration with any automation platform.",
    href: "/docs/integrations-zapier-make-n8n",
  },
  {
    title: "Hot Folder",
    description:
      "Drop files in a directory, get preflight results automatically.",
    href: "/docs/integrations-hot-folder",
  },
  {
    title: "REST API",
    description:
      "Any system that can make HTTP calls can integrate with LintPDF. One POST to submit, one GET for results.",
    href: "/docs/api-reference",
  },
];

/* ------------------------------------------------------------------ */
/*  Components                                                         */
/* ------------------------------------------------------------------ */

function IntegrationCard({ title, description, href }: Integration) {
  return (
    <Link
      href={href}
      className="group rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-1"
    >
      <h3 className="text-lg font-semibold text-slate-900 group-hover:text-brand-700 transition-colors">
        {title}
      </h3>
      <p className="mt-2 text-sm text-slate-500 leading-relaxed">
        {description}
      </p>
      <span className="mt-4 inline-block text-sm font-medium text-brand-600">
        View docs &rarr;
      </span>
    </Link>
  );
}

function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="text-center mb-12">
      <h2 className="text-2xl font-bold text-slate-900 md:text-3xl">
        {title}
      </h2>
      <p className="mt-3 text-slate-500 max-w-2xl mx-auto">{subtitle}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function IntegrationsPage() {
  return (
    <>
      {/* Hero */}
      <section className="bg-brand-50/50 pt-24 pb-16">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
            Connects to Your Workflow
          </h1>
          <p className="mt-4 text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed">
            LintPDF&apos;s API-first architecture slots into any prepress
            workflow — from no-code automation tools to enterprise workflow
            engines.
          </p>
        </div>
      </section>

      {/* Prepress Workflow Engines */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeader
            title="Prepress Workflow Engines"
            subtitle="LintPDF works as a preflight step inside your existing prepress automation."
          />
          <div className="grid gap-6 md:grid-cols-3">
            {prepressIntegrations.map((i) => (
              <IntegrationCard key={i.title} {...i} />
            ))}
          </div>
        </div>
      </section>

      {/* Print ERP / MIS */}
      <section className="bg-brand-50/50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeader
            title="Print ERP / MIS"
            subtitle="Bridge your management system and LintPDF — directly via API or through your workflow engine."
          />
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {erpIntegrations.map((i) => (
              <IntegrationCard key={i.title} {...i} />
            ))}
          </div>
        </div>
      </section>

      {/* No-code / Generic */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <SectionHeader
            title="Automation & Generic"
            subtitle="No-code tools, watched folders, and direct REST — pick what fits."
          />
          <div className="grid gap-6 md:grid-cols-3">
            {genericIntegrations.map((i) => (
              <IntegrationCard key={i.title} {...i} />
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-brand-50/50 py-20">
        <div className="mx-auto max-w-6xl px-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900 md:text-3xl">
            Ready to connect?
          </h2>
          <p className="mt-3 text-slate-500 max-w-xl mx-auto">
            Don&apos;t see your system? LintPDF&apos;s REST API works with
            anything that can make HTTP calls.
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/docs/integrations-overview"
              className="rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5"
            >
              View Integration Docs
            </Link>
            <Link
              href="/contact"
              className="rounded-xl border-2 border-slate-200 px-8 py-3.5 text-base font-medium text-slate-600 transition-all hover:border-brand-300 hover:text-brand-700 hover:bg-brand-50"
            >
              Talk to Us
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
