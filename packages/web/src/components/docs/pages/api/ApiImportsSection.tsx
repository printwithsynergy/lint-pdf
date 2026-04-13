import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiImportsSection() {
  return (
    <section className="mb-12">
      <h3 id="imports" className="text-xl font-bold text-slate-900 mb-3">
        External imports &amp; custom mappings
      </h3>
      <p className="text-slate-600 mb-4">
        When <code className="bg-slate-100 px-1 rounded">preflight_source=external</code>, submit the
        report alongside the PDF. LintPDF parses PitStop XML, callas JSON/XML,
        Acrobat Preflight XML, and our native v1 JSON schema directly. For any
        other shape, define a tenant-scoped custom mapping.
      </p>

      <Endpoint
        method="POST"
        path="/api/v1/tenant/import-mappings"
        description="Create a custom import mapping. Requires the branding:manage permission."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenant/import-mappings \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Internal QA XML",
    "description": "Maps our in-house preflight XML to LintPDF findings.",
    "format": "xml",
    "config": {
      "item_selector": "Findings/Finding",
      "fields": {
        "severity": { "selector": "@level" },
        "message":  { "selector": "Description" },
        "page_num": { "selector": "Page", "parse": "int" },
        "bbox":     { "selector": "BBox", "format": "space_xywh" },
        "inspection_id": { "selector": "@rule" }
      },
      "severity_map": { "S": "error", "W": "warning", "N": "advisory" },
      "default_severity": "warning"
    },
    "sample_payload": "<Findings>...</Findings>",
    "sample_mime": "application/xml",
    "is_active": true
  }'`}
        response={`{
  "id": "2f7c1e8a-1b4d-4e1a-9a2b-9c8d7e6f5a4b",
  "name": "Internal QA XML",
  "description": "Maps our in-house preflight XML to LintPDF findings.",
  "format": "xml",
  "config": { "item_selector": "Findings/Finding", "fields": { ... } },
  "sample_payload": "<Findings>...</Findings>",
  "sample_mime": "application/xml",
  "is_active": true,
  "created_at": "2026-04-12T10:30:00Z",
  "updated_at": "2026-04-12T10:30:00Z"
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Mapping request fields</h4>
      <FieldTable
        rows={[
          { name: "name", type: "string", required: true, description: "Human-readable label shown in the editor (1–128 chars)." },
          { name: "description", type: "string | null", description: "Optional description surfaced in the dashboard picker." },
          { name: "format", type: '"xml" | "json"', default: '"xml"', description: "Parser used to load the uploaded report." },
          { name: "config", type: "object", required: true, description: "Mapping DSL. Holds item_selector, fields, severity_map, default_severity. See the Custom Import Mappings doc for the full grammar." },
          { name: "sample_payload", type: "string | null", description: "Verbatim sample report used by the preview endpoint." },
          { name: "sample_mime", type: "string | null", description: "MIME type hint for the stored sample (e.g. application/xml, application/json). Max 64 chars." },
          { name: "is_active", type: "boolean", default: "true", description: "Inactive mappings are hidden from the submit form and cannot be used on new jobs." },
        ]}
      />

      <Endpoint
        method="GET"
        path="/api/v1/tenant/import-mappings"
        description="List all mappings owned by the current tenant. Soft-deleted mappings are flagged with is_active=false but remain visible for audit."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/tenant/import-mappings" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "mappings": [
    {
      "id": "2f7c1e8a-...",
      "name": "Internal QA XML",
      "description": "Maps our in-house preflight XML to LintPDF findings.",
      "format": "xml",
      "config": { ... },
      "sample_payload": "<Findings>...</Findings>",
      "sample_mime": "application/xml",
      "is_active": true,
      "created_at": "2026-04-12T10:30:00Z",
      "updated_at": "2026-04-12T10:30:00Z"
    }
  ]
}`}
      />

      <Endpoint
        method="GET"
        path="/api/v1/tenant/import-mappings/{mapping_id}"
        description="Retrieve a single mapping."
        auth
        request={`curl https://api.lintpdf.com/api/v1/tenant/import-mappings/2f7c1e8a-... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "id": "2f7c1e8a-...", "name": "Internal QA XML", "format": "xml", "config": {...}, "is_active": true, ... }`}
      />

      <Endpoint
        method="PUT"
        path="/api/v1/tenant/import-mappings/{mapping_id}"
        description="Replace a mapping. Body takes the same shape as create. Deactivating (is_active=false) stops the mapping being used on new submissions but preserves it for history."
        auth
        request={`curl -X PUT https://api.lintpdf.com/api/v1/tenant/import-mappings/2f7c1e8a-... \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Internal QA XML",
    "format": "xml",
    "config": { ... },
    "is_active": false
  }'`}
        response={`{ "id": "2f7c1e8a-...", "is_active": false, ... }`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/tenant/import-mappings/{mapping_id}"
        description="Soft-delete a mapping by flipping is_active to false. Historical jobs retain their finding provenance. Returns 204."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/tenant/import-mappings/2f7c1e8a-... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`HTTP/1.1 204 No Content`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/tenant/import-mappings/{mapping_id}/preview"
        description="Dry-run a mapping against a sample report. Returns the parsed findings without persisting a job. Parser errors surface as ok=false with a human-readable error instead of a 4xx so the editor can render inline feedback."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenant/import-mappings/2f7c1e8a-.../preview \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "config": { "item_selector": "Findings/Finding", "fields": { ... } },
    "sample_payload": "<Findings>...</Findings>"
  }'`}
        response={`{
  "ok": true,
  "findings_count": 12,
  "sample_findings": [
    {
      "severity": "error",
      "message": "Image resolution too low",
      "page_num": 3,
      "inspection_id": "IMG_LOWRES",
      "bbox": [72, 720, 540, 740],
      "object_id": "Im4",
      "object_type": "image",
      "category": "Images"
    }
  ],
  "error": null
}`}
      />
      <p className="text-slate-600 text-sm mt-2">
        Both request fields are optional: when omitted, preview uses the
        mapping&apos;s stored <code className="bg-slate-100 px-1 rounded">config</code> and
        {" "}<code className="bg-slate-100 px-1 rounded">sample_payload</code>. Supply
        them to iterate on a config in the editor before saving. Returns at
        most the first 5 findings in <code className="bg-slate-100 px-1 rounded">sample_findings</code>.
      </p>
    </section>
  );
}
