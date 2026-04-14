/**
 * Custom API endpoints plugin — manage vanity URL slugs bound to profiles.
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

function engineFetch(path: string, init?: RequestInit): Promise<Response> {
  const baseUrl = (
    process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com"
  ).replace(/\/$/, "");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export const lintpdfEndpointsPlugin: PixieDustPlugin = {
  name: "lintpdf-endpoints",
  version: "0.1.0",
  description: "Custom API endpoint management for LintPDF",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("endpoints:manage", ["ADMIN", "OWNER"]);

    // Navigation
    ctx.addNavItem({
      label: "API Endpoints",
      href: "/dashboard/endpoints",
      icon: "globe",
      section: "admin",
      order: 62,
      requiredPermission: "endpoints:manage",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/endpoints",
      title: "Custom API Endpoints",
      layout: "dashboard",
    });

    // Routes
    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/endpoints",
        auth: true,
        permission: "endpoints:manage",
        description: "List custom API endpoints",
        handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
          const resp = await engineFetch("/api/v1/endpoints");
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 200, body: await resp.json() };
        }) as RouteHandler,
      },
      {
        method: "POST" as HttpMethod,
        path: "/endpoints",
        auth: true,
        permission: "endpoints:manage",
        description: "Create a custom API endpoint",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await engineFetch("/api/v1/endpoints", {
            method: "POST",
            body: JSON.stringify(req.body),
          });
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 201, body: await resp.json() };
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/endpoints/:endpointId",
        auth: true,
        permission: "endpoints:manage",
        description: "Update a custom API endpoint",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await engineFetch(
            `/api/v1/endpoints/${req.params.endpointId}`,
            { method: "PATCH", body: JSON.stringify(req.body) },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 200, body: await resp.json() };
        }) as RouteHandler,
      },
      {
        method: "DELETE" as HttpMethod,
        path: "/endpoints/:endpointId",
        auth: true,
        permission: "endpoints:manage",
        description: "Delete a custom API endpoint",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await engineFetch(
            `/api/v1/endpoints/${req.params.endpointId}`,
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

    ctx.addRoutes("/api/lintpdf", routes);
  },
};
