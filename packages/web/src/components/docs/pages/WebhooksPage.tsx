import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";

export default function WebhooksPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Webhooks</h2>
      <p className="text-slate-600 mb-6">
        Webhooks are webhook callbacks. Register an endpoint and LintPDF will
        POST event payloads when files finish processing. No polling required.
      </p>

      <h3 className="font-semibold text-slate-900 mb-3">
        Registering a Webhook
      </h3>
      <CodeBlock>{`curl -X POST https://api.lintpdf.com/api/v1/webhooks \\
  -H "Authorization: Bearer lpdf_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["job.complete", "job.error"]
  }'`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">Event Types</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 px-3 text-slate-500 font-medium">
                Event
              </th>
              <th className="text-left py-2 px-3 text-slate-500 font-medium">
                Description
              </th>
            </tr>
          </thead>
          <tbody>
            {[
              [
                "job.complete",
                "File processing complete. Includes Report summary and findings.",
              ],
              [
                "job.error",
                "File has Error findings. Includes Report with critical issues.",
              ],
              ["job.pass", "File passed all Checks. Pass."],
              [
                "job.failed",
                "Processing failed (corrupt file, timeout). Includes error message.",
              ],
              ["usage.warning", "Account reached 80% of monthly file limit."],
              ["usage.cap_reached", "Overage spending cap has been reached."],
            ].map(([event, desc]) => (
              <tr key={event} className="border-b border-slate-100">
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

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        Webhook Payload
      </h3>
      <CodeBlock>{`{
  "event": "job.complete",
  "timestamp": "2026-03-15T10:30:01Z",
  "data": {
    "id": "f47ac10b-...",
    "verdict": "error",
    "ruleset": "gwg-sheetfed",
    "file_name": "document.pdf",
    "summary": {
      "total_findings": 3,
      "error": 1,
      "warning": 1,
      "info": 1
    }
  }
}`}</CodeBlock>
    </>
  );
}
