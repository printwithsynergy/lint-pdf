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
        description="Mint one or more reports for a completed job. Returns 201 on success, 403 if any requested format or the branding override exceeds the tenant's plan. Supports an optional Idempotency-Key header; repeated requests with the same key converge on the same token and reuse the stored artifact instead of regenerating it."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-.../reports \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -H "Idempotency-Key: invoice-42-2026-04-17" \\
  -d '{
    "formats": [
      { "format": "json", "return": "inline" },
      { "format": "annotated_pdf", "return": "url" },
      "html"
    ],
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
    { "format": "json", "url": null, "token": null, "expires_at": null,
      "data": { "summary": { "error_count": 2 }, "findings": [ ... ] },
      "content_type": "application/json" },
    { "format": "annotated_pdf", "token": "rpt_01HXY...",
      "expires_at": "2026-04-26T10:30:00Z",
      "url": "https://reports.lintpdf.com/r/rpt_01HXY....pdf",
      "data": null, "content_type": null },
    { "format": "html", "token": "rpt_01HXZ...",
      "expires_at": "2026-04-26T10:30:00Z",
      "url": "https://reports.lintpdf.com/r/rpt_01HXZ...",
      "data": null, "content_type": null }
  ]
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Generate-reports request fields</h4>
      <FieldTable
        rows={[
          { name: "formats", type: '(FormatName | { format: FormatName; return?: "url" | "inline" | "both" })[]', default: '["html","pdf"]', description: "Output formats to mint. Each entry is either a bare format string (back-compat; equivalent to return=\"url\") or an object selecting the return mode. Inline returns embed the payload in the response body and are supported only for json and xml; requesting inline on a binary format (pdf, annotated_pdf, annotated_pdf_markup, html) returns 422. Formats not in your plan return 403." },
          { name: "expiry_days", type: "integer | null", default: "tenant / plan default (typically 7)", description: "Token lifetime in days. Null defers to the tenant setting or plan limit. Ignored for inline-only formats (no token minted)." },
          { name: "email_to", type: "string | null", description: "Single email address to deliver the report URLs to." },
          { name: "branding", type: "BrandingOverride | null", description: "Per-call branding override. Object with name/logo_url/primary_color/accent_color/hide_footer fields (each optional). Requires the white-label entitlement." },
          { name: "detail_level", type: '"executive" | "standard" | "comprehensive"', default: '"standard"', description: "Narrative density of the generated PDF/HTML report." },
          { name: "summary_page", type: '"prepend" | "only" | "off" | null', default: '"prepend" (or tenant override)', description: "Where the executive summary page lands in the PDF." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Generate-reports response fields</h4>
      <FieldTable
        rows={[
          { name: "reports[].format", type: "string", description: "The requested format name, echoed back." },
          { name: "reports[].url", type: "string | null", description: "Signed token URL for the hosted artifact, e.g. https://reports.lintpdf.com/r/{token}{.ext}. null for inline-only rows." },
          { name: "reports[].token", type: "string | null", description: "Opaque share token. 43 characters and deterministic when the caller sent an Idempotency-Key header, otherwise a random 32-byte urlsafe string. null for inline-only rows." },
          { name: "reports[].expires_at", type: "string | null", description: "ISO-8601 timestamp when the URL stops resolving. null for inline-only rows and for mints created with expiry_days: null." },
          { name: "reports[].data", type: "object | string | null", description: "Inline payload. Parsed object for format=\"json\", raw string for format=\"xml\". Present only when return is \"inline\" or \"both\" — omitted (null) for URL-only rows." },
          { name: "reports[].content_type", type: "string | null", description: "MIME type for the inline payload (application/json or application/xml). null when data is null." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Idempotency-Key (optional)</h4>
      <p className="text-slate-600 text-sm mb-2">
        Send the <code className="bg-slate-100 px-1 rounded">Idempotency-Key</code> request header (max 255 characters) to make
        mints safe to retry. The engine derives each token as
        <code className="bg-slate-100 px-1 rounded"> sha256(tenant_id + idempotency_key + format) </code>
        and reuses the stored artifact instead of regenerating it when
        the same key recurs. Keys are scoped per tenant — a shared key
        will never collide with another tenant&apos;s reports.
      </p>
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

      <h4 id="reports-batch-mint" className="text-lg font-semibold text-slate-900 mt-10 mb-3">
        Bulk report-mint
      </h4>
      <p className="text-slate-600 mb-4">
        When a client has completed many independent jobs and needs
        share links for all of them, the single-endpoint approach is
        one HTTP round trip per job. At bulk scale (hundreds of jobs)
        that N-request storm is a common source of dropped mints.
        <code className="bg-slate-100 px-1 rounded">POST /api/v1/reports:batchMint</code>
        collapses the fan-out into a single request. Minted tokens are
        byte-identical to the single-endpoint output; the only
        behavioral difference is that advanced per-call knobs
        (universal overrides envelope, inline returns, idempotency-key)
        live only on the single endpoint. Hard-capped at 500 job_ids
        per call.
      </p>
      <Endpoint
        method="POST"
        path="/api/v1/reports:batchMint"
        description="Mint reports for up to 500 completed jobs in one round trip. Returns 200 with a per-job result array; a single failure does not drop the rest of the batch."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/reports:batchMint \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "job_ids": ["d4e5f6a7-...", "a1b2c3d4-...", "e5f6a7b8-..."],
    "formats": ["html", "pdf", "json"],
    "expiry_days": 7,
    "allow_annotations": false,
    "require_visitor_email": false
  }'`}
        response={`{
  "results": [
    { "job_id": "d4e5f6a7-...", "status": "ok",
      "reports": [
        { "format": "html", "token": "rpt_01HXY...",
          "url": "https://reports.lintpdf.com/r/rpt_01HXY...",
          "viewer_url": "https://app.lintpdf.com/view/rpt_01HXY...",
          "expires_at": "2026-04-28T10:30:00Z" },
        { "format": "pdf", "token": "rpt_01HXZ...", ... },
        { "format": "json", "token": "rpt_01HXA...", ... }
      ]
    },
    { "job_id": "a1b2c3d4-...", "status": "failed",
      "error": "404: Job not found" }
  ],
  "summary": { "ok": 1, "failed": 1 }
}`}
      />
    </section>
  );
}
