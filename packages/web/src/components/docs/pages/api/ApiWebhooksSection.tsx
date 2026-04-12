import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";
import { FieldTable } from "@/components/docs/FieldTable";

export default function ApiWebhooksSection() {
  return (
    <section className="mb-12">
      <h3 id="webhooks" className="text-xl font-bold text-slate-900 mb-3">
        Webhooks &amp; check-name registry
      </h3>
      <p className="text-slate-600 mb-4">
        Webhooks deliver real-time job events to your HTTPS endpoint. Every
        delivery is signed with
        {" "}<code className="bg-slate-100 px-1 rounded">X-LintPDF-Signature</code> using HMAC-SHA256,
        hex-encoded, and prefixed with <code className="bg-slate-100 px-1 rounded">sha256=</code>. Private-IP
        destinations are blocked at registration. Webhooks require the Growth
        plan or above.
      </p>

      <Endpoint
        method="POST"
        path="/api/v1/webhooks"
        description="Register a webhook. url must be HTTPS and must not resolve to a private network. The signing secret is generated server-side."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/webhooks \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-app.com/webhooks/lintpdf",
    "events": ["job.completed", "job.failed"]
  }'`}
        response={`{
  "id": "0e7f6c5b-4a3f-4210-9876-543210fedcba",
  "url": "https://your-app.com/webhooks/lintpdf",
  "events": ["job.completed", "job.failed"],
  "is_active": true,
  "created_at": "2026-04-12T10:30:00Z"
}`}
      />
      <p className="text-slate-600 text-sm mt-2">
        The signing secret is generated server-side at registration and is not
        returned in the response body. Retrieve it from the dashboard (Webhooks
        → Endpoint → Reveal secret). Store it alongside the endpoint URL and
        use it in the signature-validation recipes below.
      </p>

      <Endpoint
        method="GET"
        path="/api/v1/webhooks"
        description="List every webhook endpoint registered for the current tenant."
        auth
        request={`curl https://api.lintpdf.com/api/v1/webhooks \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "webhooks": [
    { "id": "0e7f6c5b-...", "url": "...", "events": [...], "is_active": true,
      "created_at": "2026-04-12T10:30:00Z" }
  ]
}`}
      />

      <Endpoint
        method="PATCH"
        path="/api/v1/webhooks/{webhook_id}"
        description="Update a webhook's URL, events, or active status. All body fields are optional."
        auth
        request={`curl -X PATCH https://api.lintpdf.com/api/v1/webhooks/0e7f6c5b-... \\
  -H "Authorization: Bearer lpdf_live_..." \\
  -H "Content-Type: application/json" \\
  -d '{ "is_active": false }'`}
        response={`{ "id": "0e7f6c5b-...", "is_active": false, ... }`}
      />

      <Endpoint
        method="DELETE"
        path="/api/v1/webhooks/{webhook_id}"
        description="Remove a webhook endpoint. Returns 204."
        auth
        request={`curl -X DELETE https://api.lintpdf.com/api/v1/webhooks/0e7f6c5b-... \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`HTTP/1.1 204 No Content`}
      />

      <Endpoint
        method="POST"
        path="/api/v1/webhooks/{webhook_id}/test"
        description="Send a synthetic test.ping event to the registered URL. Helpful when debugging signature validation."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/webhooks/0e7f6c5b-.../test \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "success": true,
  "status_code": 200,
  "error": "",
  "event": "test.ping"
}`}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Events</h4>
      <FieldTable
        rows={[
          { name: "job.completed", type: "event", description: "Preflight finished. Payload carries job_id, status, profile_id, duration_ms, summary." },
          { name: "job.failed", type: "event", description: "Preflight errored out. Payload carries job_id, status, error message." },
          { name: "test.ping", type: "event", description: "Sent only by the /test endpoint. Never fires in production flows." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Event payload — job.completed</h4>
      <CodeBlock>{`{
  "event": "job.completed",
  "job_id": "d4e5f6a7-1234-4567-89ab-cdef01234567",
  "status": "complete",
  "profile_id": "lintpdf-default",
  "duration_ms": 3480,
  "summary": {
    "total_findings": 7,
    "error_count": 1,
    "warning_count": 4,
    "advisory_count": 2,
    "passed": false,
    "page_count": 12,
    "file_size_bytes": 842139
  }
}`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Event payload — job.failed</h4>
      <CodeBlock>{`{
  "event": "job.failed",
  "job_id": "d4e5f6a7-...",
  "status": "failed",
  "error": "Unsupported PDF version: 2.1"
}`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Request headers</h4>
      <FieldTable
        rows={[
          { name: "X-LintPDF-Event", type: "string", description: "The event type, e.g. job.completed." },
          { name: "X-LintPDF-Signature", type: "string", description: "HMAC-SHA256 of the raw body, hex-encoded, prefixed with sha256=." },
          { name: "Content-Type", type: "string", description: "Always application/json." },
        ]}
      />

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
        description="Full check-name registry keyed by inspection_id."
        auth={false}
        request={`curl https://api.lintpdf.com/api/v1/check-names`}
        response={`{
  "font.not_embedded": {
    "name": "Font Not Embedded",
    "description": "Font is referenced but not embedded in the PDF"
  },
  "image.low_resolution": {
    "name": "Low-Resolution Image",
    "description": "Raster image falls below the profile's effective DPI threshold"
  }
}`}
      />
    </section>
  );
}
