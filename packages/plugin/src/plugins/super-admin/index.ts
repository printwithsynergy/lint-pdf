/**
 * Super Admin plugin — auto-provisions a "house" tenant for super admins
 * with unlimited entitlements and no billing requirement.
 *
 * Also provides the impersonation context resolution for plugin routes.
 */

import type {
  PixieDustPlugin,
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

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

/**
 * The unlimited entitlement overrides applied to super admin tenants.
 * This gives super admins access to 100% of features with no limits.
 */
const UNLIMITED_ENTITLEMENTS = {
  rate_limit_daily: 999999999,
  max_file_size_mb: 99999,
  max_custom_profiles: 9999,
  max_webhooks: 9999,
  report_storage_mb: 9999999,
  webhooks_enabled: true,
  whitelabel_enabled: true,
  priority_processing: true,
  custom_integrations: true,
  custom_profiles: true,
  ai_enabled: true,
};

export const lintpdfSuperAdminPlugin: PixieDustPlugin = {
  name: "lintpdf-super-admin",
  version: "0.1.0",
  description:
    "Super admin house tenant provisioning and impersonation support",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Navigation — "My Workspace" was a redundant alias for /dashboard/preflight.
    // Removed; super admins reach Preflight via the standard nav like everyone
    // else, with the impersonation/admin entry points kept under ADMIN.

    const routes: RouteDefinition[] = [
      {
        method: "POST" as HttpMethod,
        path: "/provision-admin-tenant",
        auth: true,
        permission: "site-admin:access",
        description:
          "Auto-provision a house tenant for the super admin with unlimited entitlements",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const userId = req.auth?.userId;
          if (!userId) {
            return { status: 400, body: { error: "Missing user context" } };
          }

          // Create a tenant in the engine with enterprise plan
          const createResp = await adminFetch("/api/v1/admin/tenants", {
            method: "POST",
            body: JSON.stringify({
              name: "Admin Workspace",
              contact_email: "admin@lintpdf.com",
              plan: "enterprise",
            }),
          });

          if (!createResp.ok) {
            const detail = await createResp.text();
            return {
              status: createResp.status,
              body: { error: `Failed to create tenant: ${detail}` },
            };
          }

          const tenant = (await createResp.json()) as Record<string, unknown>;
          const engineTenantId = tenant.id ?? tenant.tenant_id;

          // Apply unlimited entitlement overrides
          const entResp = await adminFetch(
            `/api/v1/admin/tenants/${engineTenantId}/entitlements`,
            {
              method: "PATCH",
              body: JSON.stringify(UNLIMITED_ENTITLEMENTS),
            },
          );

          if (!entResp.ok) {
            ctx.services.logger.warn(
              "Super admin plugin: failed to set unlimited entitlements",
              { tenantId: engineTenantId },
            );
          }

          return {
            status: 201,
            body: {
              tenantId: engineTenantId,
              message:
                "Admin workspace created with unlimited entitlements. No billing required.",
            },
          };
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/admin-entitlements/:tenantId",
        auth: true,
        permission: "site-admin:access",
        description:
          "Apply unlimited entitlements to any tenant (super admin only)",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${req.params.tenantId}/entitlements`,
            {
              method: "PATCH",
              body: JSON.stringify(UNLIMITED_ENTITLEMENTS),
            },
          );

          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }

          return {
            status: 200,
            body: { message: "Unlimited entitlements applied" },
          };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/lintpdf/super-admin", routes);
  },
};
