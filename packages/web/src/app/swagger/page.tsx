import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import { hiddenInOssMetadata } from "@/lib/site-mode";

export const metadata: Metadata = {
  title: "API Reference — LintPDF",
  description:
    "Interactive OpenAPI reference for the LintPDF tenant API. Try requests against every endpoint without leaving your browser.",
  ...hiddenInOssMetadata,
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
    <main className="min-h-screen bg-gradient-to-b from-brand-50/60 to-white pb-24">
      <div className="mx-auto max-w-6xl px-6 pt-16 sm:pt-24">
        <section className="mb-10 sm:mb-12">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="max-w-3xl">
              <h1 className="text-3xl font-bold text-slate-900 sm:text-4xl">
                LintPDF Tenant API
              </h1>
              <p className="mt-4 text-lg text-slate-600">
                Live OpenAPI reference for every endpoint your API key can
                call. Admin-only routes are excluded —{" "}
                <Link
                  className="text-brand-700 underline hover:text-brand-900"
                  href="/docs/webhooks"
                >
                  webhooks
                </Link>
                ,{" "}
                <Link
                  className="text-brand-700 underline hover:text-brand-900"
                  href="/docs/job-state"
                >
                  job state
                </Link>
                , and{" "}
                <a
                  className="text-brand-700 underline hover:text-brand-900"
                  href="https://app.lintpdf.com/dashboard/api-keys"
                >
                  API keys
                </a>{" "}
                are the usual starting points.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              <Link
                href="/docs/postman"
                className="inline-flex items-center rounded-lg border border-brand-200 bg-white px-4 py-2 font-semibold text-brand-700 transition-colors hover:bg-brand-50"
              >
                Postman collection
              </Link>
              <Link
                href="/docs"
                className="inline-flex items-center rounded-lg border border-brand-200 bg-white px-4 py-2 font-semibold text-brand-700 transition-colors hover:bg-brand-50"
              >
                Docs home
              </Link>
            </div>
          </div>
        </section>
      </div>

      {/* Swagger UI injects its own stylesheet via the CDN link below. */}
      {/* eslint-disable-next-line @next/next/no-css-tags */}
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"
      />
      <div
        id="swagger-ui"
        className="mx-auto max-w-7xl rounded-2xl border border-slate-200 bg-white shadow-sm"
      />
      <Script
        src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"
        strategy="afterInteractive"
      />
      <Script id="swagger-boot" strategy="afterInteractive">
        {`
          (function boot() {
            // The 'afterInteractive' strategy may run before OR after the
            // CDN bundle finishes, and 'load' may have fired already, so
            // neither window.addEventListener('load', ...) nor a one-shot
            // check is reliable. Poll with a bounded retry count until
            // SwaggerUIBundle is available, then init once.
            var tries = 0;
            function tryInit() {
              if (window.__lintpdfSwaggerInited__) return;
              if (!window.SwaggerUIBundle) {
                if (tries++ < 200) { setTimeout(tryInit, 50); return; }
                console.error('SwaggerUIBundle failed to load from CDN');
                return;
              }
              window.__lintpdfSwaggerInited__ = true;
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
            }
            tryInit();
          })();
        `}
      </Script>
    </main>
  );
}
