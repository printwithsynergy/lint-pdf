/**
 * Job proxy routes — forward requests to the LintPDF API.
 *
 * Uses ``engineFetch`` directly (rather than ``LintPDFClient``) so that
 * non-2xx engine responses propagate their status code instead of being
 * wrapped in a generic Error and surfaced as a 500 by the catch-all handler.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

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

export function jobRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET",
      path: "/jobs",
      auth: true,
      permission: "preflight:view",
      description: "List preflight jobs for the current tenant",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const page = Number(req.query.page ?? "1");
        const pageSize = Number(req.query.page_size ?? "20");
        const resp = await engineFetch(
          `/api/v1/jobs?page=${page}&page_size=${pageSize}`,
        );
        if (!resp.ok) {
          const detail = await resp.text();
          console.error(
            `[lintpdf] GET /jobs engine error ${resp.status}: ${detail}`,
          );
          return { status: resp.status, body: { error: detail } };
        }
        const data = await resp.json();
        return { status: 200, body: data };
      },
    },
    {
      method: "GET",
      path: "/jobs/:jobId",
      auth: true,
      permission: "preflight:view",
      description: "Get a specific preflight job by ID",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(`/api/v1/jobs/${req.params.jobId}`);
        if (!resp.ok) {
          const detail = await resp.text();
          console.error(
            `[lintpdf] GET /jobs/${req.params.jobId} engine error ${resp.status}: ${detail}`,
          );
          return { status: resp.status, body: { error: detail } };
        }
        const data = await resp.json();
        return { status: 200, body: data };
      },
    },
    {
      method: "DELETE",
      path: "/jobs/:jobId",
      auth: true,
      permission: "preflight:submit",
      description: "Delete a preflight job",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await engineFetch(`/api/v1/jobs/${req.params.jobId}`, {
          method: "DELETE",
        });
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        return { status: 204 };
      },
    },
  ];
}
