import type { Metadata } from "next";
import { DocsNav } from "@/components/DocsNav";
import { glossary } from "@/lib/brand";

export const metadata: Metadata = {
  title: "Documentation — LintPDF",
  description:
    "API reference, getting started guide, and full documentation for the LintPDF PDF preflight engine.",
};

const methodColors: Record<string, string> = {
  GET: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  POST: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  PUT: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  DELETE: "bg-red-500/10 text-red-600 border-red-500/20",
};

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="rounded-lg border border-slate-200 bg-brand-950 p-4 text-sm text-slate-300 overflow-x-auto leading-relaxed">
      <code>{children}</code>
    </pre>
  );
}

function Endpoint({
  method,
  path,
  description,
  auth,
  request,
  response,
}: {
  method: string;
  path: string;
  description: string;
  auth: boolean;
  request: string;
  response: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 overflow-hidden mb-6">
      <div className="flex items-center gap-3 border-b border-slate-200 px-6 py-4 bg-slate-50">
        <span
          className={`rounded border px-2.5 py-0.5 text-xs font-bold ${methodColors[method] ?? ""}`}
        >
          {method}
        </span>
        <code className="text-sm text-slate-800 font-mono">{path}</code>
        {auth && (
          <span className="ml-auto rounded bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700 border border-amber-500/20">
            API Key required
          </span>
        )}
      </div>
      <div className="px-6 py-4">
        <p className="text-sm text-slate-600 mb-4">{description}</p>
        <div className="mb-4">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Request
          </h4>
          <CodeBlock>{request}</CodeBlock>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Response
          </h4>
          <CodeBlock>{response}</CodeBlock>
        </div>
      </div>
    </div>
  );
}

export default function DocsPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-16 lg:flex lg:gap-12">
      <DocsNav />

      <main className="min-w-0 flex-1">
        <h1 className="text-4xl font-bold text-slate-900 mb-2">
          Documentation
        </h1>
        <p className="text-slate-500 mb-12">
          Everything you need to integrate LintPDF into your workflow.
        </p>

        {/* ── Getting Started ── */}
        <section id="getting-started" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Getting Started
          </h2>
          <p className="text-slate-600 mb-6">
            LintPDF is a detection-only PDF preflight engine. You send a file,
            you get a report. Three steps to your first Report:
          </p>

          <div className="grid gap-6 md:grid-cols-3 mb-8">
            <div className="rounded-xl border border-slate-200 p-5">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-sm font-bold mb-3">
                1
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">Sign up</h3>
              <p className="text-sm text-slate-500">
                Create an account at{" "}
                <a
                  href="https://app.lintpdf.com"
                  className="text-brand-600 hover:underline"
                >
                  app.lintpdf.com
                </a>{" "}
                and navigate to Dashboard.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 p-5">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-sm font-bold mb-3">
                2
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">
                Get your API Key
              </h3>
              <p className="text-sm text-slate-500">
                Generate an API key from the API Key section. Your key starts
                with{" "}
                <code className="bg-slate-100 px-1 rounded text-xs">lpdf_</code>
                .
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 p-5">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-sm font-bold mb-3">
                3
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">
                Submit your first file
              </h3>
              <p className="text-sm text-slate-500">
                Submit a PDF to the Submit endpoint and retrieve your Report.
              </p>
            </div>
          </div>

          <h3 className="font-semibold text-slate-900 mb-3">Quick example</h3>
          <CodeBlock>{`# Submit a PDF for preflight
curl -X POST https://api.lintpdf.com/api/v1/submit \\
  -H "Authorization: Bearer lpdf_your_api_key" \\
  -F file=@brochure.pdf \\
  -F ruleset=gwg-sheetfed

# Retrieve the Report
curl https://api.lintpdf.com/api/v1/reports/f47ac10b-... \\
  -H "Authorization: Bearer lpdf_your_api_key"`}</CodeBlock>
        </section>

        {/* ── Authentication ── */}
        <section id="authentication" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Authentication
          </h2>
          <p className="text-slate-600 mb-4">
            Include your API Key in the{" "}
            <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono">
              Authorization
            </code>{" "}
            header as a Bearer token:
          </p>
          <CodeBlock>Authorization: Bearer lpdf_your_api_key</CodeBlock>
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm text-amber-800">
              <span className="font-semibold">Keep your API Key secret.</span>{" "}
              Never expose it in client-side code, public repositories, or
              browser requests. Use environment variables and server-side calls
              only.
            </p>
          </div>
        </section>

        {/* ── API Reference ── */}
        <section id="api-reference" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            API Reference
          </h2>
          <p className="text-slate-600 mb-2">
            Base URL:{" "}
            <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono">
              https://api.lintpdf.com
            </code>
          </p>
          <p className="text-slate-500 text-sm mb-8">
            All endpoints return JSON. Authenticated endpoints require a valid
            API Key.
          </p>

          <Endpoint
            method="POST"
            path="/api/v1/submit"
            description="Submit a file for preflight analysis. Accepts PDF, EPS, PostScript, TIFF, JPEG, PNG, and PDF-compatible AI files. Non-PDF files are converted internally before checking."
            auth
            request={`curl -X POST https://api.lintpdf.com/api/v1/submit \\
  -H "Authorization: Bearer lpdf_..." \\
  -F file=@document.pdf \\
  -F ruleset=gwg-sheetfed`}
            response={`{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "processing",
  "ruleset": "gwg-sheetfed",
  "file_name": "document.pdf",
  "created_at": "2026-03-15T10:30:00Z"
}`}
          />

          <Endpoint
            method="GET"
            path="/api/v1/reports/{id}"
            description="Retrieve the Report for a completed preflight job. Includes summary, findings with severity levels (Error, Warning, Info), and page locations."
            auth
            request={`curl https://api.lintpdf.com/api/v1/reports/f47ac10b-... \\
  -H "Authorization: Bearer lpdf_..."`}
            response={`{
  "id": "f47ac10b-...",
  "status": "complete",
  "verdict": "error",
  "ruleset": "gwg-sheetfed",
  "file_name": "document.pdf",
  "page_count": 4,
  "duration_ms": 1240,
  "summary": {
    "total_findings": 3,
    "error": 1,
    "warning": 1,
    "info": 1
  },
  "findings": [
    {
      "inspection_id": "font.not_embedded",
      "severity": "error",
      "message": "Font 'Helvetica' is not embedded",
      "page": 1
    },
    {
      "inspection_id": "color.spot_color_usage",
      "severity": "warning",
      "message": "Spot color 'PANTONE 185 C' found on page 2",
      "page": 2
    },
    {
      "inspection_id": "image.low_resolution",
      "severity": "info",
      "message": "Image at 150 DPI (minimum 300 DPI recommended)",
      "page": 3
    }
  ]
}`}
          />

          <Endpoint
            method="GET"
            path="/api/v1/reports/{id}/report?format=pdf|json|xml"
            description="Download the Report as a formatted report. PDF reports include tenant White Label (logo, colors, footer) when configured. JSON and XML are machine-readable."
            auth
            request={`# PDF report (white-labeled)
curl -o report.pdf \\
  "https://api.lintpdf.com/api/v1/reports/f47ac10b-.../report?format=pdf" \\
  -H "Authorization: Bearer lpdf_..."

# JSON report
curl "https://api.lintpdf.com/api/v1/reports/f47ac10b-.../report?format=json" \\
  -H "Authorization: Bearer lpdf_..."`}
            response={`200 OK
Content-Type: application/pdf (or application/json, application/xml)

# JSON format returns the same structure as GET /api/v1/reports/{id}
# PDF format returns a branded, downloadable report
# XML format returns a structured XML document`}
          />

          <Endpoint
            method="PUT"
            path="/api/v1/white-label"
            description="Configure white-label branding for PDF reports. Upload your logo, set brand colors, and customize the footer text. Available on Scale and Enterprise plans."
            auth
            request={`curl -X PUT https://api.lintpdf.com/api/v1/white-label \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "logo_url": "https://yourcompany.com/logo.png",
    "primary_color": "#1a365d",
    "company_name": "Acme Print Co.",
    "footer_text": "Preflight report generated by Acme Print Co."
  }'`}
            response={`{
  "white_label": {
    "logo_url": "https://yourcompany.com/logo.png",
    "primary_color": "#1a365d",
    "company_name": "Acme Print Co.",
    "footer_text": "Preflight report generated by Acme Print Co.",
    "updated_at": "2026-03-15T10:30:00Z"
  }
}`}
          />

          <Endpoint
            method="GET"
            path="/api/v1/rulesets"
            description="List available Rulesets (preflight profiles). Includes built-in profiles and any custom profiles created by your account."
            auth={false}
            request={"curl https://api.lintpdf.com/api/v1/rulesets"}
            response={`{
  "rulesets": [
    {
      "id": "gwg-sheetfed",
      "name": "GWG Sheetfed",
      "description": "Ghent Workgroup sheetfed offset standard",
      "checks": 196,
      "is_builtin": true
    },
    {
      "id": "gwg-digital",
      "name": "GWG Digital",
      "description": "Ghent Workgroup digital printing standard",
      "checks": 180,
      "is_builtin": true
    },
    {
      "id": "pdfx4",
      "name": "PDF/X-4",
      "description": "ISO 15930-7 PDF/X-4 conformance",
      "checks": 120,
      "is_builtin": true
    },
    {
      "id": "packaging",
      "name": "Packaging",
      "description": "Packaging-specific checks including barcode grading",
      "checks": 210,
      "is_builtin": true
    }
  ]
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/rulesets"
            description="Create a custom Ruleset. Select which Checks to include and configure thresholds. Available on Growth plans and above."
            auth
            request={`curl -X POST https://api.lintpdf.com/api/v1/rulesets \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "My Custom Plan",
    "description": "Custom checks for magazine production",
    "base": "gwg-sheetfed",
    "overrides": {
      "image.min_dpi": 300,
      "barcode.min_grade": "C",
      "color.allow_spot": true
    }
  }'`}
            response={`{
  "id": "fp_custom_abc123",
  "name": "My Custom Plan",
  "description": "Custom checks for magazine production",
  "checks": 196,
  "is_builtin": false,
  "created_at": "2026-03-15T10:30:00Z"
}`}
          />
        </section>

        {/* ── Rulesets ── */}
        <section id="rulesets" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Rulesets</h2>
          <p className="text-slate-600 mb-6">
            A Ruleset is a preflight profile — a collection of Checks and
            thresholds that define what LintPDF checks for. Every submission
            requires a Ruleset.
          </p>

          <h3 className="font-semibold text-slate-900 mb-4">
            Built-in Rulesets
          </h3>
          <div className="overflow-x-auto mb-8">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Ruleset
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Standard
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Checks
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Use Case
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-slate-100">
                  <td className="py-2 px-3 font-medium text-slate-800">
                    GWG Sheetfed
                  </td>
                  <td className="py-2 px-3 text-slate-600">GWG 2022</td>
                  <td className="py-2 px-3 text-slate-600">196</td>
                  <td className="py-2 px-3 text-slate-600">
                    Commercial offset, sheetfed lithography
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2 px-3 font-medium text-slate-800">
                    GWG Digital
                  </td>
                  <td className="py-2 px-3 text-slate-600">GWG 2022</td>
                  <td className="py-2 px-3 text-slate-600">180</td>
                  <td className="py-2 px-3 text-slate-600">
                    Digital printing, wide-format, variable data
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2 px-3 font-medium text-slate-800">
                    PDF/X-4
                  </td>
                  <td className="py-2 px-3 text-slate-600">ISO 15930-7</td>
                  <td className="py-2 px-3 text-slate-600">120</td>
                  <td className="py-2 px-3 text-slate-600">
                    ISO exchange standard, transparency support
                  </td>
                </tr>
                <tr className="border-b border-slate-100">
                  <td className="py-2 px-3 font-medium text-slate-800">
                    Packaging
                  </td>
                  <td className="py-2 px-3 text-slate-600">ISO 15416</td>
                  <td className="py-2 px-3 text-slate-600">210</td>
                  <td className="py-2 px-3 text-slate-600">
                    Packaging, labels, barcode grading
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 className="font-semibold text-slate-900 mb-3">Custom Rulesets</h3>
          <p className="text-slate-600 mb-4">
            Growth, Scale, and Enterprise plans can create custom Rulesets.
            Start from a built-in base and override specific thresholds, enable
            or disable individual Checks, and name your profile for reuse across
            submissions.
          </p>
        </section>

        {/* ── Checks ── */}
        <section id="checks" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Checks Reference
          </h2>
          <p className="text-slate-600 mb-6">
            LintPDF runs 250+ individual Checks across these categories. Each
            finding in a Report references a Check ID, severity level, and
            affected page.
          </p>

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
            This is a representative sample. The full suite includes 250+
            checks. Use the{" "}
            <code className="bg-slate-100 px-1 rounded">
              GET /api/v1/rulesets
            </code>{" "}
            endpoint to see which Checks are included in each Ruleset.
          </p>
        </section>

        {/* ── Report Formats ── */}
        <section id="report-formats" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Report Formats
          </h2>
          <p className="text-slate-600 mb-6">
            Reports can be retrieved in three formats. Use the{" "}
            <code className="bg-slate-100 px-1 rounded text-sm font-mono">
              format
            </code>{" "}
            query parameter on the report endpoint.
          </p>

          <h3 className="font-semibold text-slate-900 mb-3">
            JSON Response Schema
          </h3>
          <CodeBlock>{`{
  "id": "string",
  "status": "complete",
  "verdict": "pass | error",
  "ruleset": "string",
  "file_name": "string",
  "page_count": "number",
  "duration_ms": "number",
  "summary": {
    "total_findings": "number",
    "error": "number",
    "warning": "number",
    "info": "number"
  },
  "findings": [
    {
      "inspection_id": "string",
      "severity": "error | warning | info",
      "message": "string",
      "page": "number"
    }
  ]
}`}</CodeBlock>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">
            PDF Reports &amp; White Label
          </h3>
          <p className="text-slate-600 mb-4">
            PDF reports are white-labeled using your White Label configuration.
            Scale and Enterprise plans can upload a logo, set brand colors, and
            customize footer text. Reports include a summary page, detailed
            findings grouped by severity, and page-level annotations.
          </p>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">XML Format</h3>
          <p className="text-slate-600 mb-4">
            XML reports follow the same structure as JSON but use XML elements.
            Useful for legacy integrations and enterprise systems that consume
            XML.
          </p>
          <CodeBlock>{`<?xml version="1.0" encoding="UTF-8"?>
<report id="f47ac10b-..." status="complete" verdict="error">
  <ruleset>gwg-sheetfed</ruleset>
  <file-name>document.pdf</file-name>
  <summary total="3" error="1" warning="1" info="1" />
  <findings>
    <finding inspection="font.not_embedded" severity="error" page="1">
      Font 'Helvetica' is not embedded
    </finding>
  </findings>
</report>`}</CodeBlock>
        </section>

        {/* ── Webhooks ── */}
        <section id="webhooks" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Webhooks</h2>
          <p className="text-slate-600 mb-6">
            Webhooks are webhook callbacks. Register an endpoint and LintPDF
            will POST event payloads when files finish processing. No polling
            required.
          </p>

          <h3 className="font-semibold text-slate-900 mb-3">
            Registering a Webhook
          </h3>
          <CodeBlock>{`curl -X POST https://api.lintpdf.com/api/v1/webhooks \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["job.complete", "job.error"]
  }'`}</CodeBlock>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">
            Event Types
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Event
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody>
                {[
                  [
                    "job.complete",
                    "File processing complete. Includes Report summary and findings.",
                  ],
                  [
                    "job.error",
                    "File has Error findings. Includes Report with critical issues.",
                  ],
                  ["job.pass", "File passed all Checks. Pass."],
                  [
                    "job.failed",
                    "Processing failed (corrupt file, timeout). Includes error message.",
                  ],
                  [
                    "usage.warning",
                    "Account reached 80% of monthly file limit.",
                  ],
                  [
                    "usage.cap_reached",
                    "Overage spending cap has been reached.",
                  ],
                ].map(([event, desc]) => (
                  <tr key={event} className="border-b border-slate-100">
                    <td className="py-2 px-3">
                      <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                        {event}
                      </code>
                    </td>
                    <td className="py-2 px-3 text-slate-600">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">
            Webhook Payload
          </h3>
          <CodeBlock>{`{
  "event": "job.complete",
  "timestamp": "2026-03-15T10:30:01Z",
  "data": {
    "id": "f47ac10b-...",
    "verdict": "error",
    "ruleset": "gwg-sheetfed",
    "file_name": "document.pdf",
    "summary": {
      "total_findings": 3,
      "error": 1,
      "warning": 1,
      "info": 1
    }
  }
}`}</CodeBlock>
        </section>

        {/* ── SDKs ── */}
        <section id="sdks" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            SDKs &amp; Code Examples
          </h2>
          <p className="text-slate-600 mb-8">
            LintPDF is a standard REST API — use any HTTP client. Here are
            examples in popular languages.
          </p>

          <h3 className="font-semibold text-slate-900 mb-3">Python</h3>
          <CodeBlock>{`import httpx

client = httpx.Client(
    base_url="https://api.lintpdf.com",
    headers={"Authorization": "Bearer lpdf_your_api_key"},
)

# Submit a PDF
with open("brochure.pdf", "rb") as f:
    resp = client.post("/api/v1/submit", files={"file": f}, data={"ruleset": "gwg-sheetfed"})
    job = resp.json()

print(f"Job ID: {job['id']}, Status: {job['status']}")

# Retrieve the Report
report = client.get(f"/api/v1/reports/{job['id']}").json()

if report["verdict"] == "pass":
    print("Pass!")
else:
    print(f"Error: {report['summary']['error']} Error findings")
    for finding in report["findings"]:
        print(f"  [{finding['severity']}] {finding['message']} (page {finding['page']})")`}</CodeBlock>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">Node.js</h3>
          <CodeBlock>{`import fs from "node:fs";

const API_BASE = "https://api.lintpdf.com";
const headers = { Authorization: "Bearer lpdf_your_api_key" };

// Submit a PDF
const form = new FormData();
form.append("file", new Blob([fs.readFileSync("brochure.pdf")]));
form.append("ruleset", "gwg-sheetfed");

const job = await fetch(\`\${API_BASE}/api/v1/submit\`, {
  method: "POST",
  headers,
  body: form,
}).then((r) => r.json());

console.log("Job ID:", job.id, "Status:", job.status);

// Retrieve the Report
const report = await fetch(\`\${API_BASE}/api/v1/reports/\${job.id}\`, {
  headers,
}).then((r) => r.json());

console.log("Verdict:", report.verdict);`}</CodeBlock>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">
            PHP / Laravel
          </h3>
          <CodeBlock>{`use Illuminate\\Support\\Facades\\Http;

$apiBase = 'https://api.lintpdf.com';
$headers = ['Authorization' => 'Bearer lpdf_your_api_key'];

// Submit a PDF
$response = Http::withHeaders($headers)
    ->attach('file', file_get_contents('brochure.pdf'), 'brochure.pdf')
    ->post("$apiBase/api/v1/submit", [
        'ruleset' => 'gwg-sheetfed',
    ]);

$job = $response->json();

// Retrieve the Report
$report = Http::withHeaders($headers)
    ->get("$apiBase/api/v1/reports/{$job['id']}")
    ->json();

if ($report['verdict'] === 'pass') {
    echo "Pass!";
} else {
    echo "Error: " . $report['summary']['error'] . " Error findings";
}`}</CodeBlock>
        </section>

        {/* ── Glossary ── */}
        <section id="glossary" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Glossary</h2>
          <p className="text-slate-600 mb-6">LintPDF terminology reference.</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Concept
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    LintPDF Term
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Used In
                  </th>
                </tr>
              </thead>
              <tbody>
                {glossary.map((item) => (
                  <tr key={item.term} className="border-b border-slate-100">
                    <td className="py-2 px-3 text-slate-600">{item.concept}</td>
                    <td className="py-2 px-3 font-medium text-slate-800">
                      {item.term}
                    </td>
                    <td className="py-2 px-3 text-slate-500">{item.usage}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ═══════════════════════════════════════════════════════════ */}
        {/* ── AI DOCUMENTATION ─────────────────────────────────────── */}
        {/* ═══════════════════════════════════════════════════════════ */}

        <div className="border-t-2 border-brand-200 pt-12 mb-16">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-3xl font-bold text-slate-900">
              AI-Powered Inspections
            </h2>
            <span className="rounded-full bg-brand-900 px-3 py-1 text-xs font-bold text-white">
              Invite-Only Alpha
            </span>
          </div>
          <p className="text-slate-500">
            32 AI inspections across 14 categories. Credit-based,
            detection-only, same Report format.
          </p>
        </div>

        {/* ── AI Getting Started ── */}
        <section id="ai-getting-started" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            AI Getting Started
          </h2>
          <p className="text-slate-600 mb-6">
            AI features are available as an invite-only alpha on all paid plans.
            Four steps to your first AI-powered Report:
          </p>

          <div className="grid gap-6 md:grid-cols-2 mb-8">
            <div className="rounded-xl border border-slate-200 p-5">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-sm font-bold mb-3">
                1
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">
                Request Access
              </h3>
              <p className="text-sm text-slate-500">
                Email{" "}
                <a
                  href="mailto:sales@lintpdf.com"
                  className="text-brand-600 hover:underline"
                >
                  sales@lintpdf.com
                </a>{" "}
                with your account ID and use case. We enable AI features
                individually during alpha.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 p-5">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-sm font-bold mb-3">
                2
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">
                Purchase Credits
              </h3>
              <p className="text-sm text-slate-500">
                Buy credits via pay-per-use ($0.12/credit) or volume packages
                starting at 100 credits for $10. Navigate to{" "}
                <strong>Settings &gt; AI Billing</strong> in Dashboard.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 p-5">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-sm font-bold mb-3">
                3
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">
                Configure Categories
              </h3>
              <p className="text-sm text-slate-500">
                Enable AI categories in{" "}
                <strong>Settings &gt; AI Inspections</strong>. Choose from
                barcode, content quality, regulatory, brand, and visual quality.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 p-5">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-brand-700 text-sm font-bold mb-3">
                4
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">
                Submit with AI
              </h3>
              <p className="text-sm text-slate-500">
                Add{" "}
                <code className="bg-slate-100 px-1 rounded text-xs">
                  ai_preset
                </code>{" "}
                or{" "}
                <code className="bg-slate-100 px-1 rounded text-xs">
                  ai_categories
                </code>{" "}
                to your Submit request.
              </p>
            </div>
          </div>

          <h3 className="font-semibold text-slate-900 mb-3">Quick example</h3>
          <CodeBlock>{`# Submit a PDF with FDA AI preset
curl -X POST https://api.lintpdf.com/api/v1/submit \\
  -H "Authorization: Bearer lpdf_your_api_key" \\
  -F file=@food-label.pdf \\
  -F ruleset=packaging \\
  -F ai_preset=fda-food

# Report includes both core engine and AI findings
curl https://api.lintpdf.com/api/v1/reports/f47ac10b-... \\
  -H "Authorization: Bearer lpdf_your_api_key"

# Check your credit balance
curl https://api.lintpdf.com/api/v1/ai/credits \\
  -H "Authorization: Bearer lpdf_your_api_key"`}</CodeBlock>
        </section>

        {/* ── AI Configuration ── */}
        <section id="ai-configuration" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            AI Configuration
          </h2>
          <p className="text-slate-600 mb-6">
            AI features are configured at three levels: account defaults,
            Ruleset settings, and per-request overrides.
          </p>

          <h3 className="font-semibold text-slate-900 mb-4">
            Account-Level Settings
          </h3>
          <p className="text-slate-600 mb-4">
            In <strong>Settings &gt; AI Inspections</strong>, enable or disable
            entire AI categories. These serve as defaults for all submissions.
          </p>

          <div className="overflow-x-auto mb-8">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Category
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Inspections
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Tier
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Description
                  </th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    cat: "barcode",
                    count: 7,
                    tier: "Text",
                    desc: "Barcode detection, decode, validation",
                  },
                  {
                    cat: "content_quality",
                    count: 3,
                    tier: "Text",
                    desc: "Spell check, language, duplicates",
                  },
                  {
                    cat: "color_compliance",
                    count: 2,
                    tier: "Text",
                    desc: "Brand palette, contrast ratio",
                  },
                  {
                    cat: "regulatory_fda",
                    count: 5,
                    tier: "Vision",
                    desc: "FDA Nutrition Facts (21 CFR 101.9)",
                  },
                  {
                    cat: "regulatory_eu",
                    count: 4,
                    tier: "Vision",
                    desc: "EU Food Information (1169/2011)",
                  },
                  {
                    cat: "regulatory_ghs",
                    count: 5,
                    tier: "Vision",
                    desc: "GHS/CLP Chemical Labels (1272/2008)",
                  },
                  {
                    cat: "regulatory_pharma",
                    count: 3,
                    tier: "Vision",
                    desc: "Pharmaceutical Packaging (EU FMD)",
                  },
                  {
                    cat: "brand",
                    count: 2,
                    tier: "Mixed",
                    desc: "Logo matching, palette compliance",
                  },
                  {
                    cat: "visual_quality",
                    count: 2,
                    tier: "Vision",
                    desc: "Image quality, NSFW screening",
                  },
                ].map(({ cat, count, tier, desc }) => (
                  <tr key={cat} className="border-b border-slate-100">
                    <td className="py-2 px-3">
                      <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                        {cat}
                      </code>
                    </td>
                    <td className="py-2 px-3 text-slate-600">{count}</td>
                    <td className="py-2 px-3">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          tier === "Vision"
                            ? "bg-purple-500/10 text-purple-600 border border-purple-500/20"
                            : tier === "Mixed"
                              ? "bg-amber-500/10 text-amber-600 border border-amber-500/20"
                              : "bg-slate-100 text-slate-600 border border-slate-200"
                        }`}
                      >
                        {tier}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-600">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="font-semibold text-slate-900 mb-3">
            Brand Configuration
          </h3>
          <p className="text-slate-600 mb-4">
            For brand-related AI inspections, configure your assets in{" "}
            <strong>Settings &gt; AI Brand</strong>:
          </p>
          <ul className="list-disc list-inside space-y-2 text-sm text-slate-600 mb-6">
            <li>
              <strong>Color Palette</strong> — Add approved brand colors as hex
              values with Delta E tolerance
            </li>
            <li>
              <strong>Reference Logos</strong> — Upload logo variations
              (horizontal, stacked, icon-only, reversed)
            </li>
            <li>
              <strong>Custom Dictionary</strong> — Add brand names, product
              names, and technical terms for spell checking
            </li>
          </ul>

          <h3 className="font-semibold text-slate-900 mb-3">
            Confidence Threshold
          </h3>
          <p className="text-slate-600 mb-4">
            Set the minimum confidence score for AI findings in{" "}
            <strong>Settings &gt; AI Inspections</strong>. Default is 0.75. Only
            findings above this threshold appear in your Report.
          </p>
        </section>

        {/* ── AI Credits ── */}
        <section id="ai-credits" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">AI Credits</h2>
          <p className="text-slate-600 mb-6">
            Core preflight checks are unlimited on paid plans. AI inspections
            consume credits — 1 credit for Text-tier, 2 credits for Vision-tier.
          </p>

          <h3 className="font-semibold text-slate-900 mb-4">Pricing</h3>
          <div className="overflow-x-auto mb-8">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Option
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Credits
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Price
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Per Credit
                  </th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    option: "Pay-per-use",
                    credits: "Any",
                    price: "Metered",
                    per: "$0.12",
                  },
                  {
                    option: "Starter Package",
                    credits: "100",
                    price: "$10",
                    per: "$0.10",
                  },
                  {
                    option: "Growth Package",
                    credits: "500",
                    price: "$40",
                    per: "$0.08",
                  },
                  {
                    option: "Scale Package",
                    credits: "2,000",
                    price: "$120",
                    per: "$0.06",
                  },
                  {
                    option: "Enterprise Package",
                    credits: "10,000",
                    price: "$500",
                    per: "$0.05",
                  },
                ].map(({ option, credits, price, per }) => (
                  <tr key={option} className="border-b border-slate-100">
                    <td className="py-2 px-3 font-medium text-slate-800">
                      {option}
                    </td>
                    <td className="py-2 px-3 text-slate-600">{credits}</td>
                    <td className="py-2 px-3 text-slate-600">{price}</td>
                    <td className="py-2 px-3 text-brand-600 font-medium">
                      {per}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="font-semibold text-slate-900 mb-3">
            Checking Balance
          </h3>
          <CodeBlock>{`curl https://api.lintpdf.com/api/v1/ai/credits \\
  -H "Authorization: Bearer lpdf_..."

# Response
{
  "balance": 4250,
  "billing_mode": "package",
  "auto_topup": false,
  "consumed_this_month": 750,
  "consumed_total": 3250
}`}</CodeBlock>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">
            Auto Top-up
          </h3>
          <CodeBlock>{`curl -X PUT https://api.lintpdf.com/api/v1/ai/credits/auto-topup \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "enabled": true,
    "threshold": 100,
    "package": "starter"
  }'`}</CodeBlock>

          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm text-amber-800">
              <span className="font-semibold">When credits run out:</span> AI
              inspections are skipped, not queued. Core engine checks continue
              normally. The Report includes an info note indicating which AI
              inspections were skipped.
            </p>
          </div>
        </section>

        {/* ── AI Inspections Reference ── */}
        <section id="ai-inspections" className="mb-16 scroll-mt-24">
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
              category: "Regulatory — FDA",
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
              category: "Regulatory — EU",
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
              category: "Regulatory — GHS/CLP",
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
              category: "Regulatory — Pharma",
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
                  desc: "AI visual quality assessment — blur, noise, upscaling detection",
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
        </section>

        {/* ── AI Presets ── */}
        <section id="ai-presets" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">AI Presets</h2>
          <p className="text-slate-600 mb-6">
            Pre-built collections of AI inspections for common use cases. Use a
            preset ID in your Submit request to run a curated set of AI
            inspections.
          </p>

          <div className="overflow-x-auto mb-8">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Preset
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    ID
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Inspections
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Categories
                  </th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    name: "FDA Food",
                    id: "fda-food",
                    count: 12,
                    cats: "barcode, content_quality, regulatory_fda",
                  },
                  {
                    name: "EU Food",
                    id: "eu-food",
                    count: 10,
                    cats: "barcode, content_quality, regulatory_eu",
                  },
                  {
                    name: "Pharma EU",
                    id: "pharma-eu",
                    count: 9,
                    cats: "barcode, regulatory_pharma, visual_quality",
                  },
                  {
                    name: "GHS Chemical",
                    id: "ghs-chemical",
                    count: 12,
                    cats: "barcode, content_quality, regulatory_ghs",
                  },
                  {
                    name: "Packaging QC",
                    id: "packaging-qc",
                    count: 14,
                    cats: "barcode, content_quality, color_compliance, visual_quality",
                  },
                  {
                    name: "Brand Compliance",
                    id: "brand-compliance",
                    count: 7,
                    cats: "brand, color_compliance, content_quality",
                  },
                  {
                    name: "Full AI Scan",
                    id: "full-ai",
                    count: 33,
                    cats: "All categories",
                  },
                ].map(({ name, id, count, cats }) => (
                  <tr key={id} className="border-b border-slate-100">
                    <td className="py-2 px-3 font-medium text-slate-800">
                      {name}
                    </td>
                    <td className="py-2 px-3">
                      <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                        {id}
                      </code>
                    </td>
                    <td className="py-2 px-3 text-slate-600">{count}</td>
                    <td className="py-2 px-3 text-slate-600">{cats}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="font-semibold text-slate-900 mb-3">
            Listing Presets via API
          </h3>
          <CodeBlock>{`curl https://api.lintpdf.com/api/v1/ai/presets \\
  -H "Authorization: Bearer lpdf_..."

# Response
{
  "presets": [
    {
      "id": "fda-food",
      "name": "FDA Food",
      "inspections": 12,
      "categories": ["barcode", "content_quality", "regulatory_fda"],
      "tier": "gpu"
    },
    ...
  ]
}`}</CodeBlock>
        </section>

        {/* ── AI Regulatory Compliance ── */}
        <section id="ai-regulatory" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Regulatory Compliance Guide
          </h2>
          <p className="text-slate-600 mb-6">
            LintPDF validates packaging artwork against four regulatory
            frameworks. See the{" "}
            <a href="/compliance" className="text-brand-600 hover:underline">
              full compliance page
            </a>{" "}
            for detailed check lists and example findings.
          </p>

          <div className="grid gap-6 md:grid-cols-2 mb-8">
            {[
              {
                name: "FDA Nutrition Facts",
                standard: "21 CFR 101.9",
                inspections: 5,
                desc: "Nutrition panel structure, nutrient ordering, font sizes, serving size, Daily Value formatting.",
              },
              {
                name: "EU Food Information",
                standard: "Regulation 1169/2011",
                inspections: 4,
                desc: "x-height validation, allergen emphasis, nutritional declaration order, mandatory fields.",
              },
              {
                name: "GHS/CLP Chemical",
                standard: "Regulation 1272/2008",
                inspections: 5,
                desc: "Pictogram detection and sizing, signal words, H/P statement validation.",
              },
              {
                name: "Pharma Packaging",
                standard: "EU FMD (2011/62/EU)",
                inspections: 3,
                desc: "Serialization area, Braille placeholder, font compliance for patient information.",
              },
            ].map(({ name, standard, inspections, desc }) => (
              <div
                key={name}
                className="rounded-xl border border-slate-200 p-5"
              >
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold text-slate-900">{name}</h3>
                  <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {standard}
                  </span>
                </div>
                <p className="text-sm text-slate-500 mb-2">{desc}</p>
                <p className="text-xs text-slate-400">
                  {inspections} AI inspections &middot; Vision tier
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* ── AI API Reference ── */}
        <section id="ai-api" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            AI API Reference
          </h2>
          <p className="text-slate-500 text-sm mb-8">
            All AI endpoints require a valid API Key and AI features enabled on
            your account.
          </p>

          <Endpoint
            method="POST"
            path="/api/v1/submit"
            description="Submit a file with AI inspections. Include ai_preset or ai_categories alongside your standard Submit parameters."
            auth
            request={`curl -X POST https://api.lintpdf.com/api/v1/submit \\
  -H "Authorization: Bearer lpdf_..." \\
  -F file=@label.pdf \\
  -F ruleset=packaging \\
  -F ai_preset=fda-food

# Or specify categories directly:
curl -X POST https://api.lintpdf.com/api/v1/submit \\
  -H "Authorization: Bearer lpdf_..." \\
  -F file=@label.pdf \\
  -F ruleset=packaging \\
  -F ai_categories=barcode,regulatory_fda,content_quality`}
            response={`{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "processing",
  "ruleset": "packaging",
  "ai_preset": "fda-food",
  "ai_inspections_requested": 12,
  "file_name": "label.pdf",
  "created_at": "2026-03-16T10:30:00Z"
}`}
          />

          <Endpoint
            method="GET"
            path="/api/v1/ai/credits"
            description="Retrieve your current AI credit balance, billing mode, and consumption statistics."
            auth
            request={`curl https://api.lintpdf.com/api/v1/ai/credits \\
  -H "Authorization: Bearer lpdf_..."`}
            response={`{
  "balance": 4250,
  "billing_mode": "package",
  "auto_topup": false,
  "consumed_this_month": 750,
  "consumed_total": 3250
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/ai/credits/topup"
            description="Purchase a credit package. Available packages: starter (1,000), growth (5,000), scale (25,000)."
            auth
            request={`curl -X POST https://api.lintpdf.com/api/v1/ai/credits/topup \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{"package": "starter"}'`}
            response={`{
  "balance": 5250,
  "package_purchased": "starter",
  "credits_added": 1000,
  "amount_charged": "$50.00"
}`}
          />

          <Endpoint
            method="PUT"
            path="/api/v1/ai/credits/auto-topup"
            description="Configure automatic credit top-up. When balance drops below threshold, the specified package is purchased automatically."
            auth
            request={`curl -X PUT https://api.lintpdf.com/api/v1/ai/credits/auto-topup \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "enabled": true,
    "threshold": 100,
    "package": "starter"
  }'`}
            response={`{
  "auto_topup": {
    "enabled": true,
    "threshold": 100,
    "package": "starter"
  }
}`}
          />

          <Endpoint
            method="GET"
            path="/api/v1/ai/presets"
            description="List all available AI presets with their included categories and inspection counts."
            auth
            request={`curl https://api.lintpdf.com/api/v1/ai/presets \\
  -H "Authorization: Bearer lpdf_..."`}
            response={`{
  "presets": [
    {
      "id": "fda-food",
      "name": "FDA Food",
      "inspections": 12,
      "categories": ["barcode", "content_quality", "regulatory_fda"],
      "tier": "gpu"
    },
    {
      "id": "full-ai",
      "name": "Full AI Scan",
      "inspections": 33,
      "categories": ["all"],
      "tier": "gpu"
    }
  ]
}`}
          />

          <Endpoint
            method="PUT"
            path="/api/v1/ai/brand/palette"
            description="Configure your brand color palette for the ai.color.brand_palette inspection. Set approved colors and Delta E tolerance."
            auth
            request={`curl -X PUT https://api.lintpdf.com/api/v1/ai/brand/palette \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "colors": [
      {"hex": "#1a365d", "name": "Primary Navy"},
      {"hex": "#3b6fb5", "name": "Secondary Blue"},
      {"hex": "#e2a832", "name": "Accent Gold"}
    ],
    "tolerance": 5
  }'`}
            response={`{
  "palette": {
    "colors": [
      {"hex": "#1a365d", "name": "Primary Navy"},
      {"hex": "#3b6fb5", "name": "Secondary Blue"},
      {"hex": "#e2a832", "name": "Accent Gold"}
    ],
    "tolerance": 5,
    "updated_at": "2026-03-16T10:30:00Z"
  }
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/ai/brand/logos"
            description="Upload a reference logo for the ai.brand.logo_match inspection. Supports PNG, SVG, PDF, EPS."
            auth
            request={`curl -X POST https://api.lintpdf.com/api/v1/ai/brand/logos \\
  -H "Authorization: Bearer lpdf_..." \\
  -F file=@logo-horizontal.png \\
  -F name="Horizontal Logo" \\
  -F variant="horizontal"`}
            response={`{
  "logo": {
    "id": "logo_abc123",
    "name": "Horizontal Logo",
    "variant": "horizontal",
    "file_type": "image/png",
    "created_at": "2026-03-16T10:30:00Z"
  }
}`}
          />

          <Endpoint
            method="PUT"
            path="/api/v1/ai/brand/dictionary"
            description="Manage the custom dictionary for ai.content.spell_check. Use mode 'append' to add words or 'replace' to overwrite."
            auth
            request={`curl -X PUT https://api.lintpdf.com/api/v1/ai/brand/dictionary \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "words": ["LintPDF", "PreflightPro", "XtraShield"],
    "mode": "append"
  }'`}
            response={`{
  "dictionary": {
    "word_count": 47,
    "mode": "append",
    "words_added": 3,
    "updated_at": "2026-03-16T10:30:00Z"
  }
}`}
          />
        </section>

        {/* ── AI Errors ── */}
        <section id="ai-errors" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            AI Error Reference
          </h2>
          <p className="text-slate-600 mb-6">
            AI-specific error codes that may appear in API responses or Report
            info notes.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b-2 border-slate-200">
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Error Code
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Description
                  </th>
                  <th className="text-left py-2 px-3 text-slate-500 font-medium">
                    Resolution
                  </th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    code: "ai.credits.insufficient",
                    desc: "Credit balance is zero or insufficient for requested inspections",
                    fix: "Purchase credits or enable auto top-up",
                  },
                  {
                    code: "ai.credits.depleted",
                    desc: "Credits ran out during processing — some inspections were skipped",
                    fix: "Top up credits; skipped inspections noted in Report",
                  },
                  {
                    code: "ai.circuit_breaker.open",
                    desc: "Vision capacity constrained — Vision inspections temporarily unavailable",
                    fix: "Retry in a few minutes; Text inspections unaffected",
                  },
                  {
                    code: "ai.category.disabled",
                    desc: "Requested AI category is not enabled on this account",
                    fix: "Enable the category in Settings > AI Inspections",
                  },
                  {
                    code: "ai.not_enabled",
                    desc: "AI features are not enabled on this account",
                    fix: "Request access via sales@lintpdf.com",
                  },
                  {
                    code: "ai.preset.not_found",
                    desc: "The specified AI preset ID does not exist",
                    fix: "Use GET /api/v1/ai/presets to list valid presets",
                  },
                  {
                    code: "ai.file.too_large",
                    desc: "File exceeds 100MB limit for AI processing",
                    fix: "Reduce file size; core engine checks still run",
                  },
                  {
                    code: "ai.rasterization.failed",
                    desc: "Page could not be rasterized for vision-based inspection",
                    fix: "Check for encryption, malformed structure, or unsupported features",
                  },
                  {
                    code: "ai.brand.no_palette",
                    desc: "Brand palette inspection requested but no palette configured",
                    fix: "Configure brand palette in Settings > AI Brand",
                  },
                  {
                    code: "ai.brand.no_logos",
                    desc: "Logo matching requested but no reference logos uploaded",
                    fix: "Upload reference logos in Settings > AI Brand",
                  },
                  {
                    code: "ai.model.timeout",
                    desc: "AI model processing exceeded timeout threshold",
                    fix: "Retry; if persistent, contact support",
                  },
                ].map(({ code, desc, fix }) => (
                  <tr key={code} className="border-b border-slate-100">
                    <td className="py-2 px-3">
                      <code className="text-xs font-mono text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                        {code}
                      </code>
                    </td>
                    <td className="py-2 px-3 text-slate-600">{desc}</td>
                    <td className="py-2 px-3 text-slate-600">{fix}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── AI Code Examples ── */}
        <section id="ai-examples" className="mb-16 scroll-mt-24">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            AI Code Examples
          </h2>
          <p className="text-slate-600 mb-8">
            Examples showing how to enable AI inspections in job submissions
            across different languages.
          </p>

          <h3 className="font-semibold text-slate-900 mb-3">
            Python — FDA Food Label Check
          </h3>
          <CodeBlock>{`import httpx

client = httpx.Client(
    base_url="https://api.lintpdf.com",
    headers={"Authorization": "Bearer lpdf_your_api_key"},
)

# Submit with FDA AI preset
with open("nutrition-label.pdf", "rb") as f:
    resp = client.post(
        "/api/v1/submit",
        files={"file": f},
        data={
            "ruleset": "packaging",
            "ai_preset": "fda-food",
        },
    )
    job = resp.json()

print(f"Job ID: {job['id']}")

# Retrieve Report
report = client.get(f"/api/v1/reports/{job['id']}").json()

# Separate core and AI findings
engine_findings = [f for f in report["findings"] if f.get("source") != "ai"]
ai_findings = [f for f in report["findings"] if f.get("source") == "ai"]

print(f"Core engine: {len(engine_findings)} findings")
print(f"AI: {len(ai_findings)} findings")

for finding in ai_findings:
    print(f"  [{finding['severity']}] {finding['message']}")
    print(f"    Confidence: {finding.get('confidence', 'N/A')}")
    print(f"    Credits: {finding.get('credits_consumed', 'N/A')}")`}</CodeBlock>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">
            Node.js — GHS Chemical Label Check
          </h3>
          <CodeBlock>{`import fs from "node:fs";

const API_BASE = "https://api.lintpdf.com";
const headers = { Authorization: "Bearer lpdf_your_api_key" };

// Check credit balance first
const credits = await fetch(\`\${API_BASE}/api/v1/ai/credits\`, { headers })
  .then((r) => r.json());

console.log("Credit balance:", credits.balance);

if (credits.balance < 20) {
  console.warn("Low credit balance — consider topping up");
}

// Submit with GHS preset
const form = new FormData();
form.append("file", new Blob([fs.readFileSync("chemical-label.pdf")]));
form.append("ruleset", "packaging");
form.append("ai_preset", "ghs-chemical");

const job = await fetch(\`\${API_BASE}/api/v1/submit\`, {
  method: "POST",
  headers,
  body: form,
}).then((r) => r.json());

console.log("Job:", job.id, "AI inspections:", job.ai_inspections_requested);

// Retrieve Report
const report = await fetch(\`\${API_BASE}/api/v1/reports/\${job.id}\`, {
  headers,
}).then((r) => r.json());

// Filter by regulatory findings
const ghsFindings = report.findings.filter(
  (f) => f.category === "regulatory.ghs"
);

console.log("GHS findings:", ghsFindings.length);
ghsFindings.forEach((f) => console.log(\`  [\${f.severity}] \${f.message}\`));`}</CodeBlock>

          <h3 className="font-semibold text-slate-900 mt-8 mb-3">
            PHP / Laravel — Brand Compliance Check
          </h3>
          <CodeBlock>{`use Illuminate\\Support\\Facades\\Http;

$apiBase = 'https://api.lintpdf.com';
$headers = ['Authorization' => 'Bearer lpdf_your_api_key'];

// Submit with brand compliance preset
$response = Http::withHeaders($headers)
    ->attach('file', file_get_contents('packaging-artwork.pdf'), 'packaging-artwork.pdf')
    ->post("$apiBase/api/v1/submit", [
        'ruleset' => 'packaging',
        'ai_preset' => 'brand-compliance',
    ]);

$job = $response->json();

// Retrieve Report
$report = Http::withHeaders($headers)
    ->get("$apiBase/api/v1/reports/{$job['id']}")
    ->json();

// Filter AI findings by brand category
$brandFindings = collect($report['findings'])
    ->filter(fn($f) => str_starts_with($f['category'] ?? '', 'brand'))
    ->values();

foreach ($brandFindings as $finding) {
    echo "[{$finding['severity']}] {$finding['message']}\\n";
    echo "  Confidence: {$finding['confidence']}\\n";
}`}</CodeBlock>
        </section>
      </main>
    </div>
  );
}
