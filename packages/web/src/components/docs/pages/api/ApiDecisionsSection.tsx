import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiDecisionsSection() {
  return (
    <section className="mb-12">
      <h3 id="decisions" className="text-xl font-bold text-slate-900 mb-3">
        Decisions audit (V-05)
      </h3>
      <p className="text-slate-600 mb-4">
        Operator decisions on jobs and findings are stored in a
        tenant-scoped append-only audit table. Decisions never delete
        — revoke stamps{" "}
        <code className="bg-slate-100 px-1 rounded">revoked_at</code> /{" "}
        <code className="bg-slate-100 px-1 rounded">revoked_by_user_id</code> /{" "}
        <code className="bg-slate-100 px-1 rounded">revoked_reason</code> so
        audit replays stay correct after operators change their minds.
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/jobs/{job_id}/decisions"
        auth
        description="List decisions on a job (newest first; active by default)."
        request={`GET /api/v1/jobs/abc/decisions?include_revoked=false&limit=200
Authorization: Bearer lpdf_live_...`}
        response={`{
  "decisions": [
    {
      "id": "d1",
      "job_id": "abc",
      "finding_id": null,
      "decision_type": "approve",
      "decided_by_user_id": "u1",
      "source": "dashboard",
      "decided_at": "2026-04-27T12:00:00Z",
      "is_active": true
    }
  ],
  "count": 1
}`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/jobs/{job_id}/decisions"
        auth
        description="Record a job-level decision (no finding scope)."
        request={`POST /api/v1/jobs/abc/decisions
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{
  "decision_type": "approve",
  "decided_by_user_id": "u1",
  "source": "api",
  "notes": "Approved after operator review."
}`}
        response={`{
  "id": "d1",
  "decision_type": "approve",
  "decided_by_user_id": "u1",
  "source": "api",
  "is_active": true,
  ...
}`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/jobs/{job_id}/findings/{finding_id}/decisions"
        auth
        description="Record a finding-level decision."
        request={`POST /api/v1/jobs/abc/findings/xyz/decisions
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{
  "decision_type": "waive",
  "decided_by_user_id": "u1",
  "source": "api",
  "notes": "Customer accepts the risk."
}`}
        response={`{ "id": "d2", "finding_id": "xyz", "decision_type": "waive", … }`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/jobs/{job_id}/decisions/{decision_id}/revoke"
        auth
        description="Soft-revoke a decision (Q-2). Idempotent — re-revoking is a no-op."
        request={`POST /api/v1/jobs/abc/decisions/d1/revoke
Content-Type: application/json
Authorization: Bearer lpdf_live_...

{ "revoked_by_user_id": "u2", "revoked_reason": "Mistake" }`}
        response={`{
  "id": "d1",
  "is_active": false,
  "revoked_at": "2026-04-27T12:30:00Z",
  "revoked_by_user_id": "u2",
  "revoked_reason": "Mistake"
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">
        Effective decision on findings
      </h4>
      <p className="text-slate-600 mb-3">
        The latest non-revoked decision per finding is also surfaced on
        each <code className="bg-slate-100 px-1 rounded">FindingResponse</code>{" "}
        as <code className="bg-slate-100 px-1 rounded">effective_decision</code>{" "}
        — a minimal projection so dashboards can render the verdict
        chip without a second fetch.
      </p>
      <FieldTable
        rows={[
          { name: "decision_type", type: "string", description: "approve | reject | waive | suppress | annotate | escalate" },
          { name: "decided_at", type: "string", description: "ISO-8601 UTC timestamp." },
          { name: "decided_by_user_id", type: "string", description: "Tenant-scoped operator id (max 128 chars)." },
        ]}
      />
    </section>
  );
}
