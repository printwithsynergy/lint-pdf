/**
 * Desktop app download plugin.
 *
 * Surfaces a "Desktop App" nav item and `/dashboard/downloads` page for
 * tenants whose `desktop_app_enabled` entitlement is flipped on. The
 * actual entitlement check + presigned URL generation happens on the
 * engine side — this plugin is just the session-authenticated proxy.
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
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export const lintpdfDownloadsPlugin: PixieDustPlugin = {
  name: "lintpdf-downloads",
  version: "0.1.0",
  description: "Desktop app downloads for licensed tenants",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Role-open; entitlement is the real gate (checked on engine side).
    ctx.addPermission("downloads:view", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
      "VIEWER",
    ]);

    ctx.addNavItem({
      label: "Desktop App",
      href: "/dashboard/downloads",
      icon: "download",
      section: "main",
      order: 45,
      requiredPermission: "downloads:view",
    });

    ctx.addPage({
      path: "/dashboard/downloads",
      title: "Desktop App",
      layout: "dashboard",
    });

    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/desktop",
        auth: true,
        permission: "downloads:view",
        description:
          "Get desktop app download manifest for the current tenant. " +
          "Returns { entitled: boolean, manifest?: {...} }.",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          const isSuperAdmin = req.auth?.isSuperAdmin ?? false;

          // Super admins without a tenant context (no impersonation) get
          // the admin manifest directly — useful for previews and QA.
          if (isSuperAdmin && !tenantId) {
            const resp = await adminFetch(
              `/api/v1/admin/downloads/desktop/manifest`,
            );
            if (resp.status === 404) {
              return {
                status: 200,
                body: { entitled: true, manifest: null, noRelease: true },
              };
            }
            if (!resp.ok) {
              return {
                status: 200,
                body: { entitled: false, manifest: null },
              };
            }
            const manifest = await resp.json();
            return {
              status: 200,
              body: { entitled: true, manifest },
            };
          }

          if (!tenantId) {
            return {
              status: 400,
              body: { error: "Missing tenant context" },
            };
          }

          const engineId = await resolveEngineTenantId(tenantId);
          const resp = await adminFetch(
            `/api/v1/admin/downloads/desktop/tenants/${engineId}/manifest`,
          );

          if (resp.status === 403) {
            return {
              status: 200,
              body: { entitled: false, manifest: null },
            };
          }
          if (resp.status === 404) {
            // No release published yet
            return {
              status: 200,
              body: { entitled: true, manifest: null, noRelease: true },
            };
          }
          if (!resp.ok) {
            const detail = await resp.text();
            ctx.services.logger.warn(
              "lintpdf-downloads: engine returned non-ok status",
              { status: resp.status, detail: detail.slice(0, 200) },
            );
            return {
              status: 502,
              body: { error: "Engine unreachable", detail: detail.slice(0, 200) },
            };
          }

          const manifest = await resp.json();
          return {
            status: 200,
            body: { entitled: true, manifest },
          };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/lintpdf/downloads", routes);
  },
};
