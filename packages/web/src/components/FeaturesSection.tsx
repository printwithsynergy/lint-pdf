import Link from "next/link";

const features = [
  {
    title: "Detection-Only",
    description:
      "LintPDF finds problems — it never modifies your files. Your originals stay untouched, byte for byte. Zero risk of file damage, every time.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
        />
      </svg>
    ),
  },
  {
    title: "API-First",
    description:
      "One POST to Submit your file. One GET for the Report. JSON, XML, or a white-labeled PDF report with your logo. That's the entire integration.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
        />
      </svg>
    ),
  },
  {
    title: "600+ Checks",
    description:
      "259 rule-based checks plus 247 PDF/X-4 conformance checks plus 99 AI inspections — fonts, color spaces, images, transparency, overprint, page geometry, ink coverage, packaging geometry, barcode grading, PDF/X-1a, PDF/X-3, PDF/X-4, PDF/A. Every detail that matters for print production.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  {
    title: "Bring Your Own Preflight",
    description:
      "Already running PitStop, callas pdfToolbox, or Adobe Acrobat Preflight? Send the PDF plus the upstream XML/JSON report. LintPDF parses the findings, renders them in the viewer, and mints share links — no double-checking.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M7.5 7.5h-.75A2.25 2.25 0 004.5 9.75v7.5a2.25 2.25 0 002.25 2.25h7.5a2.25 2.25 0 002.25-2.25v-7.5a2.25 2.25 0 00-2.25-2.25h-.75m-6 3.75l3 3m0 0l3-3m-3 3V1.5m6 9h.75a2.25 2.25 0 012.25 2.25v7.5a2.25 2.25 0 01-2.25 2.25h-7.5a2.25 2.25 0 01-2.25-2.25v-.75"
        />
      </svg>
    ),
  },
  {
    title: "White Label + Anonymous Output",
    description:
      "Maintain one or more BrandProfiles per tenant — pick a default, override per job or share-link, or strip everything with anonymous mode. Anonymous mode sanitizes PDF metadata, uses a neutral filename, and renders zero LintPDF marks. Perfect for brokers handing reports to distributors.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42"
        />
      </svg>
    ),
  },
  {
    title: "Rulesets & Conditional Rules",
    description:
      "Pre-built profiles for GWG Sheetfed, GWG Digital, PDF/X-1a, PDF/X-3, PDF/X-4, PDF/A, and Packaging workflows. Conditional rule engine lets you build dynamic Rulesets with the exact logic you need.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
  },
  {
    title: "Webhooks",
    description:
      "Webhook callbacks fire when your file finishes processing. Get notified the instant a Report is ready — no polling, no waiting, no wasted cycles.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
        />
      </svg>
    ),
  },
  {
    title: "Non-PDF Input Support",
    description:
      "Submit EPS, PostScript, TIFF, JPEG, PNG, and PDF-compatible AI files. LintPDF converts them to PDF internally and runs the full Check suite.",
    icon: (
      <svg
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12H9.75m3 0h3m-3 0v3m0-3v-3m-9 3h.008v.008H3.75V15zm0 3h.008v.008H3.75V18zm0-6h.008v.008H3.75V12z"
        />
      </svg>
    ),
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="bg-brand-50/50 py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-slate-900 md:text-4xl mb-4">
            Everything you need for PDF preflight
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto">
            Built for web-to-print platforms, packaging houses, and publishing
            workflows that demand precision without compromise.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-1"
            >
              <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                {feature.icon}
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50/60 p-6 md:p-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-1">
                …and more
              </h3>
              <p className="text-sm text-slate-600">
                Self-service onboarding, priority queues, conditional rule
                engines, viewer annotations, AI inspections, and more ship
                across our plans.
              </p>
            </div>
            <Link
              href="/features"
              className="whitespace-nowrap rounded-xl bg-brand-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-800 shadow-md shadow-brand-200"
            >
              See all features →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
