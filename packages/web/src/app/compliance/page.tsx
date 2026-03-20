import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Regulatory Compliance — LintPDF",
  description:
    "Automated regulatory compliance for packaging: FDA Nutrition Facts, EU Food Information, GHS/CLP Chemical Labels, and Pharmaceutical Packaging.",
};

const regulations = [
  {
    id: "fda",
    name: "FDA Nutrition Facts",
    standard: "21 CFR 101.9",
    description:
      "United States Food and Drug Administration requirements for nutrition labeling on food packaging.",
    checks: [
      {
        check: "Nutrition Facts header font size",
        severity: "Error",
        description:
          "Header must be in 13pt or larger Franklin Gothic Heavy or equivalent.",
      },
      {
        check: "Serving size declaration",
        severity: "Error",
        description:
          "Serving size and servings per container must be present and correctly formatted.",
      },
      {
        check: "Nutrient ordering",
        severity: "Error",
        description:
          "Nutrients must appear in the FDA-mandated order (calories, total fat, saturated fat, trans fat, etc.).",
      },
      {
        check: "Daily value percentages",
        severity: "Warning",
        description:
          "Percent Daily Value column must be present and right-aligned.",
      },
      {
        check: "Font size minimums",
        severity: "Error",
        description:
          "Body text minimum 8pt. Packages with < 40 sq in PDP may use 6pt minimum.",
      },
      {
        check: "Hairline rules",
        severity: "Info",
        description:
          "Horizontal rules between nutrient groups must meet minimum weight specifications.",
      },
      {
        check: "Footnote presence",
        severity: "Warning",
        description:
          "The '% Daily Value' footnote must be present on standard format labels.",
      },
    ],
    example: {
      inspection_id: "ai.fda.nutrient_order",
      severity: "error",
      message:
        "Nutrient 'Trans Fat' appears after 'Cholesterol' — FDA requires Trans Fat immediately after Saturated Fat",
      page: 1,
      source: "ai",
    },
  },
  {
    id: "eu-fir",
    name: "EU Food Information",
    standard: "Regulation (EU) No 1169/2011",
    description:
      "European Union requirements for food information provided to consumers, including nutritional declarations and allergen labeling.",
    checks: [
      {
        check: "x-height minimum",
        severity: "Error",
        description:
          "Mandatory information must have an x-height of at least 1.2mm (0.9mm for packages < 80 cm²).",
      },
      {
        check: "Allergen emphasis",
        severity: "Error",
        description:
          "Allergens in ingredients list must be typographically distinguished (bold, underline, or CAPS).",
      },
      {
        check: "Nutritional declaration order",
        severity: "Error",
        description:
          "Must follow: energy, fat, saturates, carbohydrate, sugars, protein, salt.",
      },
      {
        check: "Mandatory fields present",
        severity: "Error",
        description:
          "Product name, ingredients, allergens, net quantity, date marking, storage conditions, origin (where required).",
      },
      {
        check: "Energy units",
        severity: "Warning",
        description: "Energy must be expressed in both kJ and kcal.",
      },
      {
        check: "Per 100g/100ml declaration",
        severity: "Error",
        description:
          "Nutritional values must be declared per 100g or per 100ml.",
      },
    ],
    example: {
      inspection_id: "ai.eu_fir.allergen_emphasis",
      severity: "error",
      message:
        "Allergen 'milk' in ingredients list is not typographically distinguished — EU 1169/2011 Article 21 requires emphasis",
      page: 1,
      source: "ai",
    },
  },
  {
    id: "ghs",
    name: "GHS/CLP Chemical Labels",
    standard: "Regulation (EC) No 1272/2008",
    description:
      "Globally Harmonized System of Classification and Labelling of Chemicals, implemented in the EU as the CLP Regulation.",
    checks: [
      {
        check: "Hazard pictogram presence",
        severity: "Error",
        description:
          "All required GHS pictograms must be present based on product classification.",
      },
      {
        check: "Pictogram minimum size",
        severity: "Error",
        description:
          "Each pictogram must be at least 1/15th of the label area, minimum 1 cm².",
      },
      {
        check: "Signal word",
        severity: "Error",
        description:
          "'Danger' or 'Warning' must be present and match the highest hazard classification.",
      },
      {
        check: "H-statement validation",
        severity: "Error",
        description:
          "All required Hazard statements must be present with correct codes and text.",
      },
      {
        check: "P-statement validation",
        severity: "Warning",
        description:
          "Precautionary statements must be present and appropriate for the classification.",
      },
      {
        check: "Supplier identification",
        severity: "Warning",
        description:
          "Name, address, and telephone number of the supplier must be present.",
      },
      {
        check: "Product identifier",
        severity: "Error",
        description:
          "Product name and chemical identifiers must be present on the label.",
      },
    ],
    example: {
      inspection_id: "ai.ghs.pictogram_size",
      severity: "error",
      message:
        "GHS07 (exclamation mark) pictogram area is 0.8 cm² — minimum required is 1 cm² per CLP Regulation",
      page: 1,
      source: "ai",
    },
  },
  {
    id: "pharma",
    name: "Pharmaceutical Packaging",
    standard: "EU FMD (2011/62/EU) & National Requirements",
    description:
      "Pharmaceutical packaging requirements including serialization, Braille, patient information leaflets, and font compliance.",
    checks: [
      {
        check: "Serialization area",
        severity: "Error",
        description:
          "EU Falsified Medicines Directive requires 2D DataMatrix code area with adequate quiet zones.",
      },
      {
        check: "Braille placeholder",
        severity: "Warning",
        description:
          "Outer packaging must include Braille rendering of the medicine name (or placeholder area).",
      },
      {
        check: "Font size compliance",
        severity: "Error",
        description:
          "Patient information must meet minimum font size requirements per national guidelines.",
      },
      {
        check: "Leaflet structure",
        severity: "Info",
        description:
          "Patient information leaflet should follow the standard QRD template section ordering.",
      },
      {
        check: "Tamper evidence indicator",
        severity: "Warning",
        description:
          "Anti-tampering device area must be identifiable on the packaging artwork.",
      },
      {
        check: "Batch and expiry placement",
        severity: "Error",
        description:
          "Batch number and expiry date must be present and positioned per requirements.",
      },
    ],
    example: {
      inspection_id: "ai.pharma.serialization_area",
      severity: "error",
      message:
        "2D DataMatrix serialization area not detected — EU FMD requires serialization on outer packaging",
      page: 1,
      source: "ai",
    },
  },
];

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="rounded-lg border border-slate-200 bg-brand-950 p-4 text-sm text-slate-300 overflow-x-auto leading-relaxed">
      <code>{children}</code>
    </pre>
  );
}

export default function CompliancePage() {
  return (
    // skipcq: JS-0415
    <main>
      {/* Hero */}
      <section className="bg-brand-50/50 pt-20 pb-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <h1 className="text-4xl font-bold text-slate-900 md:text-5xl">
              Automated Regulatory Compliance for Packaging
            </h1>
          </div>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto">
            FDA, EU, GHS, and pharmaceutical label requirements — validated
            automatically against your artwork before it reaches production.
            Catch compliance failures at preflight, not at recall.
          </p>
          <div className="mt-6">
            <span className="rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white">
              AI Compliance — Invite-Only Alpha
            </span>
          </div>
        </div>
      </section>

      {/* Regulations */}
      {/* skipcq: JS-0415 */}
      {regulations.map((reg, index) => (
        <section
          key={reg.id}
          className={index % 2 === 0 ? "py-16" : "bg-brand-50/50 py-16"}
        >
          <div className="mx-auto max-w-5xl px-6">
            <div className="mb-8">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-slate-900">
                  {reg.name}
                </h2>
                <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                  {reg.standard}
                </span>
              </div>
              <p className="text-slate-500 max-w-3xl">{reg.description}</p>
            </div>

            {/* Checks Table */}
            <h3 className="font-semibold text-slate-900 mb-4">
              What LintPDF Checks
            </h3>
            <div className="overflow-x-auto mb-8">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b-2 border-slate-200">
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">
                      Check
                    </th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">
                      Severity
                    </th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {reg.checks.map((check) => (
                    <tr key={check.check} className="border-b border-slate-100">
                      <td className="py-2 px-3 font-medium text-slate-800">
                        {check.check}
                      </td>
                      <td className="py-2 px-3">
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-bold ${
                            check.severity === "Error"
                              ? "bg-red-500/10 text-red-600 border border-red-500/20"
                              : check.severity === "Warning"
                                ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                                : "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                          }`}
                        >
                          {check.severity}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-slate-600">
                        {check.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Example Finding */}
            <h3 className="font-semibold text-slate-900 mb-3">
              Example Finding
            </h3>
            <CodeBlock>{JSON.stringify(reg.example, null, 2)}</CodeBlock>
          </div>
        </section>
      ))}

      {/* CTA */}
      <section className="bg-brand-50/50 py-16">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Request Access to AI Compliance Features
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto mb-8">
            AI Compliance inspections are in invite-only alpha. Contact us to
            discuss your regulatory requirements and get early access.
          </p>
          <a
            href="mailto:sales@lintpdf.com?subject=AI%20Compliance%20Access%20Request"
            className="rounded-xl bg-brand-900 px-8 py-3.5 text-base font-semibold text-white transition-all hover:bg-brand-800 hover:shadow-lg hover:shadow-brand-900/20 hover:-translate-y-0.5 inline-block"
          >
            Request Access
          </a>
        </div>
      </section>
    </main>
  );
}
