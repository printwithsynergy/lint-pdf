import Link from "next/link";
import { CodeBlock } from "@/components/docs/CodeBlock";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ReportFormatsPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Report Formats</h2>
      <p className="text-slate-600 mb-6">
        LintPDF mints reports as immutable tokens. Each token binds a format
        (PDF, HTML, JSON, XML) and a frozen branding state. Consume reports via
        public share URLs or the authenticated list endpoint. See the{" "}
        <Link href="/docs/share-links" className="text-brand-700 hover:underline">
          Share Links
        </Link>
        {" "}and{" "}
        <Link href="/docs/branding-and-anonymous" className="text-brand-700 hover:underline">
          Branding &amp; Anonymous Output
        </Link>{" "}
        pages for the full workflow.
      </p>

      <h3 className="font-semibold text-slate-900 mb-3">Minting knobs</h3>
      <p className="text-slate-600 mb-3">
        Call <code className="bg-slate-100 px-1 rounded">POST /api/v1/jobs/{`{job_id}`}/reports</code>{" "}
        with the fields below. Every knob has a sensible default, so the
        minimum request is <code className="bg-slate-100 px-1 rounded">{`{ "formats": ["pdf"] }`}</code>.
      </p>
      <FieldTable
        rows={[
          { name: "formats", type: '("pdf"|"html"|"json"|"xml")[]', required: true, description: "Output formats to mint. Each gets its own token." },
          { name: "expiry_days", type: "integer", default: "30", description: "Token lifetime. Range 1–365. After expiry the public URLs return 410 Gone." },
          { name: "email_to", type: "string[]", description: "If provided, LintPDF emails the share URLs to these addresses (tenant-branded unless branding=anonymous)." },
          { name: "branding", type: '"anonymous" | "lintpdf" | uuid', description: "Freezes the brand state at mint time. Overrides the tenant default." },
          { name: "detail_level", type: '"executive"|"standard"|"comprehensive"', default: "standard", description: "Narrative density in PDF/HTML — executive is summary-only, comprehensive walks every finding." },
          { name: "summary_page", type: '"prepend"|"only"|"off"', default: "prepend", description: "Controls the PDF summary page placement." },
        ]}
      />

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">JSON schema</h3>
      <p className="text-slate-600 mb-3">
        The <code className="bg-slate-100 px-1 rounded">json</code> format returns the full job payload plus
        frozen source metadata. Import this shape directly using the native{" "}
        <Link href="/docs/import-schema" className="text-brand-700 hover:underline">
          LintPDF v1 import schema
        </Link>.
      </p>
      <CodeBlock>{`{
  "job_id": "d4e5f6a7-...",
  "status": "complete",
  "verdict": "rejected",
  "preflight_source": "external",
  "external_format": "pitstop_xml",
  "profile_id": "lintpdf-default",
  "file_name": "brochure.pdf",
  "page_count": 12,
  "summary": { "total_findings": 7, "error": 1, "warning": 4, "advisory": 2 },
  "findings": [
    {
      "inspection_id": "pitstop:font.not_embedded",
      "severity": "error",
      "message": "Font 'Helvetica' is not embedded",
      "page_num": 1,
      "bbox": [72, 720, 540, 740],
      "source": { "type": "external", "format": "pitstop_xml", "profile": "Sheetfed" }
    }
  ]
}`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        PDF &amp; HTML reports — branding resolution
      </h3>
      <p className="text-slate-600 mb-3">
        The PDF and HTML formats honour <code className="bg-slate-100 px-1 rounded">branding</code> at mint
        time. Anonymous mode is the strongest — it strips tenant branding,
        LintPDF branding, PDF document metadata (Author/Producer/Creator), and
        uses a neutral filename:
      </p>
      <FieldTable
        rows={[
          { name: "Filename (anonymous)", type: "string", description: "preflight-<short-id>.pdf — no tenant slug, no brand reference." },
          { name: "Filename (tenant)", type: "string", description: "{tenant-slug}-<short-id>.pdf — derived from the BrandProfile." },
          { name: "Filename (lintpdf)", type: "string", description: "lintpdf-<short-id>.pdf." },
          { name: "PDF Author", type: "metadata", description: "Anonymous: empty. Tenant: BrandProfile.company_name. LintPDF: 'LintPDF'." },
          { name: "PDF Producer", type: "metadata", description: "Anonymous: generic 'Preflight Report'. Otherwise: 'LintPDF <version>'." },
          { name: "PDF Creator", type: "metadata", description: "Anonymous: generic 'Preflight Report'. Otherwise: tenant or LintPDF brand string." },
          { name: "Footer / header", type: "render", description: "Anonymous: empty. Tenant: BrandProfile.footer_text + logo. LintPDF: product mark." },
        ]}
      />

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        Consuming a report URL
      </h3>
      <CodeBlock>{`# HTML landing (share with anyone)
GET  https://reports.lintpdf.com/r/rpt_01HXY...

# PDF download
GET  https://reports.lintpdf.com/r/rpt_01HXY....pdf?download=1

# Structured findings for the token (unauthenticated)
GET  https://api.lintpdf.com/api/v1/reports/tokens/rpt_01HXY.../findings

# Revoke (authenticated)
DELETE https://api.lintpdf.com/api/v1/jobs/{job_id}/reports/rpt_01HXY...`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">XML format</h3>
      <p className="text-slate-600 mb-4">
        XML reports follow the same field taxonomy as JSON. Use them for
        integrations that already consume XML preflight output (Switch, legacy
        MIS).
      </p>
      <CodeBlock>{`<?xml version="1.0" encoding="UTF-8"?>
<report job-id="d4e5f6a7-..." status="complete" verdict="rejected">
  <preflight-source>external</preflight-source>
  <external-format>pitstop_xml</external-format>
  <summary total="7" error="1" warning="4" advisory="2" />
  <findings>
    <finding inspection="pitstop:font.not_embedded" severity="error" page="1">
      <message>Font 'Helvetica' is not embedded</message>
      <bbox>72 720 540 740</bbox>
    </finding>
  </findings>
</report>`}</CodeBlock>
    </>
  );
}
