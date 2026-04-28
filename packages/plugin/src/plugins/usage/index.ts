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
      {
        method: "GET" as HttpMethod,
        path: "/ai-credits",
        auth: true,
        permission: "usage:view",
        description: "Current AI credit balance + monthly allotment",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const engineId = await resolveEngineTenantId(tenantId);
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${encodeURIComponent(engineId)}/ai/credits`,
          );
          if (!resp.ok) {
            // 404 / 403 are expected when AI is disabled — treat as empty.
            if (resp.status === 404 || resp.status === 403) {
              return {
                status: 200,
                body: {
                  enabled: false,
                  balance: 0,
                  monthly_allotment: 0,
                  consumed_this_month: 0,
                },
              };
            }
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = (await resp.json()) as Record<string, unknown>;
          return {
            status: 200,
            body: { enabled: true, ...data },
          };
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/ai-usage",
        auth: true,
        permission: "usage:view",
        description: "Recent AI inspection usage history",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const engineId = await resolveEngineTenantId(tenantId);
          const rawLimit = req.query?.limit;
          const limit =
            typeof rawLimit === "string"
              ? rawLimit
              : Array.isArray(rawLimit) && typeof rawLimit[0] === "string"
                ? rawLimit[0]
                : "20";
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${encodeURIComponent(engineId)}/ai/usage?limit=${encodeURIComponent(limit)}`,
          );
          if (!resp.ok) {
            if (resp.status === 404 || resp.status === 403) {
              return {
                status: 200,
                body: { enabled: false, items: [] },
              };
            }
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = (await resp.json()) as
            | unknown[]
            | { items?: unknown[] };
          const items = Array.isArray(data)
            ? data
            : Array.isArray(data?.items)
              ? data.items
              : [];
          return {
            status: 200,
            body: { enabled: true, items },
          };
        }) as RouteHandler,
      },
    ];

    // /api/lintpdf/ai/cost-cap — the credits dashboard fetches this to
    // surface a per-tenant LLM spend cap toggle. The engine doesn't
    // expose a REST endpoint for the toggle yet (it's read directly
    // from the unified-config table inside ai_explain), so return
    // `{ enabled: false }` so the page hides the UI cleanly without
    // logging a 404.
    routes.push({
      method: "GET" as HttpMethod,
      path: "/ai/cost-cap",
      auth: true,
      permission: "usage:view",
      description:
        "Cost-cap state for the credits page. Stub until the engine exposes a toggle endpoint.",
      handler: (async (): Promise<RouteResponse> => {
        return {
          status: 200,
          body: { enabled: false, monthly_cap_cents: null, used_this_month_cents: 0 },
        };
      }) as RouteHandler,
    });

    ctx.addRoutes("/api/lintpdf", routes);

    // Hooks
    ctx.on("lintpdf:job.completed", (data) => {
      ctx.services.logger.info("Usage plugin: job completed", {
        data: data as Record<string, unknown>,
      });
    });
  },
};
