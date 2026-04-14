import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiReportsSection() {
  return (
    <section className="mb-12">
      <h3 id="reports" className="text-xl font-bold text-slate-900 mb-3">
        Reports &amp; share links
      </h3>
      <p className="text-slate-600 mb-4">
        Reports are immutable artifacts minted from a complete job. Each report
        carries its own token for unauthenticated access and freezes its
        branding at mint time — flipping the tenant default later does not
        retroactively rebrand existing share links.
      </p>

      <Endpoint
        method="POST"
        path="/api/v1/jobs/{job_id}/reports"
        description="Mint one or more reports for a completed job. Returns 201 on success, 403 if any requested format or the branding override exceeds the tenant's plan."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-.../reports \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "formats": ["pdf", "html"],
    "expiry_days": 14,
    "email_to": "printer@acme.com",
    "branding": {
      "name": "Acme Print",
      "logo_url": "https://acmeprint.com/logo.svg",
      "primary_color": "#1a365d",
      "accent_color": "#2563eb",
      "hide_footer": false
    },
    "detail_level": "comprehensive",
    "summary_page": "prepend"
  }'`}
        response={`{
  "reports": [
    { "format": "pdf",  "token": "rpt_01HXY...", "expires_at": "2026-04-26T10:30:00Z",
      "url": "https://reports.lintpdf.com/r/rpt_01HXY....pdf" },
    { "format": "html", "token": "rpt_01HXZ...", "expires_at": "2026-04-26T10:30:00Z",
      "url": "https://reports.lintpdf.com/r/rpt_01HXZ..." }
  ]
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Generate-reports request fields</h4>
      <FieldTable
        rows={[
          { name: "formats", type: '("html" | "pdf" | "json" | "xml" | "annotated_pdf" | "annotated_pdf_markup")[]', default: '["html","pdf"]', description: "Output formats to mint. Formats not in your plan return 403. annotated_pdf_markup stamps reviewer markup (annotations + comment threads) and an appendix onto the original PDF; it is silently skipped when the job has no annotations." },
          { name: "expiry_days", type: "integer | null", default: "tenant / plan default (typically 7)", description: "Token lifetime in days. Null defers to the tenant setting or plan limit." },
          { name: "email_to", type: "string | null", description: "Single email address to deliver the report URLs to." },
          { name: "branding", type: "BrandingOverride | null", description: "Per-call branding override. Object with name/logo_url/primary_color/accent_color/hide_footer fields (each optional). Requires the white-label entitlement." },
          { name: "detail_level", type: '"executive" | "standard" | "comprehensive"', default: '"standard"', description: "Narrative density of the generated PDF/HTML report." },
          { name: "summary_page", type: '"prepend" | "only" | "off" | null', default: '"prepend" (or tenant override)', description: "Where the executive summary page lands in the PDF." },
        ]}
      />
      <p className="text-slate-600 text-sm mt-2">
        For a job-submit-time brand override using the three-way enum
        ({`"anonymous" | "lintpdf" | uuid`}) use the <code className="bg-slate-100 px-1 rounded">brand</code> field
        on <code className="bg-slate-100 px-1 rounded">POST /api/v1/jobs</code>. The reports endpoint takes the
        richer <code className="bg-slate-100 px-1 rounded">BrandingOverride</code> object form so per-report
        tweaks (logo URL, hide footer, etc.) survive.
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/jobs/{job_id}/reports"
        description="List existing report tokens for a job."
        auth
        request={`curl https://api.lintpdf.com/api/v1/jobs/.../reports \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "reports": [
    {
      "token": "rpt_01HXY...",
      "format": "pdf",
      "expires_at": "2026-04-26T10:30:00Z",
      "created_at": "2026-04-12T10:30:00Z",
      "accessed_count": 3
    }
  ]
}`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/jobs/{job_id}/reports/{token}"
        description="Revoke a specific report token and delete the stored file. Public URLs immediately return 410 Gone / 404. Returns 204 on success."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/jobs/.../reports/rpt_01HXY... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`HTTP/1.1 204 No Content`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Public (token-gated) surfaces</h4>
      <p className="text-slate-600 mb-3">
        The following endpoints require no authentication. Access is gated by
        possession of the token alone — treat them like signed URLs.
      </p>
      <Endpoint
        method="GET"
        path="/r/{token}"
        description="HTML landing page for a report. Anonymous reports omit all LintPDF branding."
        auth={false}
        request={`curl https://reports.lintpdf.com/r/rpt_01HXY...`}
        response={`200 OK
Content-Type: text/html`}
      />
      <Endpoint
        method="GET"
        path="/r/{token}.pdf?download=1"
        description='Direct download of the PDF report. download=1 sets Content-Disposition: attachment. Filename is "report.pdf" for normal reports and a neutral "preflight-<short-id>.pdf" for anonymous reports.'
        auth={false}
        request={`curl -o report.pdf https://reports.lintpdf.com/r/rpt_01HXY....pdf?download=1`}
        response={`200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="report.pdf"`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/reports/tokens/{token}"
        description="Token metadata used by the plugin proxy to validate public viewer access. Returns 404 on unknown tokens and 410 Gone on expired tokens."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/reports/tokens/rpt_01HXY...`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "tenant_id": "...",
  "file_name": "brochure.pdf",
  "email_required": true
}`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/reports/tokens/{token}/findings"
        description="Structured findings payload for a share link. Mirrors the findings array on GET /jobs/{id} but authenticated by token."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/reports/tokens/rpt_01HXY.../findings`}
        response={`{
  "findings": [
    {
      "inspection_id": "font.not_embedded",
      "severity": "error",
      "message": "Font 'Helvetica' is not embedded",
      "page_num": 1,
      "details": null,
      "source": "engine",
      "category": "fonts",
      "bbox": [72.0, 720.0, 540.0, 740.0],
      "object_id": "Font12",
      "object_type": "font"
    }
  ]
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Public viewer surfaces</h4>
      <p className="text-slate-600 mb-3">
        Every authenticated viewer route has an unauthenticated parallel
        rooted at <code className="bg-slate-100 px-1 rounded">{`/api/v1/viewer/public/{token}/*`}</code>. The token
        carries the frozen brand, so <code className="bg-slate-100 px-1 rounded">GET .../config</code> emits
        the same branding block regardless of later tenant setting changes.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/public/{token}/pages"
        description="Public page list for a token-scoped viewer session. Same shape as the authenticated endpoint."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/viewer/public/rpt_01HXY.../pages`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "page_count": 1,
  "pages": [ { "page_num": 1, "width_pts": 595.28, "height_pts": 841.89, ... } ]
}`}
      />
      <p className="text-slate-500 text-sm mt-4">
        Parallel public routes exist for: <code className="bg-slate-100 px-1 rounded">tile</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">info</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">separations</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">channel</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">tac-heatmap</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">sample</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">layers</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">config</code>, and
        {" "}<code className="bg-slate-100 px-1 rounded">verdict</code> (read-only GET).
      </p>
    </section>
  );
}
