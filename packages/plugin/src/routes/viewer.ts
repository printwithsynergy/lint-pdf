/**
 * Viewer proxy routes — forward page tile and info requests to the LintPDF engine.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { resolveEngineTenantId } from "../index";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

function engineUrl(path: string): string {
  const baseUrl = (
    process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com"
  ).replace(/\/$/, "");
  return `${baseUrl}${path}`;
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return headers;
}

export function viewerRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages",
      auth: true,
      permission: "preflight:view",
      description: "List all pages with dimensions for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/pages`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/tile",
      auth: true,
      permission: "preflight:view",
      description: "Get rendered page tile as PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/tile?dpi=${dpi}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: "Failed to render tile" } };
        }
        // Return raw image bytes
        const buffer = await resp.arrayBuffer();
        return {
          status: 200,
          body: Buffer.from(buffer),
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/info",
      auth: true,
      permission: "preflight:view",
      description: "Get page dimensions and box info",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/info`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    // --- Separation endpoints ---
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/separations",
      auth: true,
      permission: "preflight:view",
      description: "List ink channels (CMYK + spot colors)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/viewer/jobs/${req.params.jobId}/separations`),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/channel/:channelName",
      auth: true,
      permission: "preflight:view",
      description: "Get a single separation channel as grayscale PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/channel/${encodeURIComponent(req.params.channelName)}?dpi=${dpi}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: "Failed to render channel" } };
        }
        const buffer = await resp.arrayBuffer();
        return {
          status: 200,
          body: Buffer.from(buffer),
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        } as RouteResponse;
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/pages/:pageNum/tac-heatmap",
      auth: true,
      permission: "preflight:view",
      description: "Get TAC heatmap overlay as RGBA PNG",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const dpi = req.query.dpi ?? "150";
        const tacLimit = req.query.tac_limit ?? "300";
        const resp = await fetch(
          engineUrl(
            `/api/v1/viewer/jobs/${req.params.jobId}/pages/${req.params.pageNum}/tac-heatmap?dpi=${dpi}&tac_limit=${tacLimit}`,
          ),
          { headers: authHeaders() },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: "Failed to render heatmap" } };
        }
        const buffer = await resp.arrayBuffer();
        return {
          status: 200,
          body: Buffer.from(buffer),
          headers: {
            "Content-Type": "image/png",
            "Cache-Control": "public, max-age=86400",
          },
        } as RouteResponse;
      }) as RouteHandler,
    },
  ];
}
