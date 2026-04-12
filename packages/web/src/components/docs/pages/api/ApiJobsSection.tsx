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
  "status": "queued",
  "preflight_source": "engine",
  "profile_id": "lintpdf-default",
  "file_name": "brochure.pdf",
  "created_at": "2026-04-12T10:30:00Z",
  "reports": {
    "viewer_url": "https://app.lintpdf.com/viewer/d4e5f6a7-..."
  }
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
            description: "Tenant-defined custom import mapping. Mutually exclusive with external_format.",
          },
          {
            name: "jdf_file",
            type: "file",
            description: "Optional JDF job ticket. Findings include jdf_context when supplied.",
          },
          {
            name: "ai_enabled",
            type: "boolean",
            default: "false",
            description: "Run AI inspections in addition to engine checks. Engine mode only.",
          },
          {
            name: "ai_categories",
            type: "string[]",
            description: "Comma-separated AI category IDs to run. See AI docs.",
          },
          {
            name: "ai_features",
            type: "string[]",
            description: "Comma-separated AI inspection IDs. Takes precedence over ai_categories.",
          },
          {
            name: "ai_preset",
            type: "string",
            description: "AI preset ID (e.g. fda-food-label). Expanded server-side.",
          },
          {
            name: "brand",
            type: '"anonymous" | "lintpdf" | uuid',
            description: "Per-request brand override. UUID must be a BrandProfile owned by your tenant.",
          },
          {
            name: "unbranded",
            type: "boolean",
            default: "false",
            description: "Alias for brand=anonymous. Deprecated in favour of the explicit brand field.",
          },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Status codes</h4>
      <FieldTable
        rows={[
          { name: "202", type: "Accepted", description: "Job queued; poll GET /jobs/{id} for completion." },
          { name: "400", type: "Bad Request", description: "Missing file, malformed multipart, or mutually exclusive fields set together." },
          { name: "401", type: "Unauthorized", description: "Missing or invalid bearer token." },
          { name: "403", type: "Forbidden", description: "Valid key, but you lack permission (e.g. cross-tenant mapping_id)." },
          { name: "404", type: "Not Found", description: "profile_id or mapping_id does not exist in your tenant." },
          { name: "409", type: "Conflict", description: "Inactive or soft-deleted mapping referenced." },
          { name: "413", type: "Payload Too Large", description: "File exceeds the per-tenant upload limit." },
          { name: "422", type: "Unprocessable Entity", description: "ClamAV detected malware, or enum value was invalid." },
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
  "preflight_source": "engine",
  "external_format": null,
  "profile_id": "lintpdf-default",
  "file_name": "brochure.pdf",
  "page_count": 12,
  "duration_ms": 3480,
  "data_capabilities": {
    "pages": true,
    "separations": true,
    "fonts": true,
    "images": true,
    "tac": true,
    "layers": false,
    "findings": true
  },
  "summary": {
    "total_findings": 7,
    "error": 1,
    "warning": 4,
    "advisory": 2
  },
  "findings": [
    {
      "inspection_id": "font.not_embedded",
      "severity": "error",
      "message": "Font 'Helvetica' is not embedded",
      "page_num": 1,
      "bbox": [72.0, 720.0, 540.0, 740.0],
      "object_id": "Font12",
      "object_type": "Font",
      "category": "Fonts",
      "source": { "type": "engine", "profile": "lintpdf-default" }
    }
  ],
  "reports": {
    "viewer_url": "https://app.lintpdf.com/viewer/d4e5f6a7-...",
    "pdf_url": "https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-.../report.pdf"
  }
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/jobs?page=1&page_size=25"
        description="List jobs for the current tenant. Returns newest first."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/jobs?page=1&page_size=25" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "jobs": [ { "job_id": "...", "status": "complete", "file_name": "...", "created_at": "..." } ],
  "page": 1,
  "page_size": 25,
  "total": 418
}`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/jobs/{job_id}"
        description="Delete a job and all derived artifacts (reports, tiles, share tokens)."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/jobs/d4e5f6a7-... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "deleted": true, "job_id": "d4e5f6a7-..." }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Custom submission endpoints</h4>
      <p className="text-slate-600 mb-3">
        Growth-tier customers can mint vanity slugs and give customers a branded
        submission URL instead of <code className="bg-slate-100 px-1 rounded">/api/v1/jobs</code>.
      </p>
      <Endpoint
        method="POST"
        path="/api/v1/endpoints/{slug}/submit"
        description="Submit a file against a vanity endpoint. The endpoint's bound profile, brand, and permissions apply."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/endpoints/acme-proofs/submit \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -F file=@brochure.pdf`}
        response={`{ "job_id": "d4e5f6a7-...", "status": "queued" }`}
      />
    </section>
  );
}
