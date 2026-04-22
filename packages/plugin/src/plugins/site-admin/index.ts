/**
 * Site-wide administration plugin — SUPER_ADMIN only.
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

// ---------------------------------------------------------------------------
// Helper: proxy fetch to the LintPDF engine admin API
// ---------------------------------------------------------------------------

function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const baseUrl = (
    process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com"
  ).replace(/\/$/, "");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const adminKey = process.env.LINTPDF_ADMIN_API_KEY;
  if (adminKey) {
    headers["X-Admin-Key"] = adminKey;
  }
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export const lintpdfSiteAdminPlugin: PixieDustPlugin = {
  name: "lintpdf-site-admin",
  version: "0.2.0",
  description: "Site-wide administration for LintPDF — super admin only",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("site-admin:access", ["SUPER_ADMIN"]);

    // Navigation — admin section (renders under the "Admin" sidebar heading,
    // role-gated to SUPER_ADMIN by Pixie Dust). Previously used section: "global"
    // which the DashboardSidebar filters into the normal "Menu" group, leaking
    // super-admin routes to tenant users.
    // Admin nav items — subgroups rendered by pixie-dust-dashboard
    // ≥1.18.3 via SerializedNavItem.group. Items without a group
    // (e.g. Documentation at the bottom) render flat at the section
    // root per the backward-compat path.
    ctx.addNavItem({
      label: "All Tenants",
      href: "/dashboard/admin/tenants",
      icon: "building-2",
      section: "admin",
      group: "Operations",
      order: 10,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "All Jobs",
      href: "/dashboard/admin/jobs",
      icon: "inbox",
      section: "admin",
      group: "Operations",
      order: 20,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Preflight Audit",
      href: "/dashboard/admin/audit",
      icon: "search",
      section: "admin",
      group: "Operations",
      order: 25,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "System Health",
      href: "/dashboard/admin/health",
      icon: "zap",
      section: "admin",
      group: "Platform",
      order: 30,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Tile Warming",
      href: "/dashboard/admin/warming",
      icon: "map",
      section: "admin",
      group: "Platform",
      order: 35,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Appearance",
      href: "/dashboard/admin/appearance",
      icon: "palette",
      section: "admin",
      group: "Branding",
      order: 40,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Branding",
      href: "/dashboard/admin/branding",
      icon: "paintbrush",
      section: "admin",
      group: "Branding",
      order: 41,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Metered Billing",
      href: "/dashboard/admin/billing",
      icon: "credit-card",
      section: "admin",
      group: "Platform",
      order: 45,
      requiredRole: "SUPER_ADMIN",
    });
    // Admin-scoped Swagger: loads the FULL openapi.json so super-admins
    // can exercise every route (including /api/v1/admin/*). The
    // tenant-facing slice lives under /dashboard/api-reference + the
    // marketing-site /swagger, which both read /openapi.tenant.json.
    ctx.addPage({
      path: "/dashboard/admin/swagger",
      title: "API Reference (All)",
      layout: "dashboard",
    });
    ctx.addNavItem({
      label: "API Reference (All)",
      href: "/dashboard/admin/swagger",
      icon: "code",
      section: "admin",
      group: "API & Integrations",
      order: 46,
      requiredRole: "SUPER_ADMIN",
    });
    // Cross-tenant views — group by tenant, grant super-admin access to
    // every tenant's API keys, webhook endpoints, and report tokens.
    ctx.addNavItem({
      label: "API Keys (All)",
      href: "/dashboard/admin/api-keys",
      icon: "lock",
      section: "admin",
      group: "API & Integrations",
      order: 50,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Webhooks (All)",
      href: "/dashboard/admin/webhook-endpoints",
      icon: "bell",
      section: "admin",
      group: "API & Integrations",
      order: 51,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Reports (All)",
      href: "/dashboard/admin/reports",
      icon: "file-text",
      section: "admin",
      group: "API & Integrations",
      order: 52,
      requiredRole: "SUPER_ADMIN",
    });
    // Admin documentation — landing + per-chapter rendering lives at
    // /dashboard/admin/docs and /dashboard/admin/docs/{slug}, backed by
    // packages/app/content/docs-admin/.
    // Admin documentation lives under the same "admin" sidebar section (PD's
    // NavItem.section enum is "main" | "admin" | "tenant" | "global" — no
    // custom keys), rendered at the bottom of the group via a high order.
    ctx.addNavItem({
      label: "Documentation",
      href: "/dashboard/admin/docs",
      icon: "book-open",
      section: "admin",
      order: 100,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addPage({
      path: "/dashboard/admin/billing",
      title: "Metered Resources — Admin",
      layout: "dashboard",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/admin",
      title: "Site Administration",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/tenants",
      title: "All Tenants",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/jobs",
      title: "All Jobs",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/audit",
      title: "Preflight Audit",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/health",
      title: "System Health",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/warming",
      title: "Tile Warming",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/appearance",
      title: "Appearance",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/branding",
      title: "Branding",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/api-keys",
      title: "API Keys (All Tenants)",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/webhook-endpoints",
      title: "Webhooks (All Tenants)",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/reports",
      title: "Reports (All Tenants)",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/admin/docs",
      title: "Admin Documentation",
      layout: "dashboard",
    });

    // Routes
    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/tenants",
        auth: true,
        permission: "site-admin:access",
        description: "List all tenants (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const page = Number(req.query.page ?? 1);
          const pageSize = Number(req.query.page_size ?? 50);
          const resp = await adminFetch(
            `/api/v1/admin/tenants?page=${page}&page_size=${pageSize}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/tenants/:tenantId",
        auth: true,
        permission: "site-admin:access",
        description: "Get a specific tenant (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/tenants/:tenantId/plan",
        auth: true,
        permission: "site-admin:access",
        description: "Update a tenant's plan (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/plan`,
            { method: "PATCH", body: JSON.stringify(req.body) },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/tenants/:tenantId/status",
        auth: true,
        permission: "site-admin:access",
        description: "Update a tenant's status (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/status`,
            { method: "PATCH", body: JSON.stringify(req.body) },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/jobs",
        auth: true,
        permission: "site-admin:access",
        description: "List all jobs across tenants (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const page = Number(req.query.page ?? 1);
          const pageSize = Number(req.query.page_size ?? 50);
          const resp = await adminFetch(
            `/api/v1/admin/jobs?page=${page}&page_size=${pageSize}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            console.error(
              `[lintpdf] GET /admin/jobs engine error ${resp.status}: ${detail}`,
            );
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/jobs/:jobId",
        auth: true,
        permission: "site-admin:access",
        description: "Get full job detail (super admin, cross-tenant)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/jobs/${req.params.jobId}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            console.error(
              `[lintpdf] GET /admin/jobs/${req.params.jobId} engine error ${resp.status}: ${detail}`,
            );
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      // ── Preflight Audit (full end-to-end visibility) ─────────
      {
        method: "GET" as HttpMethod,
        path: "/audit",
        auth: true,
        permission: "site-admin:access",
        description:
          "Cross-tenant preflight audit list with grouping + filters (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams();
          for (const [k, v] of Object.entries(req.query ?? {})) {
            if (v !== undefined && v !== null && v !== "") {
              qs.set(k, String(v));
            }
          }
          const suffix = qs.toString() ? `?${qs.toString()}` : "";
          const resp = await adminFetch(`/api/v1/admin/audit/jobs${suffix}`);
          if (!resp.ok) {
            const detail = await resp.text();
            console.error(
              `[lintpdf] GET /admin/audit engine error ${resp.status}: ${detail}`,
            );
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/audit/:jobId",
        auth: true,
        permission: "site-admin:access",
        description: "Full audit detail for one job (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/audit/jobs/${req.params.jobId}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            console.error(
              `[lintpdf] GET /admin/audit/${req.params.jobId} engine error ${resp.status}: ${detail}`,
            );
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/audit/:jobId/findings",
        auth: true,
        permission: "site-admin:access",
        description: "Paginated findings for one job (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const page = Number(req.query.page ?? 1);
          const pageSize = Number(req.query.page_size ?? 200);
          const resp = await adminFetch(
            `/api/v1/admin/audit/jobs/${req.params.jobId}/findings?page=${page}&page_size=${pageSize}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/audit/imported-reports/:id",
        auth: true,
        permission: "site-admin:access",
        description:
          "Fresh presigned URL for an imported-report raw blob (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/audit/imported-reports/${req.params.id}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      // ── Cross-tenant profile (ruleset) management ────────────
      {
        method: "GET" as HttpMethod,
        path: "/profiles",
        auth: true,
        permission: "site-admin:access",
        description: "List all profiles grouped by system + tenant (super admin)",
        handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(`/api/v1/admin/profiles`);
          if (!resp.ok) {
            const detail = await resp.text();
            console.error(
              `[lintpdf] GET /admin/profiles engine error ${resp.status}: ${detail}`,
            );
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/tenants/:tenantId/profiles/:profileId",
        auth: true,
        permission: "site-admin:access",
        description: "Get profile detail for any tenant (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/profiles/${req.params.profileId}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "PUT" as HttpMethod,
        path: "/tenants/:tenantId/profiles/:profileId",
        auth: true,
        permission: "site-admin:access",
        description: "Create or update a tenant's custom profile (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/profiles/${req.params.profileId}`,
            { method: "PUT", body: JSON.stringify(req.body) },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "DELETE" as HttpMethod,
        path: "/tenants/:tenantId/profiles/:profileId",
        auth: true,
        permission: "site-admin:access",
        description: "Delete a tenant's custom profile (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/profiles/${req.params.profileId}`,
            { method: "DELETE" },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 204 };
        }) as RouteHandler,
      },
      // ── Metered resource overrides + direct grants ──
      {
        method: "PUT" as HttpMethod,
        path: "/tenants/:tenantId/credits/monthly-override",
        auth: true,
        permission: "site-admin:access",
        description: "Override a tenant's monthly AI-credit allotment",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/credits/monthly-override`,
            { method: "PUT", body: JSON.stringify(req.body) },
          );
          const text = await resp.text();
          const body = (() => {
            try {
              return JSON.parse(text);
            } catch {
              return text;
            }
          })();
          return { status: resp.status, body };
        }) as RouteHandler,
      },
      {
        method: "PUT" as HttpMethod,
        path: "/tenants/:tenantId/files/monthly-override",
        auth: true,
        permission: "site-admin:access",
        description: "Override a tenant's monthly file allotment",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/files/monthly-override`,
            { method: "PUT", body: JSON.stringify(req.body) },
          );
          const text = await resp.text();
          const body = (() => {
            try {
              return JSON.parse(text);
            } catch {
              return text;
            }
          })();
          return { status: resp.status, body };
        }) as RouteHandler,
      },
      {
        method: "POST" as HttpMethod,
        path: "/tenants/:tenantId/credits/grant",
        auth: true,
        permission: "site-admin:access",
        description: "Grant AI credits directly (admin bypass — no Stripe)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams();
          const body = (req.body as Record<string, unknown>) ?? {};
          if (typeof body.credit_amount === "number") {
            qs.set("credit_amount", String(body.credit_amount));
          }
          if (typeof body.price_paid === "number") {
            qs.set("price_paid", String(body.price_paid));
          }
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/ai/credits?${qs.toString()}`,
            { method: "POST" },
          );
          const text = await resp.text();
          const parsed = (() => {
            try {
              return JSON.parse(text);
            } catch {
              return text;
            }
          })();
          return { status: resp.status, body: parsed };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/tenants/:tenantId/metered-packages",
        auth: true,
        permission: "site-admin:access",
        description: "List every metered-resource package for a tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/metered-packages`,
          );
          const text = await resp.text();
          const body = (() => {
            try {
              return JSON.parse(text);
            } catch {
              return text;
            }
          })();
          return { status: resp.status, body };
        }) as RouteHandler,
      },
      {
        method: "DELETE" as HttpMethod,
        path: "/tenants/:tenantId/metered-packages/:packageId",
        auth: true,
        permission: "site-admin:access",
        description: "Revoke a metered-resource package (credits or files)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/metered-packages/${req.params.packageId}`,
            { method: "DELETE" },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 204 };
        }) as RouteHandler,
      },
      {
        method: "POST" as HttpMethod,
        path: "/tenants/:tenantId/files/grant",
        auth: true,
        permission: "site-admin:access",
        description: "Grant a file pack directly (admin bypass — no Stripe)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams();
          const body = (req.body as Record<string, unknown>) ?? {};
          if (typeof body.files_granted === "number") {
            qs.set("files_granted", String(body.files_granted));
          }
          if (typeof body.price_paid === "number") {
            qs.set("price_paid", String(body.price_paid));
          }
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/files/packages?${qs.toString()}`,
            { method: "POST" },
          );
          const text = await resp.text();
          const parsed = (() => {
            try {
              return JSON.parse(text);
            } catch {
              return text;
            }
          })();
          return { status: resp.status, body: parsed };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/health",
        auth: true,
        permission: "site-admin:access",
        description: "Check engine health (super admin)",
        handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch("/health");
          if (!resp.ok) {
            return {
              status: resp.status,
              body: { status: "unhealthy", error: resp.statusText },
            };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/tile-warming/events",
        auth: true,
        permission: "site-admin:access",
        description: "Recent tile-warming events (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams();
          if (req.query.tenant_id)
            qs.set("tenant_id", String(req.query.tenant_id));
          if (req.query.limit) qs.set("limit", String(req.query.limit));
          const suffix = qs.toString() ? `?${qs.toString()}` : "";
          const resp = await adminFetch(
            `/api/v1/admin/tile-warming/events${suffix}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/tile-warming/summary",
        auth: true,
        permission: "site-admin:access",
        description: "Tile-warming aggregates (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams();
          if (req.query.since_hours)
            qs.set("since_hours", String(req.query.since_hours));
          const suffix = qs.toString() ? `?${qs.toString()}` : "";
          const resp = await adminFetch(
            `/api/v1/admin/tile-warming/summary${suffix}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/tile-warming/jobs/:jobId",
        auth: true,
        permission: "site-admin:access",
        description: "Tile-warming status for a single job (super admin)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tile-warming/jobs/${req.params.jobId}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      // ── Cross-tenant admin lists (grouped by tenant) ─────────
      {
        method: "GET" as HttpMethod,
        path: "/api-keys",
        auth: true,
        permission: "site-admin:access",
        description: "List API keys across all tenants, grouped by tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams(
            Object.entries(req.query).reduce<Record<string, string>>(
              (acc, [k, v]) => {
                if (v !== undefined && v !== null) acc[k] = String(v);
                return acc;
              },
              {},
            ),
          );
          const resp = await adminFetch(`/api/v1/admin/api-keys?${qs}`);
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 200, body: await resp.json() };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/webhook-endpoints",
        auth: true,
        permission: "site-admin:access",
        description:
          "List webhook endpoints across all tenants, grouped by tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams(
            Object.entries(req.query).reduce<Record<string, string>>(
              (acc, [k, v]) => {
                if (v !== undefined && v !== null) acc[k] = String(v);
                return acc;
              },
              {},
            ),
          );
          const resp = await adminFetch(
            `/api/v1/admin/webhook-endpoints?${qs}`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 200, body: await resp.json() };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/report-tokens",
        auth: true,
        permission: "site-admin:access",
        description: "List report tokens across all tenants, grouped by tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const qs = new URLSearchParams(
            Object.entries(req.query).reduce<Record<string, string>>(
              (acc, [k, v]) => {
                if (v !== undefined && v !== null) acc[k] = String(v);
                return acc;
              },
              {},
            ),
          );
          const resp = await adminFetch(`/api/v1/admin/report-tokens?${qs}`);
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 200, body: await resp.json() };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/lintpdf/admin", routes);
  },
};
