/**
 * Color configuration proxy routes — forward to the LintPDF engine.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

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
  const apiKey = process.env.GROUNDED_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export function colorConfigRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/color-config",
      auth: true,
      permission: "account:manage",
      description: "Get tenant color management configuration",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch("/api/v1/color-config");
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
        const resp = await engineFetch("/api/v1/color-config", {
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
        const resp = await engineFetch("/api/v1/color-config/palette", {
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
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          "/api/v1/color-config/gamut-conditions",
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
}
