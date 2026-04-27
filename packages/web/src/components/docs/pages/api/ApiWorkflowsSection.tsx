import { Endpoint } from "@/components/docs/Endpoint";

export default function ApiWorkflowsSection() {
  return (
    <section className="mb-12">
      <h3 id="workflows" className="text-xl font-bold text-slate-900 mb-3">
        Workflows
      </h3>
      <p className="text-slate-600 mb-4">
        A Workflow pins a profile + brand spec + per-call ToggleOverride
        defaults under a single name so jobs can be submitted with a
        single named handle. Workflows replace the legacy{" "}
        <code className="bg-slate-100 px-1 rounded">/api/v1/endpoints</code>{" "}
        custom-endpoint surface (Phase 0.7 unified-config substrate).
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/workflows"
        auth
        description="List workflows for the current tenant."
        request={`GET /api/v1/workflows
Authorization: Bearer lpdf_live_...`}
        response={`{
  "workflows": [
    {
      "id": "w1",
      "name": "Coated stock",
      "profile_id": "lintpdf-default",
      "brand_spec_id": null,
      "created_at": "2026-04-20T12:00:00Z"
    }
  ]
}`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/workflows"
        auth
        description="Create a workflow."
        request={`POST /api/v1/workflows
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{
  "name": "Uncoated stock",
  "profile_id": "lintpdf-default",
  "brand_spec_id": null
}`}
        response={`{ "id": "w2", "name": "Uncoated stock", "profile_id": "lintpdf-default" }`}
      />

      <Endpoint
        method="PATCH"
        path="/api/v1/workflows/{workflow_id}"
        auth
        description="Update a workflow's editable fields."
        request={`PATCH /api/v1/workflows/w2
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{ "name": "Renamed" }`}
        response={`{ "id": "w2", "name": "Renamed", … }`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/workflows/{workflow_id}"
        auth
        description="Delete a workflow."
        request={`DELETE /api/v1/workflows/w2
Authorization: Bearer lpdf_live_...`}
        response={`HTTP/1.1 204 No Content`}
      />
    </section>
  );
}
