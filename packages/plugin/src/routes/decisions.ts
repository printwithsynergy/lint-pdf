/**
 * Decisions audit routes (Wave V V-05).
 *
 * Mirrors the engine's tenant-scoped decisions surface 1:1 — list,
 * record (job-level + finding-level), revoke. Decisions are
 * append-only; the revoke endpoint stamps revoked_at without deleting
 * the row, preserving the audit trail.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

function baseUrl(): string {
  return (process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com").replace(
    /\/$/,
    "",
  );
}

function tenantFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl()}${path}`, { ...init, headers });
}

export function decisionRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET",
      path: "/jobs/:jobId/decisions",
      auth: true,
      permission: "preflight:view",
      description: "List decisions on a job (active by default)",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const includeRevoked = req.query.include_revoked === "true";
        const limit = Number(req.query.limit ?? "200");
        const apiPath =
          `/api/v1/jobs/${req.params.jobId}/decisions` +
          `?include_revoked=${includeRevoked}&limit=${limit}`;
        const resp = await tenantFetch(apiPath);
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
    {
      method: "POST",
      path: "/jobs/:jobId/decisions",
      auth: true,
      permission: "preflight:submit",
      description: "Record a job-level decision",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/jobs/${req.params.jobId}/decisions`,
          {
            method: "POST",
            body: JSON.stringify(req.body ?? {}),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: resp.status, body: await resp.json() };
      },
    },
    {
      method: "POST",
      path: "/jobs/:jobId/findings/:findingId/decisions",
      auth: true,
      permission: "preflight:submit",
      description: "Record a finding-level decision",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/jobs/${req.params.jobId}/findings/${req.params.findingId}/decisions`,
          {
            method: "POST",
            body: JSON.stringify(req.body ?? {}),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: resp.status, body: await resp.json() };
      },
    },
    {
      method: "POST",
      path: "/jobs/:jobId/decisions/:decisionId/revoke",
      auth: true,
      permission: "preflight:submit",
      description: "Soft-revoke a decision (idempotent)",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/jobs/${req.params.jobId}/decisions/${req.params.decisionId}/revoke`,
          {
            method: "POST",
            body: JSON.stringify(req.body ?? {}),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
  ];
}
