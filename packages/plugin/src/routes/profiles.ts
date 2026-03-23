/**
 * Profile proxy routes — forward requests to the LintPDF API.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { getClient } from "../index";

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

export function profileRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/profiles",
      auth: true,
      permission: "preflight:view",
      description: "List available preflight profiles (flight plans)",
      handler: (async (): Promise<RouteResponse> => {
        const client = getClient();
        if (!client) {
          return { status: 503, body: { error: "LintPDF API not configured" } };
        }
        const profiles = await client.listProfiles();
        return { status: 200, body: profiles };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/profiles/:profileId",
      auth: true,
      permission: "preflight:view",
      description: "Get profile details",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          `/api/v1/profiles/${req.params.profileId}`,
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
      method: "POST" as HttpMethod,
      path: "/profiles",
      auth: true,
      permission: "flight-plan:manage",
      description: "Create a custom preflight profile",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch("/api/v1/profiles", {
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
      method: "DELETE" as HttpMethod,
      path: "/profiles/:profileId",
      auth: true,
      permission: "flight-plan:manage",
      description: "Delete a custom preflight profile",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(
          `/api/v1/profiles/${req.params.profileId}`,
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
}
