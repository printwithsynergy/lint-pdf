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
  version: "0.1.0",
  description: "Site-wide administration for LintPDF — super admin only",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("site-admin:access", ["SUPER_ADMIN"]);

    // Navigation — admin section (renders under the "Admin" sidebar heading,
    // role-gated to SUPER_ADMIN by Pixie Dust). Previously used section: "global"
    // which the DashboardSidebar filters into the normal "Menu" group, leaking
    // super-admin routes to tenant users.
    ctx.addNavItem({
      label: "All Tenants",
      href: "/dashboard/admin/tenants",
      icon: "building-2",
      section: "admin",
      order: 10,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "All Jobs",
      href: "/dashboard/admin/jobs",
      icon: "inbox",
      section: "admin",
      order: 20,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "System Health",
      href: "/dashboard/admin/health",
      icon: "zap",
      section: "admin",
      order: 30,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Tile Warming",
      href: "/dashboard/admin/warming",
      icon: "map",
      section: "admin",
      order: 35,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Appearance",
      href: "/dashboard/admin/appearance",
      icon: "palette",
      section: "admin",
      order: 40,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "Branding",
      href: "/dashboard/admin/branding",
      icon: "paintbrush",
      section: "admin",
      order: 41,
      requiredRole: "SUPER_ADMIN",
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
    ];

    ctx.addRoutes("/api/lintpdf/admin", routes);
  },
};
