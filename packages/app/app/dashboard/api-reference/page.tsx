import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";

export const metadata: Metadata = {
  title: "API Reference — LintPDF",
  description:
    "Interactive OpenAPI reference for every tenant-facing LintPDF route.",
};

/**
 * Tenant Swagger inside the authenticated dashboard. Identical payload
 * to the marketing-site ``/swagger`` page (same ``/openapi.tenant.json``
 * slice), but embedded in the dashboard chrome so customers can keep
 * their auth cookie + API key side by side while experimenting.
 *
 * Admin-only Swagger lives at ``/dashboard/admin/swagger``.
 */
export default function TenantApiReferencePage() {
  const openapiUrl = `${
    process.env.NEXT_PUBLIC_LINTPDF_API_URL ?? "https://api.lintpdf.com"
  }/openapi.tenant.json`;
  return (
    <div className="min-h-screen">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">API Reference</h1>
          <p className="text-sm text-muted-foreground">
            Every endpoint your API key can call, backed by the live
            OpenAPI spec. Use the Authorize button to paste your key and
            try requests directly from this page.
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <Link
            href="/dashboard/api-keys"
            className="rounded border px-3 py-1 hover:bg-muted"
          >
            API keys
          </Link>
          <Link
            href="/dashboard/webhooks"
            className="rounded border px-3 py-1 hover:bg-muted"
          >
            Webhooks
          </Link>
          <a
            href="/postman/lintpdf-tenant.postman_collection.json"
            download="lintpdf-tenant.postman_collection.json"
            className="rounded border px-3 py-1 hover:bg-muted"
          >
            Postman collection
          </a>
          <a
            href="https://lintpdf.com/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded border px-3 py-1 hover:bg-muted"
          >
            Public docs
          </a>
        </div>
      </div>

      {/* eslint-disable-next-line @next/next/no-css-tags */}
      <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css"
      />
      <div id="swagger-ui">
        <p className="text-sm text-muted-foreground">
          Loading the OpenAPI spec…{" "}
          <a
            href={openapiUrl}
            target="_blank"
            rel="noreferrer"
            className="underline"
          >
            Open spec directly
          </a>{" "}
          if this never finishes.
        </p>
      </div>
      <Script
        src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"
        strategy="afterInteractive"
      />
      <Script id="swagger-boot" strategy="afterInteractive">
        {`
          (function () {
            var attempts = 0;
            function boot() {
              attempts += 1;
              if (!window.SwaggerUIBundle) {
                if (attempts > 100) {
                  var el = document.getElementById('swagger-ui');
                  if (el) el.innerHTML = '<p style="color:#b91c1c">Swagger UI bundle failed to load. Check your network connection or try the public docs link above.</p>';
                  return;
                }
                setTimeout(boot, 50);
                return;
              }
              try {
                window.SwaggerUIBundle({
                  url: ${JSON.stringify(openapiUrl)},
                  dom_id: '#swagger-ui',
                  deepLinking: true,
                  displayOperationId: false,
                  defaultModelsExpandDepth: 0,
                  docExpansion: 'list',
                  filter: true,
                  tryItOutEnabled: true,
                  persistAuthorization: true
                });
              } catch (err) {
                console.error('Swagger UI boot failed', err);
                var el = document.getElementById('swagger-ui');
                if (el) el.innerHTML = '<p style="color:#b91c1c">Swagger UI failed to initialize. See browser console for details.</p>';
              }
            }
            boot();
          })();
        `}
      </Script>
    </div>
  );
}
