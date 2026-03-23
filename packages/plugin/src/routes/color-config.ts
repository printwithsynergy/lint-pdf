/**
 * Color configuration proxy routes — forward to the LintPDF engine.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { resolveEngineTenantId } from "../index";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

function engineFetch(path: string, init?: RequestInit): Promise<Response> {
  const baseUrl = (
    process.env.GROUNDED_API_URL ?? "https://api.lintpdf.com"
  ).replace(/\/$/, "");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const adminKey = process.env.GROUNDED_ADMIN_API_KEY;
  if (adminKey) {
    headers["X-Admin-Key"] = adminKey;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

async function getEnginePath(
  tenantId: string | undefined,
  suffix: string,
): Promise<{ path: string } | { error: RouteResponse }> {
  if (!tenantId) {
    return { error: { status: 400, body: { error: "Missing tenant context" } } };
  }
  const engineId = await resolveEngineTenantId(tenantId);
  return { path: `/api/v1/tenants/${engineId}/color-config${suffix}` };
}

export function colorConfigRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/color-config",
      auth: true,
      permission: "account:manage",
      description: "Get tenant color management configuration",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const result = await getEnginePath(req.auth?.tenantId, "");
        if ("error" in result) return result.error;
        const resp = await engineFetch(result.path);
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
      path: "/color-config",
      auth: true,
      permission: "account:manage",
      description: "Update tenant color management configuration",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const result = await getEnginePath(req.auth?.tenantId, "");
        if ("error" in result) return result.error;
        const resp = await engineFetch(result.path, {
          method: "PUT",
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
      method: "PUT" as HttpMethod,
      path: "/color-config/palette",
      auth: true,
      permission: "account:manage",
      description: "Update brand color palette",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const result = await getEnginePath(req.auth?.tenantId, "/palette");
        if ("error" in result) return result.error;
        const resp = await engineFetch(result.path, {
          method: "PUT",
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
      method: "GET" as HttpMethod,
      path: "/color-config/gamut-conditions",
      auth: true,
      permission: "account:manage",
      description: "List available gamut/output conditions",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const result = await getEnginePath(req.auth?.tenantId, "/gamut-conditions");
        if ("error" in result) return result.error;
        const resp = await engineFetch(result.path);
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
      path: "/color-config/pantone-overrides",
      auth: true,
      permission: "account:manage",
      description: "Get tenant Pantone color overrides",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const result = await getEnginePath(req.auth?.tenantId, "/pantone-overrides");
        if ("error" in result) return result.error;
        const resp = await engineFetch(result.path);
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
      path: "/color-config/pantone-overrides",
      auth: true,
      permission: "account:manage",
      description: "Bulk set/replace Pantone color overrides",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const result = await getEnginePath(req.auth?.tenantId, "/pantone-overrides");
        if ("error" in result) return result.error;
        const resp = await engineFetch(result.path, {
          method: "PUT",
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
      method: "DELETE" as HttpMethod,
      path: "/color-config/pantone-overrides",
      auth: true,
      permission: "account:manage",
      description: "Clear all Pantone color overrides",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const result = await getEnginePath(req.auth?.tenantId, "/pantone-overrides");
        if ("error" in result) return result.error;
        const resp = await engineFetch(result.path, { method: "DELETE" });
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        return { status: 204, body: null };
      }) as RouteHandler,
    },
  ];
}
