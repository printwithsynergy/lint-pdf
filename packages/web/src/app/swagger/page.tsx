import type { Metadata } from "next";
import Script from "next/script";

export const metadata: Metadata = {
  title: "API Reference — LintPDF",
  description:
    "Interactive OpenAPI reference for the LintPDF tenant API. Try requests against every endpoint without leaving your browser.",
};

/**
 * Public, tenant-facing Swagger UI. Fetches the `/openapi.tenant.json`
 * slice from the engine, which excludes ``/admin/*`` and trial-submit
 * plumbing so prospects don't see routes they can't call.
 *
 * Admin-only Swagger lives under the authenticated dashboard at
 * ``/dashboard/admin/swagger`` and fetches the full ``/openapi.json``.
 *
 * The CDN loader + container pattern keeps the bundle off our
 * Next.js build and lets us upgrade Swagger UI without a deploy.
 */
export default function SwaggerPage() {
  return (
    <main className="min-h-screen bg-white">
      <div className="mx-auto max-w-screen-2xl px-4 py-6">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              LintPDF Tenant API
            </h1>
            <p className="text-sm text-slate-600">
              Live OpenAPI reference for every endpoint your API key can
              call. Admin-only routes are excluded —{" "}
              <a className="text-blue-600 underline" href="/docs/webhooks">
                webhooks
              </a>
              ,{" "}
              <a className="text-blue-600 underline" href="/docs/job-state">
                job state
              </a>
              , and{" "}
              <a
                className="text-blue-600 underline"
                href="https://app.lintpdf.com/dashboard/api-keys"
              >
                API keys
              </a>{" "}
              are the usual starting points.
            </p>
          </div>
          <div className="flex gap-2 text-sm">
            <a
              href="/docs/postman"
              className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-50"
            >
              Postman collection
            </a>
            <a
              href="/docs"
              className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-50"
            >
              Docs home
            </a>
          </div>
        </div>
      </div>

      {/* Swagger UI injects its own stylesheet via the CDN link below. */}
      {/* eslint-disable-next-line @next/next/no-css-tags */}
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"
      />
      <div id="swagger-ui" />
      <Script
        src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"
        strategy="afterInteractive"
      />
      <Script id="swagger-boot" strategy="afterInteractive">
        {`
          window.addEventListener('load', function () {
            if (!window.SwaggerUIBundle) {
              // Give the CDN script one more tick.
              setTimeout(arguments.callee, 50);
              return;
            }
            window.SwaggerUIBundle({
              url: 'https://api.lintpdf.com/openapi.tenant.json',
              dom_id: '#swagger-ui',
              deepLinking: true,
              displayOperationId: false,
              defaultModelsExpandDepth: 0,
              docExpansion: 'list',
              filter: true,
              tryItOutEnabled: true,
              persistAuthorization: true
            });
          });
        `}
      </Script>
    </main>
  );
}
