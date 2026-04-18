import { CodeBlock } from "@/components/docs/CodeBlock";
import { FieldTable } from "@/components/docs/FieldTable";

export default function WebhooksPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Webhooks</h2>
      <p className="text-slate-600 mb-6">
        Webhooks deliver real-time events to your HTTPS endpoint. Every
        delivery is HMAC-SHA256 signed and every dispatch is recorded in a
        per-tenant audit log you can inspect and replay. See the{" "}
        <a className="text-blue-600 underline" href="/swagger">
          Swagger reference
        </a>{" "}
        for the exact request/response shapes.
      </p>

      <h3 className="font-semibold text-slate-900 mb-3">Registering a webhook</h3>
      <CodeBlock>{`curl -X POST https://api.lintpdf.com/api/v1/webhooks \\
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
  }'`}</CodeBlock>
      <p className="text-slate-600 text-sm mt-2">
        <code className="bg-slate-100 px-1 rounded">events</code> may be empty
        to subscribe to every event. The signing secret is generated
        server-side at registration; reveal it from the dashboard (Webhooks →
        Endpoint → Reveal secret).
      </p>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Event catalog</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-200 mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Event
              </th>
              <th className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Fires when
              </th>
            </tr>
          </thead>
          <tbody>
            {(
              [
                ["job.completed", "Preflight completes successfully. Payload includes summary counts."],
                ["job.failed", "Engine exception or external-import parse failure."],
                ["job.state_changed", "Umbrella event. Fires whenever GET /jobs/{id}/state would differ. Payload carries the full /state digest inline plus a 'reason' tag."],
                ["approval.chain.started", "Approval chain attached + step 0 kicked off."],
                ["approval.step.started", "Step enters active review."],
                ["approval.step.decided", "Approver submits a decision + optional notes."],
                ["approval.chain.completed", "Final step approved → chain success."],
                ["approval.chain.rejected", "Any step rejected → chain terminates."],
                ["approval.chain.cancelled", "Chain manually cancelled."],
                ["approval.chain.timeout", "Step expired without decision."],
                ["annotation.created", "Reviewer drew a rect/circle/arrow/note/freehand on a page."],
                ["annotation.deleted", "Annotation was removed."],
                ["comment.created", "New comment on an annotation thread."],
                ["verdict.changed", "Manual verdict pass/fail flipped. Payload: previous, current, verdict_by, notes."],
                ["report.minted", "POST /jobs/{id}/reports returned at least one URL. Payload lists every minted format + URL + expires_at."],
                ["report.expired", "Report token's expires_at passed and the nightly sweep deleted it. One event per token."],
                ["share_link.visited", "First touch per (token, visitor_email) pair. Subsequent visits update last_seen_at silently."],
                ["billing.file_quota.low", "Monthly file pool dropped from >10% to ≤10% on deduction. One-shot per crossing."],
                ["billing.file_quota.exhausted", "Submit rejected with 402 — pool empty + overage off."],
                ["billing.ai_credits.low", "AI credits crossed the 10% watermark (CREDIT_PACKAGE billing mode only)."],
                ["billing.ai_credits.exhausted", "Credit package drained to zero."],
                ["tenant.plan.changed", "Admin set a new plan value. Payload: previous_plan, new_plan."],
              ] as Array<[string, string]>
            ).map(([event, desc]) => (
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
      <p className="text-slate-600 text-sm mb-6">
        Sample payloads for every event live in{" "}
        <a
          className="text-blue-600 underline"
          href="https://github.com/thinkneverland/lint-pdf/tree/main/docs/examples/webhook-events"
          target="_blank"
          rel="noreferrer"
        >
          <code>docs/examples/webhook-events/</code>
        </a>
        .
      </p>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        Delivery semantics
      </h3>
      <p className="text-slate-600 mb-3">
        Every dispatch creates a <code className="bg-slate-100 px-1 rounded">WebhookDelivery</code>{" "}
        row BEFORE the first attempt, so even a worker crash leaves a
        replayable trail.
      </p>
      <FieldTable
        rows={[
          { name: "HTTPS only", type: "constraint", description: "Plain HTTP URLs are rejected at registration. TLS certificate must validate." },
          { name: "Private-IP blocklist", type: "constraint", description: "Destinations in RFC1918 ranges, 127.0.0.0/8, or ::1/128 are rejected." },
          { name: "Retry (5xx / timeout)", type: "behavior", description: "Celery self.retry() fires with exponential backoff: min(base * 2**(attempt-1), max_delay). Per-endpoint config overrides the platform defaults." },
          { name: "No retry (4xx)", type: "behavior", description: "Caller rejected the payload shape — retrying the same body won't fix it. Marked success=false and left in the audit log." },
          { name: "Timeout", type: "behavior", description: "Receivers have 10 seconds to respond 2xx. Slower responses count as failures (and are retried per the backoff policy above)." },
          { name: "Ordering", type: "behavior", description: "No ordering guarantees — use data.job_id or the job.state_changed snapshot to collate." },
          { name: "Audit retention", type: "behavior", description: "delivery_retention_days (nullable, 1-365, default null = forever). retention_overrides lets you keep billing events longer than annotation events." },
        ]}
      />

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Retry config fields</h4>
      <FieldTable
        rows={[
          { name: "max_retries", type: "int (0–10)", default: "3", description: "Upper bound on retry attempts. Capped platform-wide at 10." },
          { name: "retry_base_delay_seconds", type: "int (1–600)", default: "5", description: "Initial retry delay. Subsequent retries double, capped by retry_max_delay_seconds." },
          { name: "retry_max_delay_seconds", type: "int (1–3600)", default: "300", description: "Ceiling on the exponential backoff — prevents aggressive max_retries from sleeping absurdly long." },
          { name: "delivery_retention_days", type: "int (1–365)", default: "null (forever)", description: "Nightly sweep deletes audit rows older than this for the endpoint." },
          { name: "retention_overrides", type: "object", default: "{}", description: 'Per-event retention overrides, e.g. {"billing.*": 365}. Keys are fnmatch globs; longest-match wins.' },
        ]}
      />

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        Audit + replay API
      </h3>
      <p className="text-slate-600 mb-3">
        Every delivery (including failures) is queryable:
      </p>
      <CodeBlock>{`# List recent deliveries, newest first. Filter to failures with ?success=false.
GET  /api/v1/webhooks/deliveries?webhook_id={id}&page=1&page_size=50

# Inspect the signed payload that was POSTed.
GET  /api/v1/webhooks/deliveries/{delivery_id}

# Re-fire a past delivery. Creates a NEW audit row; original is preserved.
# Returns 409 if the endpoint is inactive or deleted.
POST /api/v1/webhooks/deliveries/{delivery_id}/replay`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        Signature validation
      </h3>
      <p className="text-slate-600 mb-3">
        Every delivery carries an{" "}
        <code className="bg-slate-100 px-1 rounded">X-LintPDF-Signature</code>{" "}
        header in the form{" "}
        <code className="bg-slate-100 px-1 rounded">sha256=&lt;hex&gt;</code>.
        Compute an HMAC-SHA256 over the raw request body with your registered
        secret and compare using a constant-time function.
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

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        Test deliveries
      </h3>
      <p className="text-slate-600 mb-3">
        Use the test endpoint while wiring up your receiver. It delivers a
        signed{" "}
        <code className="bg-slate-100 px-1 rounded">test.ping</code> event
        against your current URL + secret, writes a{" "}
        <code className="bg-slate-100 px-1 rounded">WebhookDelivery</code>{" "}
        audit row so it's visible in the replay surface, and returns the
        response status inline.
      </p>
      <CodeBlock>{`curl -X POST https://api.lintpdf.com/api/v1/webhooks/{webhook_id}/test \\
  -H "Authorization: Bearer lpdf_live_..."

# Response
{ "success": true, "status_code": 200, "error": null, "event": "test.ping" }`}</CodeBlock>
    </>
  );
}
