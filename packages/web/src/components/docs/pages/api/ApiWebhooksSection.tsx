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
    "events": ["job.state_changed", "approval.chain.completed"],
    "max_retries": 5,
    "retry_base_delay_seconds": 2,
    "retry_max_delay_seconds": 60,
    "delivery_retention_days": 30,
    "retention_overrides": { "billing.*": 365 }
  }'`}
        response={`{
  "id": "0e7f6c5b-4a3f-4210-9876-543210fedcba",
  "url": "https://your-app.com/webhooks/lintpdf",
  "events": ["job.state_changed", "approval.chain.completed"],
  "is_active": true,
  "created_at": "2026-04-12T10:30:00Z",
  "max_retries": 5,
  "retry_base_delay_seconds": 2,
  "retry_max_delay_seconds": 60,
  "delivery_retention_days": 30,
  "retention_overrides": { "billing.*": 365 }
}`}
      />
      <FieldTable
        rows={[
          { name: "url", type: "string (HTTPS URL)", required: true, description: "Public endpoint to POST events to. Private networks rejected at registration." },
          { name: "events", type: "string[]", default: "[job.completed, job.failed]", description: "Subscription list. Empty [] subscribes to every event. See the catalog below." },
          { name: "max_retries", type: "int (0-10)", default: "3", description: "Retry budget for 5xx/timeout failures. Null inherits the platform default. Capped at 10 platform-wide." },
          { name: "retry_base_delay_seconds", type: "int (1-600)", default: "5", description: "Initial retry delay. Subsequent retries double exponentially, capped by retry_max_delay_seconds." },
          { name: "retry_max_delay_seconds", type: "int (1-3600)", default: "300", description: "Exponential-backoff ceiling. Keeps a high max_retries from waiting absurdly long." },
          { name: "delivery_retention_days", type: "int (1-365)", default: "null (forever)", description: "Nightly sweep deletes WebhookDelivery audit rows older than this for this endpoint. Null keeps forever." },
          { name: "retention_overrides", type: "object", default: "{}", description: 'Per-event retention overrides, e.g. {"billing.*": 365, "annotation.*": 7}. Keys are fnmatch globs matched against event names; longest-match wins.' },
        ]}
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

      <h4 className="font-semibold text-slate-900 mt-8 mb-2">Event catalog</h4>
      <p className="text-slate-600 mb-3">
        The full list of events your endpoint can subscribe to. See the
        dedicated <a href="/docs/webhooks" className="text-blue-600 underline">Webhooks</a> page for delivery semantics, replay, and sample payloads.
      </p>
      <FieldTable
        rows={[
          { name: "job.completed", type: "event", description: "Preflight completes successfully." },
          { name: "job.failed", type: "event", description: "Engine exception or import parse failure." },
          { name: "job.state_changed", type: "event", description: "Umbrella event. Fires whenever GET /jobs/{id}/state would differ. Payload carries the full /state digest inline plus a 'reason' tag." },
          { name: "approval.chain.started", type: "event", description: "Approval chain attached + step 0 kicked off." },
          { name: "approval.step.started", type: "event", description: "Step enters active review." },
          { name: "approval.step.decided", type: "event", description: "Approver submits a decision + optional notes." },
          { name: "approval.chain.completed", type: "event", description: "Final step approved → chain success." },
          { name: "approval.chain.rejected", type: "event", description: "Any step rejected → chain terminates." },
          { name: "approval.chain.cancelled", type: "event", description: "Chain manually cancelled." },
          { name: "approval.chain.timeout", type: "event", description: "Step expired without decision." },
          { name: "annotation.created", type: "event", description: "Reviewer drew a rect/circle/arrow/note/freehand." },
          { name: "annotation.deleted", type: "event", description: "Annotation removed." },
          { name: "comment.created", type: "event", description: "New comment on an annotation thread." },
          { name: "verdict.changed", type: "event", description: "Manual verdict pass/fail flipped. Payload: previous, current, verdict_by, notes." },
          { name: "report.minted", type: "event", description: "POST /jobs/{id}/reports returned at least one URL. Payload lists every minted format + URL + expires_at." },
          { name: "report.expired", type: "event", description: "Report token's expires_at passed and the nightly sweep deleted it. One event per token." },
          { name: "share_link.visited", type: "event", description: "First touch per (token, visitor_email) pair. Subsequent visits update last_seen_at silently." },
          { name: "billing.file_quota.low", type: "event", description: "Monthly file pool dropped from >10% to ≤10% on deduction. One-shot per crossing." },
          { name: "billing.file_quota.exhausted", type: "event", description: "Submit rejected with 402 — pool empty + overage off." },
          { name: "billing.ai_credits.low", type: "event", description: "AI credits crossed the 10% watermark (CREDIT_PACKAGE billing mode only)." },
          { name: "billing.ai_credits.exhausted", type: "event", description: "Credit package drained to zero." },
          { name: "tenant.plan.changed", type: "event", description: "Admin PATCH /admin/tenants/{id}/plan set a new plan value. Payload: previous_plan, new_plan." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-8 mb-2">Delivery audit + replay</h4>
      <p className="text-slate-600 mb-3">
        Every dispatched event lands in the <code className="bg-slate-100 px-1 rounded">webhook_deliveries</code> table with the exact JSON body LintPDF signed. A failed endpoint no longer means a lost event — operators can inspect and replay any past delivery.
      </p>
      <Endpoint
        method="GET"
        path="/api/v1/webhooks/deliveries"
        description="List delivery attempts newest-first. Filter with ?webhook_id=, ?event=, ?success=false. Paginates via ?page= + ?page_size= (default 50, max 200)."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/webhooks/deliveries?success=false&page_size=25" \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "deliveries": [
    {
      "id": "...",
      "webhook_id": "...",
      "event": "job.state_changed",
      "url": "https://your-app.com/webhooks/lintpdf",
      "attempt_count": 1,
      "final_status_code": 503,
      "success": false,
      "last_error": "HTTP 503",
      "created_at": "2026-04-18T02:11:00Z",
      "delivered_at": "2026-04-18T02:11:02Z"
    }
  ],
  "total": 1, "page": 1, "page_size": 25
}`}
      />
      <Endpoint
        method="GET"
        path="/api/v1/webhooks/deliveries/{delivery_id}"
        description="Fetch one delivery row + the exact signed payload we POSTed."
        auth
        request={`curl "https://api.lintpdf.com/api/v1/webhooks/deliveries/..." \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`{
  "id": "...", "event": "job.state_changed", "success": false,
  "payload": { "reason": "verdict.changed", "job": { "...": "..." } }
}`}
      />
      <Endpoint
        method="POST"
        path="/api/v1/webhooks/deliveries/{delivery_id}/replay"
        description="Re-fire a past delivery against the original endpoint. Creates a NEW WebhookDelivery row; the original is preserved for audit history. Returns 409 if the endpoint is inactive or deleted."
        auth
        request={`curl -X POST https://api.lintpdf.com/api/v1/webhooks/deliveries/.../replay \\
  -H "Authorization: Bearer lpdf_live_..."`}
        response={`HTTP/1.1 201 Created
{
  "id": "<new-delivery-id>",
  "event": "job.state_changed",
  "attempt_count": 0,
  "success": false,
  "payload": { "...": "same as original" }
}`}
      />

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
