/**
 * API key management plugin — manage tenant API keys via the LintPDF engine.
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
// getClient not needed — this plugin proxies directly to the engine admin API

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

export const groundedApiKeysPlugin: PixieDustPlugin = {
  name: "grounded-api-keys",
  version: "0.1.0",
  description: "Manage per-tenant API keys for the LintPDF engine",
  dependencies: ["grounded"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("api-keys:manage", ["ADMIN", "OWNER"]);

    // Navigation
    ctx.addNavItem({
      label: "API Keys",
      href: "/dashboard/api-keys",
      icon: "key",
      section: "admin",
      order: 60,
      requiredPermission: "api-keys:manage",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/api-keys",
      title: "API Keys",
      layout: "dashboard",
    });

    // Routes
    const routes: RouteDefinition[] = [
      {
        method: "POST" as HttpMethod,
        path: "/",
        auth: true,
        permission: "api-keys:manage",
        description: "Create a new API key for the current tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${tenantId}/keys`,
            { method: "POST", body: JSON.stringify(req.body) },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 201, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/",
        auth: true,
        permission: "api-keys:manage",
        description: "List API keys for the current tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${tenantId}/keys`,
            { method: "GET" },
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
        path: "/:keyId",
        auth: true,
        permission: "api-keys:manage",
        description: "Revoke an API key",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${tenantId}/keys/${req.params.keyId}`,
            { method: "DELETE" },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 204 };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/grounded/keys", routes);
  },
};
