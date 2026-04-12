import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";

export default function ApiWebhooksSection() {
  return (
    <section className="mb-12">
      <h3 id="webhooks" className="text-xl font-bold text-slate-900 mb-3">
        Webhooks &amp; check-name registry
      </h3>
      <p className="text-slate-600 mb-4">
        Webhooks deliver real-time job events to your HTTPS endpoint. Every
        delivery is signed with
        {" "}<code className="bg-slate-100 px-1 rounded">X-LintPDF-Signature</code> using HMAC-SHA256.
        Private-IP destinations are blocked at registration.
      </p>

      <Endpoint
        method="POST"
        path="/api/v1/webhooks"
        description="Register a webhook. url must be HTTPS and must not resolve to a private network."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/webhooks \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-app.com/webhooks/lintpdf",
    "events": ["job.completed", "job.failed"],
    "secret": "whsec_random_value"
  }'`}
        response={`{ "id": "whk_01HXY...", "url": "...", "events": [...], "active": true }`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/webhooks/{id}/test"
        description="Send a synthetic test.ping event to the registered URL. Helpful when debugging signature validation."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/webhooks/whk_01.../test \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{ "delivered": true, "status": 200, "latency_ms": 82 }`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Event payload</h4>
      <CodeBlock>{`{
  "event": "job.completed",
  "timestamp": "2026-04-12T10:30:01Z",
  "data": {
    "job_id": "d4e5f6a7-...",
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

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Signature validation — Python</h4>
      <CodeBlock>{`import hmac, hashlib

def valid(body: bytes, header: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={mac}", header)`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Signature validation — Node.js</h4>
      <CodeBlock>{`import { createHmac, timingSafeEqual } from "node:crypto";

export function valid(body: Buffer, header: string, secret: string) {
  const mac = "sha256=" + createHmac("sha256", secret).update(body).digest("hex");
  const a = Buffer.from(mac);
  const b = Buffer.from(header);
  return a.length === b.length && timingSafeEqual(a, b);
}`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Check-name registry</h4>
      <p className="text-slate-600 mb-3">
        Unauthenticated, cache-aggressive endpoint mapping every engine
        {" "}<code className="bg-slate-100 px-1 rounded">inspection_id</code> to a human-readable name and
        description. Safe to cache for 24h in your client.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/check-names"
        description="Full check-name registry."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/check-names`}
        response={`{
  "checks": [
    { "id": "font.not_embedded", "name": "Font Not Embedded",
      "description": "Font is referenced but not embedded in the PDF" }
  ]
}`}
      />
    </section>
  );
}
