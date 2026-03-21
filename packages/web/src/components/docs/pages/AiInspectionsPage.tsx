export default function AiInspectionsPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">
        AI Inspections Reference
      </h2>
      <p className="text-slate-600 mb-6">
        Complete reference for all 32 AI inspections, organized by category.
      </p>

      {[
        {
          category: "Barcode Detection",
          inspections: [
            {
              id: "ai.barcode.type_detection",
              desc: "Identifies barcode symbology (EAN-13, UPC-A, Code 128, QR, DataMatrix)",
              severity: "Info",
              tier: "Text",
            },
            {
              id: "ai.barcode.decode_verify",
              desc: "Decodes barcode content and verifies against expected values",
              severity: "Error",
              tier: "Text",
            },
            {
              id: "ai.barcode.quiet_zone",
              desc: "Validates quiet zone dimensions around detected barcodes",
              severity: "Warning",
              tier: "Text",
            },
            {
              id: "ai.barcode.orientation",
              desc: "Checks barcode orientation relative to packaging layout",
              severity: "Info",
              tier: "Text",
            },
            {
              id: "ai.barcode.contrast",
              desc: "Measures symbol contrast for scanner readability",
              severity: "Error",
              tier: "Text",
            },
            {
              id: "ai.barcode.multiple_detect",
              desc: "Detects and catalogues all barcodes in the document",
              severity: "Info",
              tier: "Text",
            },
            {
              id: "ai.barcode.placement",
              desc: "Validates barcode placement against safe zone requirements",
              severity: "Warning",
              tier: "Text",
            },
          ],
        },
        {
          category: "Content Quality",
          inspections: [
            {
              id: "ai.content.spell_check",
              desc: "AI-powered spell checking with custom dictionary support",
              severity: "Warning",
              tier: "Text",
            },
            {
              id: "ai.content.language_detect",
              desc: "Identifies languages present in the document",
              severity: "Info",
              tier: "Text",
            },
            {
              id: "ai.content.duplicate_detect",
              desc: "Identifies duplicate or near-duplicate submissions",
              severity: "Info",
              tier: "Text",
            },
          ],
        },
        {
          category: "Color Compliance",
          inspections: [
            {
              id: "ai.color.brand_palette",
              desc: "Validates colors against uploaded brand palette definitions",
              severity: "Warning",
              tier: "Text",
            },
            {
              id: "ai.color.contrast_ratio",
              desc: "WCAG-style contrast ratio checks for text readability",
              severity: "Info",
              tier: "Text",
            },
          ],
        },
        {
          category: "Regulatory \u2014 FDA",
          inspections: [
            {
              id: "ai.fda.nutrition_panel",
              desc: "Detects and validates Nutrition Facts panel structure",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.fda.nutrient_order",
              desc: "Validates nutrient ordering per 21 CFR 101.9",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.fda.font_sizes",
              desc: "Checks minimum font size requirements (8pt body, 13pt header)",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.fda.serving_size",
              desc: "Validates serving size declaration format and placement",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.fda.daily_value",
              desc: "Checks Percent Daily Value column presence and formatting",
              severity: "Warning",
              tier: "Vision",
            },
          ],
        },
        {
          category: "Regulatory \u2014 EU",
          inspections: [
            {
              id: "ai.eu_fir.x_height",
              desc: "Validates minimum x-height for mandatory information (1.2mm / 0.9mm)",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.eu_fir.allergen_emphasis",
              desc: "Checks allergen typographic distinction in ingredients list",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.eu_fir.nutrition_order",
              desc: "Validates nutritional declaration ordering per 1169/2011",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.eu_fir.mandatory_fields",
              desc: "Checks presence of all mandatory label fields",
              severity: "Error",
              tier: "Vision",
            },
          ],
        },
        {
          category: "Regulatory \u2014 GHS/CLP",
          inspections: [
            {
              id: "ai.ghs.pictogram_detect",
              desc: "Detects and identifies GHS hazard pictograms",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.ghs.pictogram_size",
              desc: "Validates pictogram minimum size (1/15th label area, min 1 cm\u00B2)",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.ghs.signal_word",
              desc: "Checks signal word presence and correctness",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.ghs.h_statements",
              desc: "Validates Hazard statement presence and text",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.ghs.p_statements",
              desc: "Checks Precautionary statement presence",
              severity: "Warning",
              tier: "Vision",
            },
          ],
        },
        {
          category: "Regulatory \u2014 Pharma",
          inspections: [
            {
              id: "ai.pharma.serialization_area",
              desc: "Detects EU FMD 2D DataMatrix serialization area",
              severity: "Error",
              tier: "Vision",
            },
            {
              id: "ai.pharma.braille_placeholder",
              desc: "Validates Braille area presence on outer packaging",
              severity: "Warning",
              tier: "Vision",
            },
            {
              id: "ai.pharma.font_compliance",
              desc: "Checks font size compliance for patient information",
              severity: "Error",
              tier: "Vision",
            },
          ],
        },
        {
          category: "Brand Verification",
          inspections: [
            {
              id: "ai.brand.logo_match",
              desc: "Compares detected logos against uploaded brand references",
              severity: "Warning",
              tier: "Vision",
            },
            {
              id: "ai.brand.palette_match",
              desc: "Validates document colors against brand color definitions",
              severity: "Warning",
              tier: "Text",
            },
          ],
        },
        {
          category: "Visual Quality",
          inspections: [
            {
              id: "ai.vision.image_quality",
              desc: "AI visual quality assessment \u2014 blur, noise, upscaling detection",
              severity: "Warning",
              tier: "Vision",
            },
            {
              id: "ai.vision.nsfw_detect",
              desc: "Content safety screening for inappropriate material",
              severity: "Error",
              tier: "Vision",
            },
          ],
        },
      ].map(({ category, inspections }) => (
        <div key={category} className="mb-8">
          <h3 className="font-semibold text-slate-900 mb-3">{category}</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Check ID
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
                {inspections.map(({ id, desc, severity, tier }) => (
                  <tr key={id} className="border-b border-slate-100">
                    <td className="py-2 px-3">
                      <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                        {id}
                      </code>
                    </td>
                    <td className="py-2 px-3 text-slate-600">{desc}</td>
                    <td className="py-2 px-3">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-bold ${
                          severity === "Error"
                            ? "bg-red-500/10 text-red-600 border border-red-500/20"
                            : severity === "Warning"
                              ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                              : "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                        }`}
                      >
                        {severity}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          tier === "Vision"
                            ? "bg-purple-500/10 text-purple-600 border border-purple-500/20"
                            : "bg-slate-100 text-slate-600 border border-slate-200"
                        }`}
                      >
                        {tier}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </>
  );
}
