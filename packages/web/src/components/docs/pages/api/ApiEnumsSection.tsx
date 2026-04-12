import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiEnumsSection() {
  return (
    <section className="mb-12">
      <h3 id="enums" className="text-xl font-bold text-slate-900 mb-3">
        Enum appendix
      </h3>

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">preflight_source</h4>
      <FieldTable
        rows={[
          { name: "engine", type: "string", description: "Run LintPDF's 500+ checks and produce geometry + capability data." },
          { name: "external", type: "string", description: "Import findings from a third-party preflight (PitStop/callas/Acrobat/native)." },
          { name: "minimal", type: "string", description: "No preflight — viewer and share surfaces only. Capabilities can be filled on demand." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">external_format</h4>
      <FieldTable
        rows={[
          { name: "pitstop_xml", type: "string", description: "Enfocus PitStop Server / Pro XML report." },
          { name: "callas_json", type: "string", description: "callas pdfToolbox JSON report." },
          { name: "callas_xml", type: "string", description: "callas pdfToolbox XML report." },
          { name: "acrobat_xml", type: "string", description: "Adobe Acrobat Pro Preflight XML report." },
          { name: "lintpdf_json", type: "string", description: "LintPDF native v1 import JSON. See /schemas/import/v1.json." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">brand</h4>
      <FieldTable
        rows={[
          { name: "anonymous", type: "string", description: "Strip tenant branding AND LintPDF branding. Sanitizes PDF metadata; uses neutral filename." },
          { name: "lintpdf", type: "string", description: "Use LintPDF default branding." },
          { name: "<uuid>", type: "uuid", description: "Apply a tenant-owned BrandProfile by ID. 403 if the profile belongs to another tenant." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">severity</h4>
      <FieldTable
        rows={[
          { name: "error", type: "string", description: "Blocking issue — job verdict is rejected in verdict_mode=auto." },
          { name: "warning", type: "string", description: "Non-blocking issue — job verdict is needs_review in verdict_mode=auto." },
          { name: "advisory", type: "string", description: "Informational — does not affect verdict." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">profile_type</h4>
      <FieldTable
        rows={[
          { name: "builtin", type: "string", description: "Ships with LintPDF (e.g. lintpdf-default, gwg-sheetfed, pdfx4)." },
          { name: "tenant", type: "string", description: "Tenant-owned custom profile. Growth tier+." },
        ]}
      />
    </section>
  );
}
