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
            href="https://lintpdf.com/docs/postman"
            target="_blank"
            rel="noreferrer"
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
      <div id="swagger-ui" />
      <Script
        src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"
        strategy="afterInteractive"
      />
      <Script id="swagger-boot" strategy="afterInteractive">
        {`
          window.addEventListener('load', function () {
            if (!window.SwaggerUIBundle) {
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
    </div>
  );
}
