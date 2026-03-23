/**
 * AI configuration proxy routes — forward to the LintPDF engine.
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

export function aiConfigRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/ai-config",
      auth: true,
      permission: "account:manage",
      description: "Get tenant AI configuration",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch("/api/v1/ai/config");
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
      path: "/ai-config",
      auth: true,
      permission: "account:manage",
      description: "Update tenant AI configuration",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch("/api/v1/ai/config", {
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
  ];
}
