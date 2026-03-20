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
// Helper: proxy fetch to the Grounded engine admin API
// ---------------------------------------------------------------------------

function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const baseUrl = (process.env.GROUNDED_API_URL ?? "https://api.grounded.dev").replace(
    /\/$/,
    "",
  );
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const adminKey = process.env.GROUNDED_ADMIN_API_KEY;
  if (adminKey) {
    headers["X-Admin-Key"] = adminKey;
  }
  const apiKey = process.env.GROUNDED_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export const groundedSiteAdminPlugin: PixieDustPlugin = {
  name: "grounded-site-admin",
  version: "0.1.0",
  description: "Site-wide administration for Grounded — super admin only",
  dependencies: ["grounded"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("site-admin:access", ["SUPER_ADMIN"]);

    // Navigation — global section
    ctx.addNavItem({
      label: "All Tenants",
      href: "/dashboard/admin/tenants",
      icon: "building",
      section: "global",
      order: 10,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "All Jobs",
      href: "/dashboard/admin/jobs",
      icon: "folder-search",
      section: "global",
      order: 20,
      requiredRole: "SUPER_ADMIN",
    });
    ctx.addNavItem({
      label: "System Health",
      href: "/dashboard/admin/health",
      icon: "activity",
      section: "global",
      order: 30,
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
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
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
    ];

    ctx.addRoutes("/api/grounded/admin", routes);
  },
};
