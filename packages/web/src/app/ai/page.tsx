import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI-Powered Preflight — LintPDF",
  description:
    "33 AI inspections across barcode detection, regulatory compliance, content quality, brand verification, and more. Invite-only alpha.",
};

const aiCategories = [
  {
    name: "Barcode Detection",
    count: 7,
    inspections: [
      {
        id: "ai.barcode.type_detection",
        description:
          "Identifies barcode symbology (EAN-13, UPC-A, Code 128, QR, DataMatrix, etc.)",
        severity: "Info",
        tier: "Text",
      },
      {
        id: "ai.barcode.decode_verify",
        description:
          "Decodes barcode content and verifies against expected values",
        severity: "Error",
        tier: "Text",
      },
      {
        id: "ai.barcode.quiet_zone",
        description: "Validates quiet zone dimensions around detected barcodes",
        severity: "Warning",
        tier: "Text",
      },
      {
        id: "ai.barcode.orientation",
        description: "Checks barcode orientation relative to packaging layout",
        severity: "Info",
        tier: "Text",
      },
      {
        id: "ai.barcode.contrast",
        description: "Measures symbol contrast for scanner readability",
        severity: "Error",
        tier: "Text",
      },
      {
        id: "ai.barcode.multiple_detect",
        description:
          "Detects and catalogues all barcodes present in the document",
        severity: "Info",
        tier: "Text",
      },
      {
        id: "ai.barcode.placement",
        description:
          "Validates barcode placement against safe zone requirements",
        severity: "Warning",
        tier: "Text",
      },
    ],
  },
  {
    name: "Content Quality",
    count: 3,
    inspections: [
      {
        id: "ai.content.spell_check",
        description: "AI-powered spell checking with custom dictionary support",
        severity: "Warning",
        tier: "Text",
      },
      {
        id: "ai.content.language_detect",
        description: "Identifies languages present in the document",
        severity: "Info",
        tier: "Text",
      },
      {
        id: "ai.content.duplicate_detect",
        description: "Identifies duplicate or near-duplicate submissions",
        severity: "Info",
        tier: "Text",
      },
    ],
  },
  {
    name: "Color Compliance",
    count: 2,
    inspections: [
      {
        id: "ai.color.brand_palette",
        description:
          "Validates colors against uploaded brand palette definitions",
        severity: "Warning",
        tier: "Text",
      },
      {
        id: "ai.color.contrast_ratio",
        description: "WCAG-style contrast ratio checks for text readability",
        severity: "Info",
        tier: "Text",
      },
    ],
  },
  {
    name: "Regulatory — FDA",
    count: 5,
    inspections: [
      {
        id: "ai.fda.nutrition_panel",
        description:
          "Detects and validates FDA Nutrition Facts panel structure",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.fda.nutrient_order",
        description: "Validates nutrient ordering per 21 CFR 101.9",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.fda.font_sizes",
        description: "Checks minimum font size requirements for label elements",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.fda.serving_size",
        description: "Validates serving size declaration format and placement",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.fda.daily_value",
        description:
          "Checks Percent Daily Value column presence and formatting",
        severity: "Warning",
        tier: "Vision",
      },
    ],
  },
  {
    name: "Regulatory — EU",
    count: 4,
    inspections: [
      {
        id: "ai.eu_fir.x_height",
        description:
          "Validates minimum x-height for mandatory information (1.2mm / 0.9mm)",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.eu_fir.allergen_emphasis",
        description:
          "Checks allergen typographic distinction in ingredients list",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.eu_fir.nutrition_order",
        description:
          "Validates nutritional declaration ordering per Regulation 1169/2011",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.eu_fir.mandatory_fields",
        description: "Checks presence of all mandatory label fields",
        severity: "Error",
        tier: "Vision",
      },
    ],
  },
  {
    name: "Regulatory — GHS/CLP",
    count: 5,
    inspections: [
      {
        id: "ai.ghs.pictogram_detect",
        description: "Detects and identifies GHS hazard pictograms",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.ghs.pictogram_size",
        description:
          "Validates pictogram minimum size (1/15th label area, min 1 cm²)",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.ghs.signal_word",
        description:
          "Checks signal word ('Danger' or 'Warning') presence and correctness",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.ghs.h_statements",
        description:
          "Validates presence and text of required Hazard statements",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.ghs.p_statements",
        description: "Checks Precautionary statements presence",
        severity: "Warning",
        tier: "Vision",
      },
    ],
  },
  {
    name: "Regulatory — Pharma",
    count: 3,
    inspections: [
      {
        id: "ai.pharma.serialization_area",
        description: "Detects EU FMD 2D DataMatrix serialization area",
        severity: "Error",
        tier: "Vision",
      },
      {
        id: "ai.pharma.braille_placeholder",
        description: "Validates Braille area presence on outer packaging",
        severity: "Warning",
        tier: "Vision",
      },
      {
        id: "ai.pharma.font_compliance",
        description: "Checks font size compliance for patient information",
        severity: "Error",
        tier: "Vision",
      },
    ],
  },
  {
    name: "Brand Verification",
    count: 2,
    inspections: [
      {
        id: "ai.brand.logo_match",
        description:
          "Compares detected logos against uploaded brand references",
        severity: "Warning",
        tier: "Vision",
      },
      {
        id: "ai.brand.palette_match",
        description:
          "Validates document colors against brand color definitions",
        severity: "Warning",
        tier: "Text",
      },
    ],
  },
  {
    name: "Visual Quality",
    count: 2,
    inspections: [
      {
        id: "ai.vision.image_quality",
        description:
          "AI visual quality assessment — blur, noise, upscaling detection",
        severity: "Warning",
        tier: "Vision",
      },
      {
        id: "ai.vision.nsfw_detect",
        description: "Content safety screening for inappropriate material",
        severity: "Error",
        tier: "Vision",
      },
    ],
  },
];

const presets = [
  {
    name: "FDA Food",
    description: "All FDA nutrition and labeling inspections",
    inspections: 12,
    tier: "Vision",
  },
  {
    name: "EU Food",
    description: "EU FIR 1169/2011 compliance checks",
    inspections: 10,
    tier: "Vision",
  },
  {
    name: "Pharma EU",
    description: "EU FMD, Braille, font compliance for pharmaceuticals",
    inspections: 9,
    tier: "Vision",
  },
  {
    name: "GHS Chemical",
    description: "GHS/CLP hazard labeling compliance",
    inspections: 12,
    tier: "Vision",
  },
  {
    name: "Packaging QC",
    description: "Barcode, content quality, and visual checks for packaging",
    inspections: 14,
    tier: "Mixed",
  },
  {
    name: "Brand Compliance",
    description: "Logo verification, palette matching, and custom dictionaries",
    inspections: 7,
    tier: "Mixed",
  },
  {
    name: "Full AI Scan",
    description: "All 33 AI inspections — comprehensive analysis",
    inspections: 33,
    tier: "Vision",
  },
];

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="rounded-lg border border-slate-200 bg-brand-950 p-4 text-sm text-slate-300 overflow-x-auto leading-relaxed">
      <code>{children}</code>
    </pre>
  );
}

export default function AIPage() {
  const totalInspections = aiCategories.reduce(
    (sum, cat) => sum + cat.count,
    0,
  );

  return (
    <main>
      {/* Hero */}
      <section className="bg-brand-50/50 pt-20 pb-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <h1 className="text-4xl font-bold text-slate-900 md:text-5xl">
              AI-Powered Preflight Detection
            </h1>
          </div>
          <div className="mb-6">
            <span className="rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white">
              Invite-Only Alpha
            </span>
          </div>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto mb-4">
            We added AI where it actually helps — not everywhere just because we
            could.
          </p>
          <p className="text-base text-slate-400 max-w-2xl mx-auto">
            {totalInspections} AI inspections across {aiCategories.length}{" "}
            categories. Credit-based, detection-only, same Report format.
            Tenant-scoped. AI findings sit alongside core engine findings with a{" "}
            <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono text-slate-600">
              source: &quot;ai&quot;
            </code>{" "}
            field so you always know what detected them.
          </p>
        </div>
      </section>

      {/* Category Overview */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-8">
            Inspection Categories
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {aiCategories.map((cat) => (
              <div
                key={cat.name}
                className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm transition-all hover:shadow-md hover:-translate-y-1"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-slate-900">{cat.name}</h3>
                  <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-bold text-brand-700">
                    {cat.count} checks
                  </span>
                </div>
                <ul className="space-y-1.5">
                  {cat.inspections.slice(0, 3).map((insp) => (
                    <li
                      key={insp.id}
                      className="text-xs text-slate-500 flex items-start gap-1.5"
                    >
                      <svg
                        className="h-3 w-3 mt-0.5 flex-shrink-0 text-brand-500"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      {insp.description}
                    </li>
                  ))}
                  {cat.inspections.length > 3 && (
                    <li className="text-xs text-slate-400 pl-4.5">
                      +{cat.inspections.length - 3} more
                    </li>
                  )}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Full Inspection Reference */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-8">
            Full Inspection Reference
          </h2>
          {aiCategories.map((cat) => (
            <div key={cat.name} className="mb-8">
              <h3 className="font-semibold text-slate-900 mb-3">{cat.name}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">
                        Inspection ID
                      </th>
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">
                        Description
                      </th>
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">
                        Severity
                      </th>
                      <th className="text-left py-2 px-3 text-slate-500 font-medium">
                        Tier
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {cat.inspections.map((insp) => (
                      <tr key={insp.id} className="border-b border-slate-100">
                        <td className="py-2 px-3">
                          <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                            {insp.id}
                          </code>
                        </td>
                        <td className="py-2 px-3 text-slate-600">
                          {insp.description}
                        </td>
                        <td className="py-2 px-3">
                          <span
                            className={`rounded px-2 py-0.5 text-xs font-bold ${
                              insp.severity === "Error"
                                ? "bg-red-500/10 text-red-600 border border-red-500/20"
                                : insp.severity === "Warning"
                                  ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                                  : "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                            }`}
                          >
                            {insp.severity}
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          <span
                            className={`rounded px-2 py-0.5 text-xs font-medium ${
                              insp.tier === "Vision"
                                ? "bg-purple-500/10 text-purple-600 border border-purple-500/20"
                                : "bg-slate-100 text-slate-600 border border-slate-200"
                            }`}
                          >
                            {insp.tier}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Example Finding */}
      <section className="py-16">
        <div className="mx-auto max-w-4xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            AI Findings in Your Report
          </h2>
          <p className="text-slate-500 mb-6">
            AI findings appear alongside core engine findings in the same
            Report. The{" "}
            <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">
              source
            </code>{" "}
            field distinguishes them so you can filter, route, or display them
            separately.
          </p>
          <CodeBlock>{`{
  "inspection_id": "ai.fda.nutrient_order",
  "severity": "error",
  "message": "Nutrient 'Trans Fat' appears after 'Cholesterol' — FDA requires Trans Fat immediately after Saturated Fat",
  "page": 1,
  "source": "ai",
  "category": "regulatory.fda",
  "credits_consumed": 1,
  "model_version": "lintpdf-compliance-v1",
  "confidence": 0.97
}`}</CodeBlock>
        </div>
      </section>

      {/* Pre-built Presets */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Pre-built AI Presets
          </h2>
          <p className="text-slate-500 mb-8">
            Select a preset when submitting a job to run a curated set of AI
            inspections. Or build your own combination in a custom Ruleset.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Preset
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Description
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Inspections
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Tier
                  </th>
                </tr>
              </thead>
              <tbody>
                {presets.map((preset) => (
                  <tr key={preset.name} className="border-b border-slate-100">
                    <td className="py-2 px-3 font-medium text-slate-800">
                      {preset.name}
                    </td>
                    <td className="py-2 px-3 text-slate-600">
                      {preset.description}
                    </td>
                    <td className="py-2 px-3 text-slate-600">
                      {preset.inspections}
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          preset.tier === "Vision"
                            ? "bg-purple-500/10 text-purple-600 border border-purple-500/20"
                            : preset.tier === "Mixed"
                              ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                              : "bg-slate-100 text-slate-600 border border-slate-200"
                        }`}
                      >
                        {preset.tier}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Vision vs Text */}
      <section className="py-16">
        <div className="mx-auto max-w-4xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Vision vs Text Tiers
          </h2>
          <p className="text-slate-500 mb-8">
            AI inspections run on two infrastructure tiers. The tier affects
            processing speed and credit cost.
          </p>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-3">
                <span className="rounded px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                  Text
                </span>
                <h3 className="font-semibold text-slate-900">Text Tier</h3>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed mb-4">
                Text-based analysis: spell checking, language detection, barcode
                decode, color palette matching, duplicate detection.
              </p>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="flex items-start gap-2">
                  <svg
                    className="h-4 w-4 mt-0.5 flex-shrink-0 text-brand-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  1 credit per inspection
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="h-4 w-4 mt-0.5 flex-shrink-0 text-brand-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Sub-second processing
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="h-4 w-4 mt-0.5 flex-shrink-0 text-brand-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Always available
                </li>
              </ul>
            </div>
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-3">
                <span className="rounded px-2 py-0.5 text-xs font-medium bg-purple-500/10 text-purple-600 border border-purple-500/20">
                  Vision
                </span>
                <h3 className="font-semibold text-slate-900">Vision Tier</h3>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed mb-4">
                Vision-based analysis: regulatory panel detection, logo
                matching, NSFW screening, image quality assessment, GHS
                pictogram validation.
              </p>
              <ul className="space-y-2 text-sm text-slate-600">
                <li className="flex items-start gap-2">
                  <svg
                    className="h-4 w-4 mt-0.5 flex-shrink-0 text-brand-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  2 credits per inspection
                </li>
                <li className="flex items-start gap-2">
                  <svg
                    className="h-4 w-4 mt-0.5 flex-shrink-0 text-brand-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  1-5 second processing
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Credit System */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-5xl px-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Credit System
          </h2>
          <p className="text-slate-500 mb-8">
            Core preflight checks remain unlimited on all paid plans. AI
            inspections are metered separately using credits. Pay-per-use at
            $0.12/credit or save with volume packages.
          </p>
          <div className="grid gap-4 md:grid-cols-4">
            {[
              {
                name: "Starter",
                credits: "100",
                price: "$10",
                per: "$0.10/credit",
              },
              {
                name: "Growth",
                credits: "500",
                price: "$40",
                per: "$0.08/credit",
              },
              {
                name: "Scale",
                credits: "2,000",
                price: "$120",
                per: "$0.06/credit",
              },
              {
                name: "Enterprise",
                credits: "10,000",
                price: "$500",
                per: "$0.05/credit",
              },
            ].map((pkg) => (
              <div
                key={pkg.name}
                className="rounded-xl border border-slate-200 bg-white p-5 text-center"
              >
                <h3 className="font-semibold text-slate-900 mb-1">
                  {pkg.name}
                </h3>
                <p className="text-2xl font-bold text-slate-900 mb-1">
                  {pkg.price}
                </p>
                <p className="text-sm text-brand-600 font-medium mb-2">
                  {pkg.credits} credits
                </p>
                <p className="text-xs text-slate-400">{pkg.per}</p>
              </div>
            ))}
          </div>
          <p className="mt-6 text-center text-sm text-slate-400">
            Credits never expire. Available on all paid plans. See{" "}
            <a href="/pricing" className="text-brand-600 hover:underline">
              pricing
            </a>{" "}
            for details.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Request Access
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto mb-8">
            AI inspections are in invite-only alpha. Tell us about your use case
            and we will get you set up.
          </p>
          <a
            href="mailto:sales@lintpdf.com?subject=AI%20Preflight%20Access%20Request"
            className="rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5 inline-block"
          >
            Request Access
          </a>
          <p className="mt-4 text-sm text-slate-400">
            Or email{" "}
            <a
              href="mailto:sales@lintpdf.com"
              className="text-brand-600 hover:underline"
            >
              sales@lintpdf.com
            </a>{" "}
            directly.
          </p>
        </div>
      </section>
    </main>
  );
}
