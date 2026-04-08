/**
 * Viewer proxy routes — forward page tile and info requests to the LintPDF engine.
 * Also includes public viewer routes (no auth) and view tracking.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { resolveEngineTenantId } from "../index";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

interface ViewerDb {
  reportView: {
    create: (args: Record<string, unknown>) => Promise<unknown>;
    findMany: (args: Record<string, unknown>) => Promise<unknown[]>;
  };
}

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

/**
 * Validate a report token by proxying to the engine's report token endpoint.
 * Returns job data on success, or null on failure.
 */
async function validateToken(
  token: string,
): Promise<{ jobId: string; tenantId: string; fileName: string; emailRequired: boolean } | null> {
  try {
    const resp = await fetch(
      engineUrl(`/api/v1/reports/tokens/${token}`),
      { headers: authHeaders() },
    );
    if (!resp.ok) return null;
    const data = await resp.json() as Record<string, unknown>;
    return {
      jobId: (data.job_id ?? data.jobId) as string,
      tenantId: (data.tenant_id ?? data.tenantId ?? "") as string,
      fileName: (data.file_name ?? data.fileName ?? "Untitled") as string,
      emailRequired: (data.email_required ?? data.emailRequired ?? true) as boolean,
    };
  } catch {
    return null;
  }
}

export function viewerRoutes(db?: ViewerDb): RouteDefinition[] {
  return [
    // ── Authenticated viewer proxy routes ──────────────────
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
      path: "/viewer/:jobId/interpretation",
      auth: true,
      permission: "preflight:view",
      description:
        "Get AI interpretation for a job (proxies to engine captains-log)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await fetch(
          engineUrl(`/api/v1/captains-log/${req.params.jobId}/interpret`),
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

    // ── Public viewer routes (no auth) ─────────────────────

    {
      method: "GET" as HttpMethod,
      path: "/viewer/public/:token/job",
      auth: false,
      description: "Get job data for public viewing via report token",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tokenData = await validateToken(req.params.token);
        if (!tokenData) {
          return { status: 404, body: { error: "Invalid or expired token" } };
        }
        return {
          status: 200,
          body: {
            jobId: tokenData.jobId,
            tenantId: tokenData.tenantId,
            fileName: tokenData.fileName,
            emailRequired: tokenData.emailRequired,
          },
        };
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/viewer/public/:token/identify",
      auth: false,
      description: "Identify viewer for public report access and record view",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tokenData = await validateToken(req.params.token);
        if (!tokenData) {
          return { status: 404, body: { error: "Invalid or expired token" } };
        }

        const { email, name } = req.body as { email?: string; name?: string };
        if (tokenData.emailRequired && !email) {
          return { status: 400, body: { error: "Email is required" } };
        }

        // Record the view in Prisma
        if (db) {
          try {
            await db.reportView.create({
              data: {
                jobId: tokenData.jobId,
                tenantId: tokenData.tenantId,
                reportToken: req.params.token,
                viewerEmail: email ?? null,
                viewerName: name ?? null,
                ipAddress: req.headers?.["x-forwarded-for"] ?? req.headers?.["x-real-ip"] ?? null,
                userAgent: req.headers?.["user-agent"] ?? null,
              },
            });
          } catch {
            // Non-fatal — don't block viewer access if tracking fails
          }
        }

        return {
          status: 200,
          body: {
            success: true,
            jobId: tokenData.jobId,
          },
        };
      }) as RouteHandler,
    },

    // ── View tracking routes (auth required) ───────────────

    {
      method: "POST" as HttpMethod,
      path: "/viewer/:jobId/track-view",
      auth: true,
      permission: "preflight:view",
      description: "Record an authenticated view of a job report",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        if (db) {
          try {
            await db.reportView.create({
              data: {
                jobId: req.params.jobId,
                tenantId,
                reportToken: "",
                viewerEmail: req.auth?.email ?? null,
                viewerName: (req.auth as Record<string, unknown>)?.name as string | null ?? null,
                ipAddress: req.headers?.["x-forwarded-for"] ?? req.headers?.["x-real-ip"] ?? null,
                userAgent: req.headers?.["user-agent"] ?? null,
              },
            });
          } catch {
            return { status: 500, body: { error: "Failed to record view" } };
          }
        }

        return { status: 200, body: { success: true } };
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/viewer/:jobId/views",
      auth: true,
      permission: "preflight:view",
      description: "List all views for a job",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        const tenantId = req.auth?.tenantId;
        if (!tenantId) {
          return { status: 400, body: { error: "Missing tenant context" } };
        }

        if (!db) {
          return { status: 200, body: [] };
        }

        try {
          const views = await db.reportView.findMany({
            where: { jobId: req.params.jobId, tenantId },
            orderBy: { viewedAt: "desc" },
          });
          return { status: 200, body: views };
        } catch {
          return { status: 500, body: { error: "Failed to fetch views" } };
        }
      }) as RouteHandler,
    },
  ];
}
