import Link from "next/link";
import { CodeBlock } from "@/components/docs/CodeBlock";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ReportFormatsPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Report Formats</h2>
      <p className="text-slate-600 mb-6">
        LintPDF mints reports as immutable tokens. Each token binds a format
        (PDF, HTML, JSON, XML, optionally annotated PDF) and a frozen branding
        state. Consume reports via public share URLs or the authenticated list
        endpoint. See the{" "}
        <Link href="/docs/share-links" className="text-brand-700 hover:underline">
          Share Links
        </Link>
        {" "}and{" "}
        <Link href="/docs/branding-and-anonymous" className="text-brand-700 hover:underline">
          Branding &amp; Anonymous Output
        </Link>{" "}
        pages for the full workflow.
      </p>

      <h3 className="font-semibold text-slate-900 mb-3">Available formats</h3>
      <FieldTable
        rows={[
          { name: "html", type: "format", description: "Branded interactive landing page. Served at /r/{token} (no extension). Plans: Free+." },
          { name: "pdf", type: "format", description: "Print-ready PDF report with summary page and findings detail. Served at /r/{token}.pdf. Plans: Starter+." },
          { name: "json", type: "format", description: "Structured findings matching the LintPDF v1 import schema — re-importable via preflight_source=external, external_format=lintpdf_json. Served at /r/{token}.json. Plans: Free+." },
          { name: "xml", type: "format", description: "Same field taxonomy as JSON, for Switch / MIS / legacy XML consumers. Served at /r/{token}.xml. Plans: Starter+." },
          { name: "annotated_pdf", type: "format", description: "Original PDF with findings drawn as overlays on the source pages. Served at /r/{token}.pdf. Plans: Scale+ (silently skipped if the original PDF cannot be re-fetched from object storage)." },
          { name: "annotated_pdf_markup", type: "format", description: "Original PDF stamped with the reviewer's interactive-viewer markup (rects, circles, arrows, freehand strokes, numbered sticky-note pins) plus an appendix page that resolves each note number to its body and full comment thread. Served at /r/{token}.pdf. Plans: Scale+. Silently skipped if no annotations exist." },
        ]}
      />

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Minting knobs</h3>
      <p className="text-slate-600 mb-3">
        Call <code className="bg-slate-100 px-1 rounded">POST /api/v1/jobs/{`{job_id}`}/reports</code>{" "}
        with the fields below. Every knob has a sensible default, so the
        minimum request is <code className="bg-slate-100 px-1 rounded">{`{ "formats": ["pdf"] }`}</code>.
      </p>
      <FieldTable
        rows={[
          { name: "formats", type: '("html"|"pdf"|"json"|"xml"|"annotated_pdf"|"annotated_pdf_markup")[]', required: true, description: "Output formats to mint. Each gets its own token. Default: [\"html\", \"pdf\"]." },
          { name: "expiry_days", type: "integer", default: "tenant default (typically 7–30)", description: "Token lifetime in days. After expiry the public URLs return 410 Gone." },
          { name: "email_to", type: "string[]", description: "If provided, LintPDF emails the share URLs to these addresses (tenant-branded unless branding=anonymous)." },
          { name: "branding", type: '"anonymous" | "lintpdf" | uuid', description: "Freezes the brand state at mint time. Overrides the tenant default." },
          { name: "detail_level", type: '"executive"|"standard"|"comprehensive"', default: "standard", description: "Narrative density in PDF/HTML — executive is summary-only, comprehensive walks every finding. Ignored by JSON/XML." },
          { name: "summary_page", type: '"prepend"|"only"|"off"', default: "prepend", description: "Controls the PDF summary page placement. Ignored by JSON/XML." },
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
  "schema_version": "1",
  "job_id": "d4e5f6a7-...",
  "profile_id": "lintpdf-default",
  "preflight_source": "engine",
  "external_format": null,
  "summary": {
    "passed": false,
    "total_findings": 7,
    "error_count": 1,
    "warning_count": 4,
    "advisory_count": 2,
    "page_count": 12,
    "file_size_bytes": 1834221
  },
  "document": {
    "pdf_version": "1.7",
    "page_count": 12,
    "is_encrypted": false,
    "conformance": "PDF/X-4"
  },
  "findings": [
    {
      "inspection_id": "LPDF_FONT_001",
      "severity": "error",
      "message": "Font 'Helvetica' is not embedded",
      "page_num": 1,
      "object_id": "F1",
      "object_type": "font",
      "iso_clause": "ISO 32000-2:2020 9.6",
      "category": "fonts",
      "source": "engine",
      "bbox": [72.0, 720.0, 540.0, 740.0],
      "details": { "font_name": "Helvetica" }
    }
  ],
  "metadata": { "pdf_version": "1.7", "page_count": 12, "...": "..." },
  "duration_ms": 4321
}`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">XML schema</h3>
      <p className="text-slate-600 mb-4">
        XML reports follow the same field taxonomy as JSON in the
        {" "}<code className="bg-slate-100 px-1 rounded">urn:lintpdf:preflight:1.0</code>{" "}
        namespace. Use them for integrations that already consume XML preflight
        output (Switch, legacy MIS).
      </p>
      <CodeBlock>{`<?xml version="1.0" encoding="UTF-8"?>
<PreflightReport xmlns="urn:lintpdf:preflight:1.0" schemaVersion="1">
  <JobId>d4e5f6a7-...</JobId>
  <ProfileId>lintpdf-default</ProfileId>
  <DurationMs>4321</DurationMs>
  <PreflightSource>engine</PreflightSource>
  <Summary>
    <Passed>false</Passed>
    <TotalFindings>7</TotalFindings>
    <ErrorCount>1</ErrorCount>
    <WarningCount>4</WarningCount>
    <AdvisoryCount>2</AdvisoryCount>
    <PageCount>12</PageCount>
    <FileSizeBytes>1834221</FileSizeBytes>
  </Summary>
  <Document>
    <PdfVersion>1.7</PdfVersion>
    <IsEncrypted>false</IsEncrypted>
    <Conformance>PDF/X-4</Conformance>
  </Document>
  <Findings>
    <Finding>
      <InspectionId>LPDF_FONT_001</InspectionId>
      <Severity>error</Severity>
      <Message>Font 'Helvetica' is not embedded</Message>
      <PageNum>1</PageNum>
      <ObjectId>F1</ObjectId>
      <ObjectType>font</ObjectType>
      <IsoClause>ISO 32000-2:2020 9.6</IsoClause>
      <Category>fonts</Category>
      <Source>engine</Source>
      <BBox>72.0 720.0 540.0 740.0</BBox>
      <Details>
        <Detail key="font_name">Helvetica</Detail>
      </Details>
    </Finding>
  </Findings>
</PreflightReport>`}</CodeBlock>

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
      <p className="text-slate-600 text-sm mt-2">
        JSON and XML formats are identical regardless of branding mode — only
        document metadata can carry brand identifiers, and structured payloads
        don&apos;t embed any.
      </p>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        Consuming a report URL
      </h3>
      <CodeBlock>{`# Interactive HTML landing (share with anyone)
GET  https://reports.lintpdf.com/r/rpt_01HXY...

# PDF download (?download=1 forces Content-Disposition: attachment)
GET  https://reports.lintpdf.com/r/rpt_01HXY....pdf?download=1

# Structured JSON (LintPDF v1 import schema, public)
GET  https://reports.lintpdf.com/r/rpt_01HXY....json

# Legacy XML (same taxonomy as JSON, public)
GET  https://reports.lintpdf.com/r/rpt_01HXY....xml

# Findings-only JSON via the API host (alias of /r/{token}.json)
GET  https://api.lintpdf.com/api/v1/reports/tokens/rpt_01HXY.../findings

# Revoke (authenticated)
DELETE https://api.lintpdf.com/api/v1/jobs/{job_id}/reports/rpt_01HXY...`}</CodeBlock>
    </>
  );
}
