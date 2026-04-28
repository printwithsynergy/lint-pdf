/**
 * Report viewing plugin — view and download preflight reports.
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { getClient } from "../../index";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

// ---------------------------------------------------------------------------
// Helper: proxy fetch to the LintPDF engine API
// ---------------------------------------------------------------------------

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

export const lintpdfReportsPlugin: PixieDustPlugin = {
  name: "lintpdf-reports",
  version: "0.1.0",
  description: "View and download preflight reports",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("reports:view", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
      "VIEWER",
    ]);
    ctx.addPermission("reports:download", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
    ]);

    // Pages
    ctx.addPage({
      path: "/dashboard/preflight/[jobId]/report",
      title: "Preflight Report",
      layout: "dashboard",
    });

    // Routes
    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/:jobId",
        auth: true,
        permission: "reports:view",
        description: "Get report findings for a job",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const client = getClient();
          if (!client) {
            return {
              status: 503,
              body: { error: "LintPDF API not configured" },
            };
          }
          try {
            const job = await client.getJob(req.params.jobId);
            return { status: 200, body: job };
          } catch (err) {
            // The SDK throws on any non-2xx engine response (e.g.
            // "LintPDF API: 404"). Pass the status through to the
            // dashboard so the report page renders an empty / not-
            // found state instead of a 500.
            const message = err instanceof Error ? err.message : String(err);
            const match = /LintPDF API:\s*(\d{3})/.exec(message);
            if (match) {
              const status = Number(match[1]);
              if (status === 404) {
                return { status: 404, body: { error: "Job not found" } };
              }
              return { status, body: { error: message } };
            }
            console.warn("[reports] getJob failed:", message);
            return {
              status: 502,
              body: { error: "Engine unreachable", detail: message },
            };
          }
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/:jobId/html",
        auth: true,
        permission: "reports:view",
        description: "Get or redirect to the HTML report for a job",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await engineFetch(
            `/api/v1/jobs/${req.params.jobId}/report/html`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          // If the engine returns a redirect URL, pass it through
          const data = (await resp.json()) as Record<string, unknown>;
          if (data.url) {
            return {
              status: 302,
              body: { url: data.url },
            };
          }
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/:jobId/download",
        auth: true,
        permission: "reports:download",
        description: "Download the PDF report for a job",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await engineFetch(
            `/api/v1/jobs/${req.params.jobId}/report/pdf`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = (await resp.json()) as Record<string, unknown>;
          if (data.url) {
            return {
              status: 302,
              body: { url: data.url },
            };
          }
          return { status: 200, body: data };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/lintpdf/reports", routes);
  },
};
