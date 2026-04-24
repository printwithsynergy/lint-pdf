import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";

export const metadata: Metadata = {
  title: "API Reference (All Routes) — LintPDF Admin",
  description:
    "Complete OpenAPI reference for every engine route including admin surface.",
};

/**
 * Admin-only Swagger UI — loads the FULL ``/openapi.json`` from the
 * engine, so every admin-scoped endpoint is visible and try-it-outable.
 *
 * Access is gated by the same authenticated-admin layout that protects
 * the rest of ``/dashboard/admin/*`` (see ``dashboard/admin/layout.tsx``).
 *
 * Tenants get a filtered slice at ``/swagger`` on the marketing site,
 * which hits ``/openapi.tenant.json`` and excludes admin routes.
 */
export default function AdminSwaggerPage() {
  const openapiUrl = `${
    process.env.NEXT_PUBLIC_LINTPDF_API_URL ?? "https://api.lintpdf.com"
  }/openapi.json`;
  return (
    <div className="min-h-screen">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">
            Full API Reference
          </h1>
          <p className="text-sm text-muted-foreground">
            Every route in the engine — tenant-facing and admin. Use the
            Authorize button with your admin key for admin endpoints.
          </p>
        </div>
        <div className="flex gap-2 text-sm">
          <Link
            href="/dashboard/webhooks"
            className="rounded border px-3 py-1 hover:bg-muted"
          >
            Webhooks
          </Link>
          <a
            href="https://lintpdf.com/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded border px-3 py-1 hover:bg-muted"
          >
            Public docs
          </a>
          <Link
            href="/dashboard/admin/postman"
            className="rounded border px-3 py-1 hover:bg-muted"
          >
            Postman (full)
          </Link>
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
              url: ${JSON.stringify(openapiUrl)},
              dom_id: '#swagger-ui',
              deepLinking: true,
              displayOperationId: false,
              defaultModelsExpandDepth: 0,
              docExpansion: 'none',
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
