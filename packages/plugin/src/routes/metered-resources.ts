/**
 * Metered-resource proxy routes — credits + file packs balance/topup.
 *
 * Mirrors the layout of ``ai-config.ts`` so the dashboard can call
 * ``/api/lintpdf/credits`` and ``/api/lintpdf/files/quota`` without
 * knowing that they dispatch to the engine.
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
    process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com"
  ).replace(/\/$/, "");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

async function passthrough(path: string, init?: RequestInit): Promise<RouteResponse> {
  const resp = await engineFetch(path, init);
  const text = await resp.text();
  const body = (() => {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  })();
  return { status: resp.status, body };
}

export function meteredResourceRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/credits",
      auth: true,
      permission: "account:manage",
      description: "Current AI credit balance + monthly allotment.",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> =>
        passthrough("/api/v1/ai/credits")) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/credits/topup",
      auth: true,
      permission: "account:manage",
      description: "Create a Stripe Checkout session for a credit pack.",
      handler: (async (req: RouteRequest): Promise<RouteResponse> =>
        passthrough("/api/v1/ai/credits/topup", {
          method: "POST",
          body: JSON.stringify(req.body),
        })) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/credits/usage",
      auth: true,
      permission: "account:manage",
      description: "Daily AI credit consumption trend for the dashboard chart.",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const days = req.query?.days ?? "30";
        return passthrough(
          `/api/v1/ai/usage/trends?days=${encodeURIComponent(String(days))}`,
        );
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/credits/packages",
      auth: true,
      permission: "account:manage",
      description: "List every AI-credit package for the authenticated tenant.",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> =>
        passthrough("/api/v1/ai/credits/packages")) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/files/quota",
      auth: true,
      permission: "account:manage",
      description: "Current file-pack balance + monthly allotment.",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> =>
        passthrough("/api/v1/files/quota")) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/files/packages",
      auth: true,
      permission: "account:manage",
      description: "List every file pack for the authenticated tenant.",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> =>
        passthrough("/api/v1/files/packages")) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/files/topup",
      auth: true,
      permission: "account:manage",
      description: "Create a Stripe Checkout session for a file pack.",
      handler: (async (req: RouteRequest): Promise<RouteResponse> =>
        passthrough("/api/v1/files/topup", {
          method: "POST",
          body: JSON.stringify(req.body),
        })) as RouteHandler,
    },
  ];
}
