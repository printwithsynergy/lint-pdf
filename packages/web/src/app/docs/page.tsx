import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Documentation — LintPDF",
  description:
    "API reference, getting started guide, and full documentation for the LintPDF PDF preflight engine.",
};

const sections = [
  {
    heading: "Getting Started",
    items: [
      {
        slug: "getting-started",
        title: "Getting Started",
        desc: "Three steps to your first LintPDF report.",
      },
      {
        slug: "authentication",
        title: "Authentication",
        desc: "API key setup and Bearer token auth.",
      },
    ],
  },
  {
    heading: "API",
    items: [
      {
        slug: "api-reference",
        title: "API Reference",
        desc: "Complete REST API with request/response examples.",
      },
      {
        slug: "rulesets",
        title: "Rulesets",
        desc: "Built-in and custom preflight profiles.",
      },
      {
        slug: "checks",
        title: "Checks Reference",
        desc: "500+ checks across fonts, colors, images, barcodes, packaging, and more.",
      },
      {
        slug: "report-formats",
        title: "Report Formats",
        desc: "JSON, PDF, and XML output formats.",
      },
      {
        slug: "webhooks",
        title: "Webhooks",
        desc: "Real-time event notifications via HTTP callbacks.",
      },
      {
        slug: "sdks",
        title: "SDKs & Code Examples",
        desc: "Python, Node.js, and PHP examples.",
      },
      {
        slug: "glossary",
        title: "Glossary",
        desc: "LintPDF terminology reference.",
      },
    ],
  },
  {
    heading: "Color",
    items: [
      {
        slug: "color-management",
        title: "Color Management",
        desc: "ICC profiles, gamut checking, ink coverage.",
      },
      {
        slug: "color-quality-score",
        title: "Color Quality Score",
        desc: "The 0-100 color quality scoring system.",
      },
      {
        slug: "standards-compliance",
        title: "Standards Compliance",
        desc: "G7, GRACoL, and ISO 12647 readiness.",
      },
      {
        slug: "ecg-readiness",
        title: "ECG Readiness",
        desc: "CMYKOGV extended gamut preflight.",
      },
      {
        slug: "epm-readiness",
        title: "EPM Readiness",
        desc: "HP Indigo Enhanced Productivity Mode checks.",
      },
    ],
  },
  {
    heading: "AI Inspections",
    badge: "Alpha",
    items: [
      {
        slug: "ai-getting-started",
        title: "AI Getting Started",
        desc: "Enable and configure AI-powered preflight.",
      },
      {
        slug: "ai-setup",
        title: "AI Setup",
        desc: "Account setup and billing configuration.",
      },
      {
        slug: "ai-configuration",
        title: "AI Configuration",
        desc: "Categories, thresholds, and account settings.",
      },
      {
        slug: "ai-credits",
        title: "AI Credits",
        desc: "Credit system, packages, and top-ups.",
      },
      {
        slug: "ai-inspections",
        title: "AI Inspections Reference",
        desc: "All 32 inspections across 14 categories.",
      },
      {
        slug: "ai-presets",
        title: "AI Presets",
        desc: "Pre-built category bundles for common workflows.",
      },
      {
        slug: "ai-brand-config",
        title: "Brand Config",
        desc: "Brand palette, logos, and custom dictionaries.",
      },
      {
        slug: "ai-findings",
        title: "Reading Findings",
        desc: "Understanding AI findings in reports.",
      },
      {
        slug: "ai-regulatory",
        title: "Regulatory Compliance",
        desc: "FDA, EU FIR, GHS/CLP, pharmaceutical.",
      },
      {
        slug: "ai-monitoring",
        title: "Usage Monitoring",
        desc: "Credit consumption and quality metrics.",
      },
      {
        slug: "ai-voyage-plans",
        title: "AI in Rulesets",
        desc: "Using AI checks in presets and overrides.",
      },
      {
        slug: "ai-faq",
        title: "FAQ",
        desc: "Common questions about AI inspections.",
      },
      {
        slug: "ai-api",
        title: "AI API Reference",
        desc: "Endpoints for AI submissions and credits.",
      },
      {
        slug: "ai-errors",
        title: "AI Errors",
        desc: "Error codes and troubleshooting.",
      },
      {
        slug: "ai-examples",
        title: "AI Code Examples",
        desc: "Python and Node.js integration examples.",
      },
    ],
  },
];

export default function DocsPage() {
  return (
    <>
      <h1 className="text-2xl sm:text-4xl font-bold text-slate-900 mb-2">Documentation</h1>
      <p className="text-slate-500 mb-12">
        Everything you need to integrate LintPDF into your workflow.
      </p>

      <div className="space-y-12">
        {sections.map((section) => (
          <div key={section.heading}>
            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-xl font-bold text-slate-900">
                {section.heading}
              </h2>
              {section.badge && (
                <span className="rounded-full bg-brand-900 px-2.5 py-0.5 text-xs font-bold text-white">
                  {section.badge}
                </span>
              )}
            </div>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {section.items.map((item) => (
                <Link
                  key={item.slug}
                  href={`/docs/${item.slug}`}
                  className="rounded-xl border border-slate-200 p-4 hover:border-brand-200 hover:bg-brand-50/30 transition-all group"
                >
                  <h3 className="font-semibold text-slate-900 group-hover:text-brand-700 mb-1 text-sm">
                    {item.title}
                  </h3>
                  <p className="text-xs text-slate-500">{item.desc}</p>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
