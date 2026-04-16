/**
 * Account self-service plugin — tenant settings, branding, and configuration.
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

import { resolveEngineTenantId } from "../../index";

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

export const lintpdfAccountPlugin: PixieDustPlugin = {
  name: "lintpdf-account",
  version: "0.1.0",
  description: "Tenant account settings, branding, and self-service management",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("account:manage", ["ADMIN", "OWNER"]);

    // Navigation
    ctx.addNavItem({
      label: "Account",
      href: "/dashboard/account",
      icon: "settings",
      section: "tenant",
      order: 10,
      requiredPermission: "account:manage",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/account",
      title: "Account",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/account/settings",
      title: "Settings",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/account/branding",
      title: "Branding",
      layout: "dashboard",
    });

    // Routes
    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/",
        auth: true,
        permission: "account:manage",
        description: "Get tenant account information",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const engineId = await resolveEngineTenantId(tenantId);
          const resp = await adminFetch(`/api/v1/admin/tenants/${engineId}`);
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
        path: "/",
        auth: true,
        permission: "account:manage",
        description: "Update tenant account settings",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const engineId = await resolveEngineTenantId(tenantId);
          const resp = await adminFetch(`/api/v1/admin/tenants/${engineId}`, {
            method: "PATCH",
            body: JSON.stringify(req.body),
          });
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
        path: "/branding",
        auth: true,
        permission: "account:manage",
        description: "Update tenant branding settings",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }

          const engineId = await resolveEngineTenantId(tenantId);
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${engineId}/branding`,
            {
              method: "PATCH",
              body: JSON.stringify(req.body),
            },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const engineData = await resp.json();
          return { status: 200, body: engineData };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/lintpdf/account", routes);
  },
};
