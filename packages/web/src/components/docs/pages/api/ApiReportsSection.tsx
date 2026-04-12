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
        description="Mint one or more reports for a completed job."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-.../reports \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "formats": ["pdf", "html", "json"],
    "expiry_days": 14,
    "email_to": ["printer@acme.com"],
    "branding": "anonymous",
    "detail_level": "comprehensive",
    "summary_page": "prepend"
  }'`}
        response={`{
  "tokens": [
    { "format": "pdf",  "token": "rpt_01HXY...", "expires_at": "2026-04-26T10:30:00Z",
      "url": "https://reports.lintpdf.com/r/rpt_01HXY....pdf" },
    { "format": "html", "token": "rpt_01HXZ...", "expires_at": "2026-04-26T10:30:00Z",
      "url": "https://reports.lintpdf.com/r/rpt_01HXZ..." }
  ]
}`}
      />

      <FieldTable
        rows={[
          { name: "formats", type: '("pdf"|"html"|"json"|"xml")[]', required: true, description: "One or more output formats to mint." },
          { name: "expiry_days", type: "integer", default: "30", description: "Token lifetime in days. Range 1–365." },
          { name: "email_to", type: "string[]", description: "Deliver the report URLs to these addresses." },
          { name: "branding", type: '"anonymous" | "lintpdf" | uuid', description: "Freeze branding for this report. Overrides the tenant default at mint time." },
          { name: "detail_level", type: '"executive"|"standard"|"comprehensive"', default: "standard", description: "Narrative density of the generated PDF/HTML report." },
          { name: "summary_page", type: '"prepend"|"only"|"off"', default: "prepend", description: "Where the executive summary page lands in the PDF." },
        ]}
      />

      <Endpoint
        method="GET"
        path="/api/v1/jobs/{job_id}/reports"
        description="List existing report tokens for a job."
        auth
        request={`curl https://api.lintpdf.com/api/v1/jobs/.../reports \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "reports": [
    { "token": "rpt_01HXY...", "format": "pdf", "brand_mode": "anonymous", "expires_at": "..." }
  ]
}`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/jobs/{job_id}/reports/{token}"
        description="Revoke a specific report token. Public URLs immediately return 410 Gone."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/jobs/.../reports/rpt_01HXY... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "revoked": true, "token": "rpt_01HXY..." }`}
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
        description="Direct download of the PDF report. download=1 sets Content-Disposition: attachment."
        auth={false}
        request={`curl -o report.pdf https://reports.lintpdf.com/r/rpt_01HXY....pdf?download=1`}
        response={`200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename=preflight-01HXY.pdf`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/reports/tokens/{token}"
        description="Token metadata: job reference, brand mode, expiry, revocation state."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/reports/tokens/rpt_01HXY...`}
        response={`{
  "token": "rpt_01HXY...",
  "job_id": "d4e5f6a7-...",
  "brand_mode": "anonymous",
  "expires_at": "2026-04-26T10:30:00Z",
  "revoked": false
}`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/reports/tokens/{token}/findings"
        description="Structured findings payload for a share link. Mirrors GET /jobs/{id} but token-gated."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/reports/tokens/rpt_01HXY.../findings`}
        response={`{ "summary": { ... }, "findings": [ { ... } ] }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Public viewer surfaces</h4>
      <p className="text-slate-600 mb-3">
        Every authenticated viewer route has an unauthenticated parallel
        rooted at <code className="bg-slate-100 px-1 rounded">/api/v1/viewer/public/{`{token}`}/*</code>. The token
        carries the frozen brand, so <code className="bg-slate-100 px-1 rounded">GET .../config</code> emits
        the same branding block regardless of later tenant setting changes.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/viewer/public/{token}/pages"
        description="Public page list for a token-scoped viewer session."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/viewer/public/rpt_01HXY.../pages`}
        response={`{ "pages": [ { "page_num": 1, "width_pt": 595.28, "height_pt": 841.89 } ] }`}
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
        {" "}<code className="bg-slate-100 px-1 rounded">verdict</code>.
      </p>
    </section>
  );
}
