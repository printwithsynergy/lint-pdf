import { CodeBlock } from "@/components/docs/CodeBlock";
import { Endpoint } from "@/components/docs/Endpoint";

export default function ReportFormatsPage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">
        Report Formats
      </h2>
      <p className="text-slate-600 mb-6">
        Reports can be retrieved in three formats. Use the{" "}
        <code className="bg-slate-100 px-1 rounded text-sm font-mono">
          format
        </code>{" "}
        query parameter on the report endpoint.
      </p>

      <h3 className="font-semibold text-slate-900 mb-3">
        JSON Response Schema
      </h3>
      <CodeBlock>{`{
  "id": "string",
  "status": "complete",
  "verdict": "pass | error",
  "ruleset": "string",
  "file_name": "string",
  "page_count": "number",
  "duration_ms": "number",
  "summary": {
    "total_findings": "number",
    "error": "number",
    "warning": "number",
    "info": "number"
  },
  "findings": [
    {
      "inspection_id": "string",
      "severity": "error | warning | info",
      "message": "string",
      "page": "number"
    }
  ]
}`}</CodeBlock>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">
        PDF Reports &amp; White Label
      </h3>
      <p className="text-slate-600 mb-4">
        PDF reports are white-labeled using your White Label configuration.
        Scale and Enterprise plans can upload a logo, set brand colors, and
        customize footer text. Reports include a summary page, detailed
        findings grouped by severity, and page-level annotations.
      </p>

      <h3 className="font-semibold text-slate-900 mt-8 mb-3">XML Format</h3>
      <p className="text-slate-600 mb-4">
        XML reports follow the same structure as JSON but use XML elements.
        Useful for legacy integrations and enterprise systems that consume
        XML.
      </p>
      <CodeBlock>{`<?xml version="1.0" encoding="UTF-8"?>
<report id="f47ac10b-..." status="complete" verdict="error">
  <ruleset>gwg-sheetfed</ruleset>
  <file-name>document.pdf</file-name>
  <summary total="3" error="1" warning="1" info="1" />
  <findings>
    <finding inspection="font.not_embedded" severity="error" page="1">
      Font 'Helvetica' is not embedded
    </finding>
  </findings>
</report>`}</CodeBlock>
    </>
  );
}
