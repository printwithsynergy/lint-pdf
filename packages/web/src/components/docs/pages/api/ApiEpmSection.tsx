import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiEpmSection() {
  return (
    <section className="mb-12">
      <h3 id="epm" className="text-xl font-bold text-slate-900 mb-3">
        EPM candidacy verdict
      </h3>
      <p className="text-slate-600 mb-4">
        EPM (Extended Print Mode) is HP&apos;s CMY-only press path that
        skips the K plate for throughput. The engine scores every
        completed job against the 16{" "}
        <code className="bg-slate-100 px-1 rounded">LPDF_EPM_*_REJECT</code>{" "}
        codes plus the legacy{" "}
        <code className="bg-slate-100 px-1 rounded">LPDF_EPM_001..018</code>{" "}
        set and surfaces a tier verdict with rejection drivers,
        advisories, and an IndiChrome-substrate upsell hint.
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/jobs/{job_id}/epm"
        auth
        description="Read the EPM candidacy verdict for a job's fired findings."
        request={`GET /api/v1/jobs/abc/epm
Authorization: Bearer lpdf_live_...`}
        response={`{
  "job_id": "abc",
  "tier": "marginal",
  "rejection_drivers": ["LPDF_EPM_BLEED_REJECT"],
  "advisories": ["LPDF_EPM_TRAPPING_REJECT"],
  "recommends_indichrome": false,
  "legacy_codes_fired": [],
  "epm_findings_count": 2
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Tiers</h4>
      <FieldTable
        rows={[
          { name: "pass", type: "string", description: "No EPM-related findings — job runs cleanly on the EPM path." },
          { name: "pass_with_advisory", type: "string", description: "Tier-C advisory findings only; verdict is still PASS but operators should review." },
          { name: "marginal", type: "string", description: "One Tier-B soft-rejection finding fired; treat as borderline. Two or more → reject." },
          { name: "reject", type: "string", description: "Any Tier-A finding, or two+ Tier-B findings — job is not an EPM candidate." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Inline on JobResponse</h4>
      <p className="text-slate-600 mb-3">
        The verdict is also surfaced inline on the single-job{" "}
        <code className="bg-slate-100 px-1 rounded">GET /api/v1/jobs/{`{id}`}</code>{" "}
        response under <code className="bg-slate-100 px-1 rounded">epm_verdict</code>.
        List endpoints (<code className="bg-slate-100 px-1 rounded">GET /api/v1/jobs</code>) leave it null —
        scoring per row is skipped to keep list latency cheap.
      </p>
      <CodeBlock>{`GET /api/v1/jobs/abc

{
  "job_id": "abc",
  "epm_verdict": { "tier": "marginal", … },
  "decisions_count": 1,
  …
}`}</CodeBlock>
    </section>
  );
}
