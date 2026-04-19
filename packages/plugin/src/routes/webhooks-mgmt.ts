/**
 * Webhook management proxy routes — CRUD for customer webhook endpoints.
 *
 * Distinct from routes/index.ts which handles *incoming* webhook events.
 * These routes let customers manage their outbound webhook registrations.
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
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export function webhookMgmtRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/webhook-endpoints",
      auth: true,
      permission: "webhooks:manage",
      description: "List webhook endpoints for the current tenant",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch("/api/v1/webhooks");
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        const data = await resp.json();
        return { status: 200, body: data };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/webhook-endpoints",
      auth: true,
      permission: "webhooks:manage",
      description: "Create a new webhook endpoint",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch("/api/v1/webhooks", {
          method: "POST",
          body: JSON.stringify(req.body),
        });
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        const data = await resp.json();
        return { status: 201, body: data };
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/webhook-endpoints/:webhookId",
      auth: true,
      permission: "webhooks:manage",
      description: "Update a webhook endpoint",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          `/api/v1/webhooks/${req.params.webhookId}`,
          {
            method: "PATCH",
            body: JSON.stringify(req.body),
          },
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
      path: "/webhook-endpoints/:webhookId",
      auth: true,
      permission: "webhooks:manage",
      description: "Delete a webhook endpoint",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          `/api/v1/webhooks/${req.params.webhookId}`,
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
      path: "/webhook-endpoints/:webhookId/test",
      auth: true,
      permission: "webhooks:manage",
      description: "Send a test payload to a webhook endpoint",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          `/api/v1/webhooks/${req.params.webhookId}/test`,
          { method: "POST" },
        );
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        const data = await resp.json();
        return { status: 200, body: data };
      }) as RouteHandler,
    },
    // --- Delivery audit + replay ----------------------------------
    {
      method: "GET" as HttpMethod,
      path: "/webhook-endpoints/:webhookId/deliveries",
      auth: true,
      permission: "webhooks:manage",
      description: "List recent delivery attempts for one webhook endpoint",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        // Plugin RouteRequest types ``query`` values as
        // ``string | string[] | undefined`` so a repeated key (?event=a&event=b)
        // still parses. Coerce to a single string before encoding -- arrays
        // can't be encodeURIComponent'd directly.
        const firstValue = (
          v: string | string[] | undefined,
        ): string => (Array.isArray(v) ? (v[0] ?? "") : v ?? "");
        const page = firstValue(req.query?.page) || "1";
        const pageSize = firstValue(req.query?.page_size) || "50";
        const successRaw = firstValue(req.query?.success);
        const eventRaw = firstValue(req.query?.event);
        const successFilter = successRaw
          ? `&success=${encodeURIComponent(successRaw)}`
          : "";
        const eventFilter = eventRaw
          ? `&event=${encodeURIComponent(eventRaw)}`
          : "";
        const resp = await engineFetch(
          `/api/v1/webhooks/deliveries?webhook_id=${req.params.webhookId}` +
            `&page=${encodeURIComponent(page)}&page_size=${encodeURIComponent(pageSize)}${successFilter}${eventFilter}`,
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
      path: "/webhook-endpoints/deliveries/:deliveryId",
      auth: true,
      permission: "webhooks:manage",
      description: "Fetch the signed payload of one past delivery",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          `/api/v1/webhooks/deliveries/${req.params.deliveryId}`,
        );
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/webhook-endpoints/deliveries/:deliveryId/replay",
      auth: true,
      permission: "webhooks:manage",
      description: "Re-fire a past delivery against its original endpoint",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          `/api/v1/webhooks/deliveries/${req.params.deliveryId}/replay`,
          { method: "POST" },
        );
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        return { status: 201, body: await resp.json() };
      }) as RouteHandler,
    },
  ];
}
