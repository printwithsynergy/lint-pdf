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
        Every job-submit response (<code className="bg-slate-100 px-1 rounded">POST /api/v1/jobs</code>
        {" "}and the vanity <code className="bg-slate-100 px-1 rounded">/endpoints/{`{slug}`}/submit</code>)
        carries the following headers. Use them to back off gracefully before
        a <code className="bg-slate-100 px-1 rounded">429</code> is returned.
      </p>
      <CodeBlock>{`X-RateLimit-Limit: 5000           # Files included in the current billing cycle
X-RateLimit-Used: 412             # Files consumed so far this cycle
X-RateLimit-Remaining: 4588       # Files remaining before overage kicks in

# The next four only appear once you've exceeded the included allowance:
X-RateLimit-Overage: true              # Boolean flag — present = in overage
X-RateLimit-Overage-Count: 12          # Files billed at the overage rate this cycle
X-RateLimit-Overage-Rate-Cents: 10     # Per-file overage cost in cents
X-RateLimit-Overage-Cost-Cents: 120    # Accrued overage cost this cycle`}</CodeBlock>
      <p className="text-slate-600 text-sm mt-2">
        The overage headers are omitted entirely while you are inside your
        plan&apos;s included allowance — treat their absence as &ldquo;no overage&rdquo;.
      </p>

      <h4 className="font-semibold text-slate-900 mt-6 mb-2">Error envelope</h4>
      <p className="text-slate-600 mb-3">
        Errors use FastAPI&apos;s default JSON shape. Status codes follow HTTP
        semantics; the <code className="bg-slate-100 px-1 rounded">detail</code> field carries the
        human-readable message.
      </p>
      <CodeBlock>{`HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "detail": "preflight_source must be one of: engine, external, minimal"
}`}</CodeBlock>
      <p className="text-slate-600 text-sm mt-2">
        Request-validation errors (malformed body, missing required fields)
        follow FastAPI&apos;s structured form with
        {" "}<code className="bg-slate-100 px-1 rounded">detail</code> as an array of
        {" "}<code className="bg-slate-100 px-1 rounded">{`{ loc, msg, type }`}</code> entries.
      </p>
    </section>
  );
}
