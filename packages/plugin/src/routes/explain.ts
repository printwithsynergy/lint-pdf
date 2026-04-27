/**
 * AI-Explain route — Q-C4/C5 surface.
 *
 * Forwards to the engine's
 * ``POST /api/v1/jobs/{job_id}/findings/{finding_id}/explain`` endpoint.
 * The engine handles cost-cap gating (HTTP 402) and Claude Haiku 4.5
 * caching; this proxy passes the response through verbatim so dashboard
 * + plugin consumers see the same body shape the SDK does.
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

export function explainRoutes(): RouteDefinition[] {
  return [
    {
      method: "POST",
      path: "/jobs/:jobId/findings/:findingId/explain",
      auth: true,
      permission: "preflight:view",
      description:
        "Generate (or fetch cached) AI explanation for a finding via Claude Haiku 4.5",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const apiPath = `/api/v1/jobs/${req.params.jobId}/findings/${req.params.findingId}/explain`;
        const resp = await tenantFetch(apiPath, { method: "POST", body: "{}" });
        // Pass HTTP 402 (cost cap exceeded) through unchanged so the
        // dashboard can show the upgrade-cap CTA.
        if (!resp.ok) {
          const detail = await resp.text();
          return { status: resp.status, body: { error: detail } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
  ];
}
