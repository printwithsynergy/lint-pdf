/**
 * Branding proxy routes — forward brand profile CRUD to the LintPDF engine.
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

async function getTenantId(req: RouteRequest): Promise<string | null> {
  const id = req.auth?.tenantId;
  if (!id) return null;
  return resolveEngineTenantId(id);
}

export function brandingRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/branding/profiles",
      auth: true,
      permission: "branding:manage",
      description: "List brand profiles for the tenant",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/brand-profiles`,
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/branding/profiles",
      auth: true,
      permission: "branding:manage",
      description: "Create a brand profile",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/brand-profiles`,
          { method: "POST", body: JSON.stringify(req.body) },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 201, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/branding/profiles/:profileId",
      auth: true,
      permission: "branding:manage",
      description: "Get a brand profile",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/brand-profiles/${req.params.profileId}`,
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "PUT" as HttpMethod,
      path: "/branding/profiles/:profileId",
      auth: true,
      permission: "branding:manage",
      description: "Update a brand profile",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/brand-profiles/${req.params.profileId}`,
          { method: "PUT", body: JSON.stringify(req.body) },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "DELETE" as HttpMethod,
      path: "/branding/profiles/:profileId",
      auth: true,
      permission: "branding:manage",
      description: "Delete a brand profile",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/brand-profiles/${req.params.profileId}`,
          { method: "DELETE" },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 204 };
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/branding/default",
      auth: true,
      permission: "branding:manage",
      description: "Set the default brand profile for the tenant",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/default-brand-profile`,
          { method: "PATCH", body: JSON.stringify(req.body) },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    // -- White-label custom report domain (self-service) ------------------
    {
      method: "GET" as HttpMethod,
      path: "/branding/custom-domain",
      auth: true,
      permission: "branding:manage",
      description: "Get the tenant's white-label custom report domain state",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/custom-domain`,
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/branding/custom-domain",
      auth: true,
      permission: "branding:manage",
      description: "Set or clear the tenant's white-label custom report domain",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/custom-domain`,
          { method: "PATCH", body: JSON.stringify(req.body) },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/branding/profiles/:profileId/custom-domain",
      auth: true,
      permission: "branding:manage",
      description: "Set or clear a brand profile's white-label custom report domain",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = await getTenantId(req);
        if (!tenantId) return { status: 400, body: { error: "Missing tenant context" } };
        const resp = await engineFetch(
          `/api/v1/tenants/${tenantId}/brand-profiles/${req.params.profileId}/custom-domain`,
          { method: "PATCH", body: JSON.stringify(req.body) },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },

    // ── Default output branding (anonymous / profile / LintPDF) ──────
    {
      method: "GET" as HttpMethod,
      path: "/branding/defaults",
      auth: true,
      permission: "branding:manage",
      description: "Get the tenant's default output branding mode",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(`/api/v1/tenant/branding-defaults`);
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/branding/defaults",
      auth: true,
      permission: "branding:manage",
      description:
        "Update the tenant's default output branding (anonymous / profile / LintPDF)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(`/api/v1/tenant/branding-defaults`, {
          method: "PATCH",
          body: JSON.stringify(req.body),
        });
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
  ];
}
