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
          { name: "engine", type: "string", description: "Run LintPDF's 600+ checks and produce geometry + capability data." },
          { name: "external", type: "string", description: "Import findings from a third-party preflight (PitStop/callas/Acrobat/native or a custom mapping)." },
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
          { name: "custom", type: "string", description: "Set implicitly when mapping_id is supplied — the tenant's custom mapping parses the report." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">brand</h4>
      <FieldTable
        rows={[
          { name: "anonymous", type: "string", description: "Strip tenant branding AND LintPDF branding. Sanitizes PDF metadata; uses neutral filename." },
          { name: "lintpdf", type: "string", description: "Use LintPDF default branding." },
          { name: "<uuid>", type: "uuid", description: "Apply a tenant-owned BrandProfile by ID. 403/404 if the profile belongs to another tenant or doesn't exist." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">branding-defaults mode</h4>
      <FieldTable
        rows={[
          { name: "anonymous", type: "string", description: "Tenant default is no branding at all (broker → distributor use case). Strips logos, headers, PDF metadata, filename slug, viewer chrome, and share-page chrome." },
          { name: "profile", type: "string", description: "Tenant default is a specific BrandProfile. Requires brand_profile_id." },
          { name: "lintpdf", type: "string", description: "Tenant default is LintPDF's built-in branding." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">severity</h4>
      <FieldTable
        rows={[
          { name: "error", type: "string", description: "Blocking issue — contributes to summary.error_count and makes summary.passed=false." },
          { name: "warning", type: "string", description: "Non-blocking issue — contributes to summary.warning_count." },
          { name: "advisory", type: "string", description: "Informational — does not affect summary.passed." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">verdict</h4>
      <FieldTable
        rows={[
          { name: "pass", type: "string", description: "Reviewer-set or auto-derived approval." },
          { name: "fail", type: "string", description: "Reviewer-set rejection. Requires notes when set manually." },
        ]}
      />
      <p className="text-slate-600 text-sm mt-2">
        The viewer config also carries <code className="bg-slate-100 px-1 rounded">verdict_mode</code>
        {" "}(<code className="bg-slate-100 px-1 rounded">auto | manual | off</code>) which governs
        whether a pass/fail comes from the engine&apos;s summary or a manual
        reviewer action.
      </p>

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">source (finding provenance)</h4>
      <FieldTable
        rows={[
          { name: "engine", type: "string", description: "Produced by LintPDF's native analyzer pipeline." },
          { name: "ai", type: "string", description: "Produced by an AI inspection." },
          { name: "external:pitstop", type: "string", description: "Imported from an Enfocus PitStop XML report." },
          { name: "external:callas", type: "string", description: "Imported from a callas pdfToolbox JSON or XML report." },
          { name: "external:acrobat", type: "string", description: "Imported from an Adobe Acrobat Preflight XML report." },
          { name: "external:lintpdf_json", type: "string", description: "Imported from a LintPDF-native v1 import JSON document." },
          { name: "external:custom:<mapping-id>", type: "string", description: "Imported via a tenant-defined custom mapping; the mapping UUID is appended for audit." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">BrandProfile profile_type</h4>
      <FieldTable
        rows={[
          { name: "custom", type: "string", description: "Use this profile's own brand_name / logo_url / colors / footer_text." },
          { name: "lintpdf", type: "string", description: "Use LintPDF default branding. Useful as a 'reset to defaults' sibling profile." },
          { name: "none", type: "string", description: "Neutral / blind output — blank brand name, generic greys, no footer." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">Finding object_type</h4>
      <FieldTable
        rows={[
          { name: "image", type: "string", description: "Raster XObject." },
          { name: "text", type: "string", description: "Text run." },
          { name: "path", type: "string", description: "Vector path." },
          { name: "font", type: "string", description: "Font resource." },
          { name: "page", type: "string", description: "Whole-page finding." },
          { name: "document", type: "string", description: "Document-level finding (no page reference)." },
        ]}
      />

      <p className="text-slate-600 text-sm mt-4">
        Preflight profiles (as opposed to <em>brand</em> profiles) don&apos;t use a
        string enum — the API exposes a boolean
        {" "}<code className="bg-slate-100 px-1 rounded">is_builtin</code> on
        {" "}<code className="bg-slate-100 px-1 rounded">ProfileSummaryResponse</code> to distinguish
        LintPDF-shipped profiles from tenant-owned customs.
      </p>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">EpmTier</h4>
      <FieldTable
        rows={[
          { name: "pass", type: "string", description: "No EPM-related findings — job runs cleanly on the EPM path." },
          { name: "pass_with_advisory", type: "string", description: "Tier-C advisory findings only; verdict is still PASS but operators should review." },
          { name: "marginal", type: "string", description: "One Tier-B soft-rejection finding fired; treat as borderline." },
          { name: "reject", type: "string", description: "Any Tier-A finding, or two+ Tier-B findings — job is not an EPM candidate." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">decision_type</h4>
      <FieldTable
        rows={[
          { name: "approve", type: "string", description: "Operator approves the job / finding." },
          { name: "reject", type: "string", description: "Operator rejects the job / finding." },
          { name: "waive", type: "string", description: "Operator waives a finding (acknowledges + accepts the risk)." },
          { name: "suppress", type: "string", description: "Hide the finding from future renders without changing severity." },
          { name: "annotate", type: "string", description: "Attach a note/comment without changing approval status." },
          { name: "escalate", type: "string", description: "Bump the finding to a higher reviewer in the approval chain." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">decision_source</h4>
      <FieldTable
        rows={[
          { name: "dashboard", type: "string", description: "Recorded from the LintPDF web dashboard." },
          { name: "api", type: "string", description: "Recorded directly via the REST API (curl/SDK/server-to-server)." },
          { name: "plugin", type: "string", description: "Recorded via a Fairy Ring plugin route." },
          { name: "sdk", type: "string", description: "Recorded via the Python SDK." },
          { name: "share_link", type: "string", description: "Recorded by an anonymous reviewer through a share-link URL." },
          { name: "approval_chain", type: "string", description: "Auto-recorded by the multi-step approval chain workflow." },
          { name: "desktop", type: "string", description: "Recorded from the desktop app." },
          { name: "system", type: "string", description: "Recorded automatically by an internal engine process (no operator)." },
          { name: "migration", type: "string", description: "Synthetic decision created during a data migration." },
        ]}
      />
    </section>
  );
}
