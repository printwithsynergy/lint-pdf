/**
 * Usage metering plugin — extracted from the main LintPDF plugin.
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { resolveEngineTenantId } from "../../index";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

// ---------------------------------------------------------------------------
// Helper: proxy fetch to the LintPDF engine admin API
// ---------------------------------------------------------------------------
//
// The tenant-facing `/api/v1/usage` endpoint resolves its tenant from a
// `Authorization: Bearer <api_key>` header — which works for API key
// clients but not for the dashboard's session-authenticated users. To
// show each user the usage for *their* tenant (not whatever tenant the
// app's shared API key happens to belong to), we proxy through the
// engine admin endpoint `/api/v1/admin/tenants/{tenant_id}/usage` with
// the admin key and the resolved engine tenant id from
// `req.auth.tenantId`.
function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const baseUrl = (
    process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com"
  ).replace(/\/$/, "");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const adminKey = process.env.LINTPDF_ADMIN_API_KEY;
  if (adminKey) {
    headers["X-Admin-Key"] = adminKey;
  }
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export const lintpdfUsagePlugin: PixieDustPlugin = {
  name: "lintpdf-usage",
  version: "0.1.0",
  description: "Usage metering and rate-limit visibility for LintPDF preflight",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("usage:view", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
      "VIEWER",
    ]);

    // Navigation
    ctx.addNavItem({
      label: "Usage",
      href: "/dashboard/usage",
      icon: "bar-chart",
      section: "main",
      order: 42,
      requiredPermission: "usage:view",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/usage",
      title: "Usage & Limits",
      layout: "dashboard",
    });

    // Routes
    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/usage",
        auth: true,
        permission: "usage:view",
        description: "Get current usage and rate-limit status",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return {
              status: 400,
              body: { error: "Missing tenant context" },
            };
          }
          const engineId = await resolveEngineTenantId(tenantId);
          ctx.services.logger.info("Usage: resolve", {
            data: { appTenantId: tenantId, engineTenantId: engineId },
          });
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${encodeURIComponent(engineId)}/usage`,
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          return { status: 200, body: await resp.json() };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/lintpdf", routes);

    // Hooks
    ctx.on("lintpdf:job.completed", (data) => {
      ctx.services.logger.info("Usage plugin: job completed", {
        data: data as Record<string, unknown>,
      });
    });
  },
};
