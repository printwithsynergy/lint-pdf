import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";

export default function ApiExplainSection() {
  return (
    <section className="mb-12">
      <h3 id="explain" className="text-xl font-bold text-slate-900 mb-3">
        AI-Explain
      </h3>
      <p className="text-slate-600 mb-4">
        Generate a human-readable explanation for a finding via Claude
        Haiku 4.5. Explanations are cached on the finding row so
        repeated calls hit the cache for free. Cost-cap exceeded
        returns <code className="bg-slate-100 px-1 rounded">HTTP 402</code>{" "}
        — preflight + reports keep working, only the LLM features pause
        until the next monthly reset (or a higher cap).
      </p>

      <Endpoint
        method="POST"
        path="/api/v1/jobs/{job_id}/findings/{finding_id}/explain"
        auth
        description="Generate (or fetch cached) AI explanation for a finding."
        request={`POST /api/v1/jobs/abc/findings/xyz/explain
Authorization: Bearer lpdf_live_...`}
        response={`{
  "finding_id": "xyz",
  "explanation": "This font is not embedded; the press will substitute Helvetica.",
  "model": "claude-haiku-4-5",
  "cached": false,
  "cost_cents": 0.04
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">
        Cost-cap behavior (Q-C5)
      </h4>
      <p className="text-slate-600 mb-3">
        When the tenant&apos;s monthly LLM cost cap is exhausted, this
        endpoint returns 402 with a structured detail. The dashboard
        and SDK surface that as a &ldquo;raise the cap&rdquo; CTA.
      </p>
      <CodeBlock>{`HTTP/1.1 402 Payment Required
Content-Type: application/json

{
  "detail": "Cost cap exceeded — raise the cap in Account → Billing.",
  "used_cents": 9987,
  "monthly_cap_cents": 10000
}`}</CodeBlock>
    </section>
  );
}
