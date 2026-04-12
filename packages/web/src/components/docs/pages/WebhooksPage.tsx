import { CodeBlock } from "@/components/docs/CodeBlock";
import { FieldTable } from "@/components/docs/FieldTable";

export default function WebhooksPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Webhooks</h2>
      <p className="text-slate-600 mb-6">
        Webhooks deliver real-time job events to your HTTPS endpoint. Every
        delivery is signed; destinations must be reachable over HTTPS and must
        not resolve to a private network. Registration fails at{" "}
        <code className="bg-slate-100 px-1 rounded">POST /api/v1/webhooks</code> if either check fails.
      </p>

      <h3 className="font-semibold text-slate-900 mb-3">Registering a webhook</h3>
      <CodeBlock>{`curl -X POST https://api.lintpdf.com/api/v1/webhooks \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-app.com/webhooks/lintpdf",
    "events": ["job.completed", "job.failed"],
    "secret": "whsec_random_value"
  }'`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Event types</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-200 mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Event</th>
              <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Fires when</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["job.completed", "A job finishes processing — engine, external, or minimal mode."],
              ["job.failed", "A job hits a permanent error (corrupt PDF, timeout, parser failure)."],
              ["test.ping", "Delivered by POST /api/v1/webhooks/{id}/test for integration smoke tests."],
            ].map(([event, desc]) => (
              <tr key={event} className="border-b border-slate-100 last:border-0">
                <td className="py-2 px-3">
                  <code className="text-xs font-mono text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded">
                    {event}
                  </code>
                </td>
                <td className="py-2 px-3 text-slate-600">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Payload shape</h3>
      <p className="text-slate-600 mb-3">
        The <code className="bg-slate-100 px-1 rounded">job.completed</code> payload includes the
        preflight provenance (<code className="bg-slate-100 px-1 rounded">preflight_source</code> and{" "}
        <code className="bg-slate-100 px-1 rounded">external_format</code>) plus the effective{" "}
        <code className="bg-slate-100 px-1 rounded">data_capabilities</code> map. Downstream systems can
        use the capability flags to know whether separations/TAC/fonts/images
        are available before fetching them.
      </p>
      <CodeBlock>{`{
  "event": "job.completed",
  "timestamp": "2026-04-12T10:30:01Z",
  "data": {
    "job_id": "d4e5f6a7-...",
    "status": "complete",
    "preflight_source": "external",
    "external_format": "pitstop_xml",
    "profile_id": "lintpdf-default",
    "data_capabilities": {
      "pages": true, "separations": false, "fonts": false,
      "images": false, "tac": false, "layers": false, "findings": true
    },
    "summary": { "total_findings": 12, "error": 2, "warning": 7, "advisory": 3 }
  }
}`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Signature validation</h3>
      <p className="text-slate-600 mb-3">
        Every delivery carries an <code className="bg-slate-100 px-1 rounded">X-LintPDF-Signature</code>{" "}
        header in the form <code className="bg-slate-100 px-1 rounded">sha256=&lt;hex&gt;</code>. Compute an
        HMAC-SHA256 over the raw request body with your registered secret and
        compare using a constant-time function.
      </p>

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">Python</h4>
      <CodeBlock>{`import hmac, hashlib

def valid(body: bytes, header: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={mac}", header)`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-4 mb-2">Node.js</h4>
      <CodeBlock>{`import { createHmac, timingSafeEqual } from "node:crypto";

export function valid(body: Buffer, header: string, secret: string) {
  const mac = "sha256=" + createHmac("sha256", secret).update(body).digest("hex");
  const a = Buffer.from(mac);
  const b = Buffer.from(header);
  return a.length === b.length && timingSafeEqual(a, b);
}`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Test deliveries</h3>
      <p className="text-slate-600 mb-3">
        Use the test endpoint while wiring up your receiver. It delivers a{" "}
        <code className="bg-slate-100 px-1 rounded">test.ping</code> event against your current URL +
        secret and returns the response status and latency.
      </p>
      <CodeBlock>{`curl -X POST https://api.lintpdf.com/api/v1/webhooks/whk_01.../test \\
  -H "Authorization: Bearer lpdf_live_..."

# Response
{ "delivered": true, "status": 200, "latency_ms": 82 }`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Operational notes</h3>
      <FieldTable
        rows={[
          { name: "HTTPS only", type: "constraint", description: "Plain HTTP URLs are rejected at registration. TLS certificate must validate." },
          { name: "Private-IP blocklist", type: "constraint", description: "Destinations in RFC1918 ranges, 127.0.0.0/8, or ::1/128 are rejected." },
          { name: "Retries", type: "behavior", description: "Failed deliveries retry with exponential backoff at 30s, 2m, 10m, 1h. After four attempts, the event is abandoned." },
          { name: "Timeouts", type: "behavior", description: "Receivers have 10 seconds to respond 2xx. Slower responses count as failures." },
          { name: "Ordering", type: "behavior", description: "No ordering guarantees — use the data.job_id to collate." },
        ]}
      />
    </>
  );
}
