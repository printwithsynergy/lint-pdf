/**
 * EPM candidacy verdict route.
 *
 * Forwards to ``GET /api/v1/jobs/{job_id}/epm`` so dashboard + plugin
 * consumers see the same EPM tier / drivers / advisories shape that
 * the SDK and inline ``JobResponse.epm_verdict`` carry.
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

export function epmRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET",
      path: "/jobs/:jobId/epm",
      auth: true,
      permission: "preflight:view",
      description:
        "EPM candidacy verdict (tier, rejection drivers, advisories, IndiChrome hint)",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(`/api/v1/jobs/${req.params.jobId}/epm`);
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
  ];
}
