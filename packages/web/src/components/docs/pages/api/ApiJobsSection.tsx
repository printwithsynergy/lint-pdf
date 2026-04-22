import Link from "next/link";
import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiJobsSection() {
  return (
    <section className="mb-12">
      <h3 id="jobs" className="text-xl font-bold text-slate-900 mb-3">
        Jobs
      </h3>
      <p className="text-slate-600 mb-4">
        A Job is one file submitted for processing. Jobs carry a status,
        findings, reports, and (optionally) a preflight source. LintPDF supports
        three submission modes via <code className="bg-slate-100 px-1 rounded">preflight_source</code>:
        {" "}<code className="bg-slate-100 px-1 rounded">engine</code> (run our analyzers),
        {" "}<code className="bg-slate-100 px-1 rounded">external</code> (import findings
        from your own preflight tool), and <code className="bg-slate-100 px-1 rounded">minimal</code>
        {" "}(viewer-only, no analysis).
      </p>

      <Endpoint
        method="POST"
        path="/api/v1/jobs"
        description="Submit a PDF for processing. Accepts multipart/form-data. All fields except file are optional."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/jobs \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -F file=@brochure.pdf \\
  -F profile_id=lintpdf-default \\
  -F preflight_source=engine`}
        response={`{
  "job_id": "d4e5f6a7-1234-4567-89ab-cdef01234567",
  "status": "pending",
  "message": "Job submitted successfully"
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Request fields</h4>
      <FieldTable
        rows={[
          {
            name: "file",
            type: "file",
            required: true,
            description: "The PDF (or convertible input) to process.",
          },
          {
            name: "profile_id",
            type: "string",
            default: "lintpdf-default",
            description: "Preflight profile ID. Ignored when preflight_source is minimal.",
          },
          {
            name: "preflight_source",
            type: '"engine" | "external" | "minimal"',
            default: "engine",
            description: "How findings are produced for this job.",
          },
          {
            name: "external_format",
            type: '"pitstop_xml" | "callas_json" | "callas_xml" | "acrobat_xml" | "lintpdf_json"',
            description: "Format of the external report. Omit to auto-detect. Mutually exclusive with mapping_id.",
          },
          {
            name: "external_report",
            type: "file",
            description: "The preflight report when preflight_source=external. XML or JSON.",
          },
          {
            name: "mapping_id",
            type: "uuid",
            description: "Tenant-defined custom import mapping. Mutually exclusive with external_format — sets the format to custom internally.",
          },
          {
            name: "jdf_file",
            type: "file",
            description: "Optional JDF/XJDF sidecar. Findings include jdf_context when supplied.",
          },
          {
            name: "ai_enabled",
            type: "boolean",
            default: "null (profile decides)",
            description: "Per-job override: true forces AI on, false forces AI off, unset defers to the profile.",
          },
          {
            name: "ai_categories",
            type: "string",
            description: "Comma-separated AI category IDs to enable. Applied only when ai_enabled=true.",
          },
          {
            name: "ai_features",
            type: "string",
            description: "Comma-separated AI inspection slugs. Takes precedence over ai_categories.",
          },
          {
            name: "ai_preset",
            type: "string",
            description: "AI preset slug (e.g. brand-compliance, packaging-qc, full-ai-scan). Implicitly enables AI.",
          },
          {
            name: "brand",
            type: '"anonymous" | "lintpdf" | uuid',
            description: "Per-request brand override. UUID must be a BrandProfile owned by your tenant. Absent → tenant default.",
          },
          {
            name: "unbranded",
            type: "boolean",
            description: "Convenience alias: when true, equivalent to brand=anonymous.",
          },
          {
            name: "wait",
            type: "float (query param)",
            description:
              "If set, block the response up to this many seconds for the job to reach a terminal state. On success the handler returns 200 + the full JobResponse; on timeout it falls back to the 202 + job_id response so you can keep polling. Server-side ceiling is LINTPDF_SYNC_MAX_WAIT_S (default 120s).",
          },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Status codes</h4>
      <FieldTable
        rows={[
          { name: "200", type: "OK", description: "Only when ?wait= was set and the job reached a terminal state inline. Body is the full JobResponse." },
          { name: "202", type: "Accepted", description: "Job queued; poll GET /jobs/{id} for completion." },
          { name: "401", type: "Unauthorized", description: "Missing or invalid bearer token." },
          { name: "403", type: "Forbidden", description: "Valid key, but you lack permission — e.g. cross-tenant mapping_id, or plan doesn't include the requested feature." },
          { name: "404", type: "Not Found", description: "profile_id or mapping_id does not exist in your tenant." },
          { name: "413", type: "Payload Too Large", description: "File exceeds the per-tenant upload limit." },
          { name: "422", type: "Unprocessable Entity", description: "Invalid enum value, malformed UUID, unparseable external_report, ClamAV-detected malware, or mutually exclusive fields set together." },
          { name: "429", type: "Too Many Requests", description: "Rate limit exceeded. Back off using the X-RateLimit-* headers." },
        ]}
      />

      <Endpoint
        method="GET"
        path="/api/v1/jobs/{job_id}"
        description="Retrieve a single job, including summary, findings, and report URLs."
        auth
        request={`curl https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job_id": "d4e5f6a7-...",
  "status": "complete",
  "profile_id": "lintpdf-default",
  "file_name": "brochure.pdf",
  "file_size": 842139,
  "page_count": 12,
  "created_at": "2026-04-12T10:30:00Z",
  "completed_at": "2026-04-12T10:30:04Z",
  "duration_ms": 3480,
  "summary": {
    "total_findings": 7,
    "error_count": 1,
    "warning_count": 4,
    "advisory_count": 2,
    "passed": false,
    "page_count": 12,
    "file_size_bytes": 842139
  },
  "findings": [
    {
      "inspection_id": "font.not_embedded",
      "severity": "error",
      "message": "Font 'Helvetica' is not embedded",
      "page_num": 1,
      "bbox": [72.0, 720.0, 540.0, 740.0],
      "object_id": "Font12",
      "object_type": "font",
      "category": "fonts",
      "source": "engine",
      "audit": {
        "status": "confirmed",
        "rationale": "Helvetica glyph references with no matching /FontFile entry.",
        "model": "modal:qwen2-vl-7b",
        "at": "2026-04-22T18:05:34Z"
      }
    }
  ],
  "reports": {
    "pdf": "https://reports.lintpdf.com/r/abc123.pdf",
    "html": "https://reports.lintpdf.com/r/abc123"
  }
}`}
      />

      <p className="text-slate-600 text-sm mt-2">
        Capability flags (<code className="bg-slate-100 px-1 rounded">separations</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">tac</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">fonts</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">images</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">layers</code>) live on
        the viewer config (<code className="bg-slate-100 px-1 rounded">GET /viewer/jobs/{"{id}"}/config</code>), not
        on the job payload.
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/jobs?page=1&page_size=25"
        description="List jobs for the current tenant. Returns newest first."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/jobs?page=1&page_size=25" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "jobs": [ { "job_id": "...", "status": "complete", "file_name": "...", "created_at": "..." } ],
  "total": 418,
  "page": 1,
  "page_size": 25
}`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/jobs/{job_id}"
        description="Delete a job and all derived artifacts (reports, tiles, share tokens). Returns 204 No Content on success."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`HTTP/1.1 204 No Content`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Universal job state</h4>
      <p className="text-slate-600 mb-3">
        <code className="bg-slate-100 px-1 rounded">GET /api/v1/jobs/{"{job_id}"}/state</code>
        {" "}returns preflight results, every minted report URL, the approval
        chain (with each approver&apos;s notes), the manual verdict, and every
        viewer annotation with its comment thread embedded — in one call.
        Previously this required 3+ round trips and an N+1 fan-out for
        comments. See the dedicated <Link href="/docs/job-state" className="text-blue-600 underline">Universal Job State</Link>
        {" "}page for the full field table and a runnable example payload.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/jobs/{job_id}/state"
        description="Aggregated digest: core job + reports + approval chain + verdict + annotations-with-comments. Filter with ?include=reports,approval_chain,verdict,annotations."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-.../state" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "job": { "job_id": "...", "status": "complete", "summary": { "passed": true, "total_findings": 2 } },
  "reports": [
    { "format": "annotated_pdf", "url": "https://reports.lintpdf.com/r/...", "token": "...",
      "allow_annotations": false, "require_visitor_email": null }
  ],
  "approval_chain": {
    "status": "approved", "current_step": 0,
    "step_history": [
      { "step_name": "Print ops", "approver_email": "ops@example.com",
        "decision": "approved", "notes": "Looks great, ship it." }
    ]
  },
  "verdict": { "verdict": "approved", "auto_passed": true, "notes": "..." },
  "annotations": {
    "total": 1, "by_page": { "1": 1 },
    "items": [
      { "id": "...", "page_num": 1, "kind": "rect", "text": "Fix the bleed",
        "comments": [ { "body": "Will do by EOD.", "author_email": "..." } ] }
    ]
  }
}`}
      />

      <FieldTable
        rows={[
          {
            name: "include",
            type: "string (CSV)",
            default: "all sections",
            description:
              "Optional comma-separated list. Accepted keys: reports, approval_chain, verdict, annotations. Unknown keys 422. Core job block is always returned.",
          },
        ]}
      />

      <p className="text-slate-600 text-sm mt-3 mb-6">
        Share-link mirror: <code className="bg-slate-100 px-1 rounded">GET /api/v1/viewer/public/{"{token}"}/state</code>
        {" "}returns the same shape minus the <code className="bg-slate-100 px-1 rounded">reports</code>
        {" "}section (listing sibling share-link tokens from a single token would leak shares that weren&apos;t handed to the current visitor).
      </p>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Custom submission endpoints</h4>
      <p className="text-slate-600 mb-3">
        Growth-tier customers can mint vanity slugs and give customers a branded
        submission URL instead of <code className="bg-slate-100 px-1 rounded">/api/v1/jobs</code>.
        Each endpoint has a <code className="bg-slate-100 px-1 rounded">response_mode</code>
        {" "}setting: <code className="bg-slate-100 px-1 rounded">async</code> (default) returns
        {" "}202 + job_id so the caller polls <code className="bg-slate-100 px-1 rounded">GET /api/v1/jobs/{"{id}"}</code>;
        {" "}<code className="bg-slate-100 px-1 rounded">sync</code> blocks the submit request until
        the job is terminal and returns the full JobResponse inline. A per-request
        {" "}<code className="bg-slate-100 px-1 rounded">?wait=</code> query param can override either way
        (useful for integrations like Zapier / n8n / Make.com that can&apos;t orchestrate a polling loop).
      </p>
      <Endpoint
        method="POST"
        path="/api/v1/endpoints/{slug}/submit"
        description="Submit a file against a vanity endpoint. The endpoint's bound profile, brand, response_mode, and permissions apply. Pass ?wait=<seconds> to override response_mode for a single call."
        auth
        request={`# Async (default)
curl -X POST https://api.lintpdf.com/api/v1/endpoints/acme-proofs/submit \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -F file=@brochure.pdf

# Sync (wait inline for the verdict)
curl -X POST "https://api.lintpdf.com/api/v1/endpoints/acme-proofs/submit?wait=60" \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -F file=@brochure.pdf`}
        response={`# 202 Accepted (async)
{ "job_id": "d4e5f6a7-...", "status": "pending", "message": "Job submitted successfully" }

# 200 OK (sync, reached terminal within wait budget)
{ "job_id": "d4e5f6a7-...", "status": "complete", "summary": { ... }, "findings": [ ... ], "reports": { ... } }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Endpoint fields</h4>
      <FieldTable
        rows={[
          { name: "slug", type: "string", required: true, description: "Lowercase kebab-case URL slug, unique per tenant (2-255 chars)." },
          { name: "profile_id", type: "string", required: true, description: "Profile this endpoint is bound to. Built-in or tenant-owned." },
          { name: "description", type: "string", description: "Free-text label shown in the dashboard (max 1024 chars)." },
          { name: "is_active", type: "boolean", default: "true", description: "Disable to 404 the submit URL without deleting the slug." },
          {
            name: "response_mode",
            type: '"async" | "sync"',
            default: "async",
            description:
              "Default response behavior for this endpoint. async = 202 + job_id (caller polls). sync = block for terminal state and return full JobResponse. Server-side ceiling is LINTPDF_SYNC_MAX_WAIT_S (default 120s). Callers can override per-request via ?wait= on the submit route.",
          },
        ]}
      />
    </section>
  );
}
