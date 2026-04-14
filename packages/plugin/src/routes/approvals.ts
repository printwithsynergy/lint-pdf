/**
 * Approval chain proxy routes — forward to engine's approval API.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

const engineUrl = (path: string): string => {
  const base = process.env.LINTPDF_API_URL || "http://localhost:8000";
  return `${base.replace(/\/$/, "")}${path}`;
};

const authHeaders = (): Record<string, string> => {
  const key = process.env.LINTPDF_API_KEY || "";
  return key ? { Authorization: `Bearer ${key}` } : {};
};

export function approvalRoutes(): RouteDefinition[] {
  return [
    // ── Tenant-authenticated (session required, proxies with API key) ──
    {
      method: "GET" as HttpMethod,
      path: "/approval-templates",
      auth: true,
      permission: "preflight:view",
      description: "List approval chain templates for the tenant",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl("/api/v1/approval-templates"), {
          headers: authHeaders(),
        });
        const data = await resp.json().catch(() => []);
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/approval-templates",
      auth: true,
      permission: "preflight:manage",
      description: "Create an approval chain template",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl("/api/v1/approval-templates"), {
          method: "POST",
          headers: { ...authHeaders(), "Content-Type": "application/json" },
          body: JSON.stringify(req.body ?? {}),
        });
        const data = await resp.json().catch(() => ({}));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
    {
      method: "PATCH" as HttpMethod,
      path: "/approval-templates/:id",
      auth: true,
      permission: "preflight:manage",
      description: "Update an approval chain template",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl(`/api/v1/approval-templates/${req.params.id}`), {
          method: "PATCH",
          headers: { ...authHeaders(), "Content-Type": "application/json" },
          body: JSON.stringify(req.body ?? {}),
        });
        const data = await resp.json().catch(() => ({}));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
    {
      method: "DELETE" as HttpMethod,
      path: "/approval-templates/:id",
      auth: true,
      permission: "preflight:manage",
      description: "Delete an approval chain template",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl(`/api/v1/approval-templates/${req.params.id}`), {
          method: "DELETE",
          headers: authHeaders(),
        });
        return { status: resp.status, body: {} };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/jobs/:jobId/approval-chain",
      auth: true,
      permission: "preflight:manage",
      description: "Attach an approval chain to a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/jobs/${req.params.jobId}/approval-chain`),
          {
            method: "POST",
            headers: { ...authHeaders(), "Content-Type": "application/json" },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        const data = await resp.json().catch(() => ({}));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/jobs/:jobId/approval-chain",
      auth: true,
      permission: "preflight:view",
      description: "Get the approval chain for a job (tenant view)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/jobs/${req.params.jobId}/approval-chain`),
          { headers: authHeaders() },
        );
        const data = await resp.json().catch(() => ({}));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/jobs/:jobId/approval-chain/cancel",
      auth: true,
      permission: "preflight:manage",
      description: "Cancel an active approval chain",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/jobs/${req.params.jobId}/approval-chain/cancel`),
          { method: "POST", headers: authHeaders() },
        );
        const data = await resp.json().catch(() => ({}));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },

    // ── Public approver endpoints (token-gated, no auth) ──
    {
      method: "GET" as HttpMethod,
      path: "/approvals/info/:accessToken",
      auth: false,
      description: "Get chain info for an approver landing page",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(engineUrl(`/api/v1/approvals/info/${req.params.accessToken}`));
        const data = await resp.json().catch(() => ({}));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/approvals/decide/:accessToken",
      auth: false,
      description: "Submit approver decision",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/approvals/decide/${req.params.accessToken}`),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req.body ?? {}),
          },
        );
        const data = await resp.json().catch(() => ({}));
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/approval-chain",
      auth: false,
      description: "Get chain status for the public viewer",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/public/${req.params.token}/approval-chain`),
        );
        const data = await resp.json().catch(() => null);
        return { status: resp.status, body: data };
      }) as RouteHandler,
    },
  ];
}
