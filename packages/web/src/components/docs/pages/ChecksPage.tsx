import Link from "next/link";

export default function ChecksPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">
        Checks Reference
      </h2>
      <p className="text-slate-600 mb-4">
        LintPDF runs 600+ individual Checks across these categories — 259
        rule-based engine checks, 247 PDF/X-4 conformance checks, and 99 AI
        inspections. Each finding in a Report references a Check ID, severity
        level, and affected page.
      </p>
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 mb-6 text-sm text-slate-600">
        <p className="mb-2">
          <strong className="text-slate-900">Engine mode only.</strong> The 600+
          checks below only run when{" "}
          <code className="bg-white px-1 rounded">preflight_source=engine</code>.
          Jobs submitted with{" "}
          <code className="bg-white px-1 rounded">preflight_source=external</code>{" "}
          import their findings verbatim from PitStop / callas / Acrobat /
          native payloads — LintPDF does not re-check them. See{" "}
          <Link
            href="/docs/preflight-modes"
            className="text-brand-700 hover:underline"
          >
            Preflight Modes
          </Link>{" "}
          for the full matrix.
        </p>
        <p>
          Programmatic consumers should fetch the full registry from{" "}
          <code className="bg-white px-1 rounded">GET /api/v1/check-names</code>
          {" "}(unauthenticated, cache-friendly) — it returns the canonical{" "}
          <code className="bg-white px-1 rounded">inspection_id → {`{ name, description }`}</code>
          {" "}mapping for every shipping check.
        </p>
      </div>

      {[
        {
          category: "Fonts",
          inspections: [
            {
              id: "font.not_embedded",
              desc: "Font is referenced but not embedded in the PDF",
            },
            {
              id: "font.subset_incomplete",
              desc: "Font subset is missing required glyphs",
            },
            {
              id: "font.type3_detected",
              desc: "Type 3 font detected (bitmap, not scalable)",
            },
            {
              id: "font.encoding_mismatch",
              desc: "Font encoding does not match declared encoding",
            },
            {
              id: "font.simulated_bold_italic",
              desc: "Bold or italic style is simulated, not native",
            },
          ],
        },
        {
          category: "Color Spaces",
          inspections: [
            {
              id: "color.rgb_in_cmyk_workflow",
              desc: "RGB color space found in CMYK workflow",
            },
            {
              id: "color.spot_color_usage",
              desc: "Spot color detected in document",
            },
            {
              id: "color.icc_profile_missing",
              desc: "Output intent ICC profile not embedded",
            },
            {
              id: "color.overprint_conflict",
              desc: "Overprint settings may cause unexpected output",
            },
            {
              id: "color.ink_coverage_exceeded",
              desc: "Total area coverage exceeds threshold",
            },
          ],
        },
        {
          category: "Images",
          inspections: [
            {
              id: "image.low_resolution",
              desc: "Image resolution below minimum DPI threshold",
            },
            {
              id: "image.jpeg_artifacts",
              desc: "JPEG compression artifacts detected",
            },
            {
              id: "image.missing_or_corrupt",
              desc: "Image stream is missing or corrupted",
            },
            {
              id: "image.alpha_transparency",
              desc: "Image contains alpha channel transparency",
            },
          ],
        },
        {
          category: "Transparency",
          inspections: [
            {
              id: "transparency.present",
              desc: "Transparency effects detected in document",
            },
            {
              id: "transparency.blend_mode",
              desc: "Non-standard blend mode in use",
            },
            {
              id: "transparency.soft_mask",
              desc: "Soft mask (gradient transparency) detected",
            },
          ],
        },
        {
          category: "Page Geometry",
          inspections: [
            {
              id: "geometry.trim_box_missing",
              desc: "TrimBox not defined (required for print)",
            },
            {
              id: "geometry.bleed_insufficient",
              desc: "Bleed area smaller than minimum threshold",
            },
            {
              id: "geometry.page_size_mismatch",
              desc: "Page dimensions do not match expected size",
            },
            {
              id: "geometry.content_outside_trim",
              desc: "Content extends beyond TrimBox",
            },
          ],
        },
        {
          category: "Compliance",
          inspections: [
            {
              id: "compliance.pdfx4_violation",
              desc: "Document violates PDF/X-4 (ISO 15930-7) requirements",
            },
            {
              id: "compliance.pdfa_violation",
              desc: "Document violates PDF/A archival requirements",
            },
            {
              id: "compliance.javascript_present",
              desc: "JavaScript detected (prohibited in PDF/X)",
            },
            {
              id: "compliance.encryption_present",
              desc: "Document encryption detected",
            },
          ],
        },
        {
          category: "Barcodes",
          inspections: [
            {
              id: "barcode.detected",
              desc: "Barcode pattern detected in page content",
            },
            {
              id: "barcode.low_dpi",
              desc: "Barcode area DPI below minimum threshold",
            },
            {
              id: "barcode.non_compliant_colors",
              desc: "Barcode uses colors that may not scan correctly",
            },
            {
              id: "barcode.decode_failed",
              desc: "Barcode could not be decoded",
            },
            {
              id: "barcode.grade_below_threshold",
              desc: "ISO 15416 barcode grade below minimum",
            },
            {
              id: "barcode.quiet_zone_insufficient",
              desc: "Barcode quiet zone smaller than required",
            },
          ],
        },
        {
          category: "Dieline / Cutter",
          inspections: [
            {
              id: "LPDF_DIE_ZORDER",
              desc: "Dieline drawn below artwork (D-06) — cutter spot must paint on top of every other layer",
            },
            {
              id: "LPDF_DIE_KNOCKOUT",
              desc: "Dieline stroke set to knockout instead of overprint (D-07) — leaves white gaps along cut lines",
            },
            {
              id: "LPDF_DIE_BLEND_MODE",
              desc: "Dieline painted with non-Normal blend mode (D-08) — RIP will drop or composite the cutter plate",
            },
            {
              id: "LPDF_DIE_OPACITY_LOW",
              desc: "Dieline painted with reduced opacity (D-09) — partial alpha does not survive RIP separation",
            },
            {
              id: "LPDF_PAGE_BLEED_PAST_DIELINE",
              desc: "Page BleedBox extends past the dieline polygon (P-30) — press-side bleed allowance does not fit inside the cutter region",
            },
            {
              id: "LPDF_TEXT_ON_DIELINE_PATH",
              desc: "Text region overlaps the dieline cut path (F-32) — glyphs will be physically sliced at the cutter",
            },
            {
              id: "LPDF_DIE_AS_ART",
              desc: "Dieline spot used as a fill (D-15) — cutter will follow the filled region as a closed path",
            },
            {
              id: "LPDF_DIE_LAYER_CONTENT",
              desc: "Foreign content on a dieline-named OCG layer (D-04) — artwork on the cutter plate",
            },
            {
              id: "LPDF_DIE_CONTENT_OUTSIDE",
              desc: "Content extends beyond the dieline polygon (D-15) — risks clipping in production",
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
                </tr>
              </thead>
              <tbody>
                {inspections.map(({ id, desc }) => (
                  <tr key={id} className="border-b border-slate-100">
                    <td className="py-2 px-3">
                      <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                        {id}
                      </code>
                    </td>
                    <td className="py-2 px-3 text-slate-600">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      <p className="text-sm text-slate-500 mt-4">
        This is a representative sample. The full suite includes 600+ checks.
        Use the{" "}
        <code className="bg-slate-100 px-1 rounded">GET /api/v1/rulesets</code>{" "}
        endpoint to see which Checks are included in each Ruleset.
      </p>
    </>
  );
}
