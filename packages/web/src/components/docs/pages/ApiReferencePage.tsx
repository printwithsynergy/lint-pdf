import ApiAuthSection from "./api/ApiAuthSection";
import ApiJobsSection from "./api/ApiJobsSection";
import ApiImportsSection from "./api/ApiImportsSection";
import ApiBrandingSection from "./api/ApiBrandingSection";
import ApiViewerSection from "./api/ApiViewerSection";
import ApiReportsSection from "./api/ApiReportsSection";
import ApiWebhooksSection from "./api/ApiWebhooksSection";
import ApiEnumsSection from "./api/ApiEnumsSection";

export default function ApiReferencePage() {
  return (
    <>
      <h2 className="text-2xl font-bold text-slate-900 mb-4">API Reference</h2>
      <p className="text-slate-600 mb-2">
        Base URL:{" "}
        <code className="bg-slate-100 px-1.5 py-0.5 rounded text-sm font-mono">
          https://api.lintpdf.com
        </code>
      </p>
      <p className="text-slate-500 text-sm mb-8">
        All endpoints return JSON (or PNG for render endpoints). Authenticated
        endpoints require a Bearer token. Every route supports the three
        submission modes: <code className="bg-slate-100 px-1 rounded">engine</code>,
        {" "}<code className="bg-slate-100 px-1 rounded">external</code>, and
        {" "}<code className="bg-slate-100 px-1 rounded">minimal</code>.
      </p>

      <nav className="mb-8 rounded-xl border border-slate-200 p-4 bg-slate-50">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
          On this page
        </p>
        <ul className="grid grid-cols-2 gap-1 text-sm">
          <li><a href="#auth" className="text-brand-700 hover:underline">Authentication &amp; rate limits</a></li>
          <li><a href="#jobs" className="text-brand-700 hover:underline">Jobs</a></li>
          <li><a href="#imports" className="text-brand-700 hover:underline">External imports &amp; mappings</a></li>
          <li><a href="#branding" className="text-brand-700 hover:underline">Branding &amp; domains</a></li>
          <li><a href="#viewer" className="text-brand-700 hover:underline">Viewer</a></li>
          <li><a href="#reports" className="text-brand-700 hover:underline">Reports &amp; share links</a></li>
          <li><a href="#webhooks" className="text-brand-700 hover:underline">Webhooks &amp; check names</a></li>
          <li><a href="#enums" className="text-brand-700 hover:underline">Enum appendix</a></li>
        </ul>
      </nav>

      <ApiAuthSection />
      <ApiJobsSection />
      <ApiImportsSection />
      <ApiBrandingSection />
      <ApiViewerSection />
      <ApiReportsSection />
      <ApiWebhooksSection />
      <ApiEnumsSection />
    </>
  );
}
