import { CodeBlock } from "@/components/docs/CodeBlock";

export default function ApiAuthSection() {
  return (
    <section className="mb-12">
      <h3 id="auth" className="text-xl font-bold text-slate-900 mb-3">
        Authentication &amp; rate limits
      </h3>
      <p className="text-slate-600 mb-4">
        All authenticated endpoints require a Bearer token issued from the
        Dashboard. Keys are prefixed <code className="bg-slate-100 px-1 rounded">lpdf_live_</code> for
        production and <code className="bg-slate-100 px-1 rounded">lpdf_test_</code> for sandbox.
      </p>
      <CodeBlock>{`Authorization: Bearer lpdf_live_...`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Rate-limit headers</h4>
      <p className="text-slate-600 mb-3">
        Every authenticated response carries the following headers. Use them to
        back off gracefully before a <code className="bg-slate-100 px-1 rounded">429</code> is returned.
      </p>
      <CodeBlock>{`X-RateLimit-Limit: 5000           # Requests allowed per rolling minute
X-RateLimit-Used: 412             # Consumed so far
X-RateLimit-Remaining: 4588       # Remaining before throttle
X-RateLimit-Overage: 0            # Billable overage files this cycle
X-RateLimit-Overage-Count: 0      # Number of overage events
X-RateLimit-Overage-Rate-Cents: 10   # Cost in cents per overage file
X-RateLimit-Overage-Cost-Cents: 0    # Cost incurred this cycle`}</CodeBlock>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Error envelope</h4>
      <p className="text-slate-600 mb-3">
        Errors return a JSON envelope. Status codes follow HTTP semantics; the
        <code className="bg-slate-100 px-1 rounded">code</code> field is the programmatic identifier.
      </p>
      <CodeBlock>{`{
  "error": {
    "code": "invalid_preflight_source",
    "message": "preflight_source must be one of: engine, external, minimal",
    "status": 422
  }
}`}</CodeBlock>
    </section>
  );
}
