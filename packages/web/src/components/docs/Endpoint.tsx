import { CodeBlock } from "./CodeBlock";

const methodColors: Record<string, string> = {
  GET: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  POST: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  PUT: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  DELETE: "bg-red-500/10 text-red-600 border-red-500/20",
};

export function Endpoint({
  method,
  path,
  description,
  auth,
  request,
  response,
}: {
  method: string;
  path: string;
  description: string;
  auth: boolean;
  request: string;
  response: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 overflow-hidden mb-6">
      <div className="flex items-center gap-3 border-b border-slate-200 px-6 py-4 bg-slate-50">
        <span
          className={`rounded border px-2.5 py-0.5 text-xs font-bold ${methodColors[method] ?? ""}`}
        >
          {method}
        </span>
        <code className="text-sm text-slate-800 font-mono">{path}</code>
        {auth && (
          <span className="ml-auto rounded bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700 border border-amber-500/20">
            API Key required
          </span>
        )}
      </div>
      <div className="px-6 py-4">
        <p className="text-sm text-slate-600 mb-4">{description}</p>
        <div className="mb-4">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Request
          </h4>
          <CodeBlock>{request}</CodeBlock>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Response
          </h4>
          <CodeBlock>{response}</CodeBlock>
        </div>
      </div>
    </div>
  );
}
