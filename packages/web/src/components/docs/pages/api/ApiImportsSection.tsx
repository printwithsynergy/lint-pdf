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
    "format": "xml",
    "item_selector": "//Finding",
    "fields": {
      "severity": { "selector": "@level" },
      "message":  { "selector": "Description" },
      "page_num": { "selector": "Page", "parse": "int" },
      "bbox":     { "selector": "BBox", "format": "space_xywh" },
      "inspection_id": { "selector": "@rule" }
    },
    "severity_map": { "S": "error", "W": "warning", "N": "advisory" },
    "default_severity": "warning"
  }'`}
        response={`{
  "id": "mpg_01HXY...",
  "name": "Internal QA XML",
  "format": "xml",
  "is_active": true,
  "created_at": "2026-04-12T10:30:00Z"
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Mapping request fields</h4>
      <FieldTable
        rows={[
          { name: "name", type: "string", required: true, description: "Human-readable label shown in the editor." },
          { name: "format", type: '"xml" | "json"', required: true, description: "Parser used to load the uploaded report." },
          { name: "item_selector", type: "string", required: true, description: "XPath (XML) or dotted path (JSON) selecting each finding. JSON supports [*] expansion." },
          { name: "fields", type: "object", required: true, description: "Per-field selectors. See Custom Import Mappings doc for the full grammar." },
          { name: "severity_map", type: "Record<string,string>", description: "Maps raw severity strings to error|warning|advisory." },
          { name: "default_severity", type: '"error"|"warning"|"advisory"', default: "warning", description: "Applied when severity_map misses." },
          { name: "is_active", type: "boolean", default: "true", description: "Inactive mappings are hidden from the submit form and cannot be used on new jobs." },
        ]}
      />

      <Endpoint
        method="GET"
        path="/api/v1/tenant/import-mappings"
        description="List all mappings owned by the current tenant. Soft-deleted mappings are excluded unless include_deleted=true."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/tenant/import-mappings" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "mappings": [
    { "id": "mpg_01HXY...", "name": "Internal QA XML", "format": "xml", "is_active": true }
  ]
}`}
      />

      <Endpoint
        method="PATCH"
        path="/api/v1/tenant/import-mappings/{id}"
        description="Update any mapping field except id and tenant_id. Deactivating a mapping stops it being used on new submissions but preserves it for history."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/tenant/import-mappings/mpg_01HXY... \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "is_active": false }'`}
        response={`{ "id": "mpg_01HXY...", "is_active": false }`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/tenant/import-mappings/{id}"
        description="Soft-delete a mapping. Historical jobs retain their finding provenance."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/tenant/import-mappings/mpg_01HXY... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "deleted": true, "id": "mpg_01HXY..." }`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/tenant/import-mappings/preview"
        description="Dry-run a mapping against a sample report. Returns the parsed findings without persisting a job."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/tenant/import-mappings/preview \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -F mapping_id=mpg_01HXY... \\
  -F sample=@report.xml`}
        response={`{
  "findings": [
    { "severity": "error", "message": "...", "page_num": 3, "bbox": [72,720,540,740] }
  ],
  "matched": 12,
  "errors": []
}`}
      />
    </section>
  );
}
