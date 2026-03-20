/**
 * Account self-service plugin — tenant settings, branding, and configuration.
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

interface AccountDb {
  appSettings: {
    upsert: (args: Record<string, unknown>) => Promise<unknown>;
  };
}

// ---------------------------------------------------------------------------
// Helper: proxy fetch to the Grounded engine admin API
// ---------------------------------------------------------------------------

function adminFetch(path: string, init?: RequestInit): Promise<Response> {
  const baseUrl = (
    process.env.GROUNDED_API_URL ?? "https://api.grounded.dev"
  ).replace(/\/$/, "");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const adminKey = process.env.GROUNDED_ADMIN_API_KEY;
  if (adminKey) {
    headers["X-Admin-Key"] = adminKey;
  }
  const apiKey = process.env.GROUNDED_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl}${path}`, { ...init, headers });
}

export const groundedAccountPlugin: PixieDustPlugin = {
  name: "grounded-account",
  version: "0.1.0",
  description: "Tenant account settings, branding, and self-service management",
  dependencies: ["grounded"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("account:manage", ["ADMIN", "OWNER"]);

    // Navigation
    ctx.addNavItem({
      label: "Account",
      href: "/dashboard/account",
      icon: "settings",
      section: "tenant",
      order: 10,
      requiredPermission: "account:manage",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/account",
      title: "Account",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/account/settings",
      title: "Settings",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/account/branding",
      title: "Branding",
      layout: "dashboard",
    });

    // Routes
    const db = ctx.services.db as AccountDb;

    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/",
        auth: true,
        permission: "account:manage",
        description: "Get tenant account information",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const resp = await adminFetch(`/api/v1/admin/tenants/${tenantId}`);
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/",
        auth: true,
        permission: "account:manage",
        description: "Update tenant account settings",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }
          const resp = await adminFetch(`/api/v1/admin/tenants/${tenantId}`, {
            method: "PATCH",
            body: JSON.stringify(req.body),
          });
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const data = await resp.json();
          return { status: 200, body: data };
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/branding",
        auth: true,
        permission: "account:manage",
        description: "Update tenant branding settings",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const tenantId = req.auth?.tenantId;
          if (!tenantId) {
            return { status: 400, body: { error: "Missing tenant context" } };
          }

          // 1. Update branding in the Grounded engine
          const resp = await adminFetch(
            `/api/v1/admin/tenants/${tenantId}/branding`,
            {
              method: "PATCH",
              body: JSON.stringify(req.body),
            },
          );
          if (!resp.ok) {
            const detail = await resp.text();
            return { status: resp.status, body: { error: detail } };
          }
          const engineData = await resp.json();

          // 2. Sync branding to Pixie Dust AppSettings
          try {
            const branding = req.body as Record<string, unknown>;
            await db.appSettings.upsert({
              where: { tenantId },
              update: {
                brandName: branding.name ?? undefined,
                brandLogoUrl: branding.logo_url ?? undefined,
                primaryColor: branding.primary_color ?? undefined,
                accentColor: branding.accent_color ?? undefined,
              },
              create: {
                tenantId,
                brandName: (branding.name as string) ?? "",
                brandLogoUrl: (branding.logo_url as string) ?? null,
                primaryColor: (branding.primary_color as string) ?? "#000000",
                accentColor: (branding.accent_color as string) ?? "#0066FF",
              },
            });
          } catch (err) {
            ctx.services.logger.warn(
              "Account plugin: failed to sync branding to AppSettings",
              {
                tenantId,
                error: err instanceof Error ? err.message : String(err),
              },
            );
          }

          return { status: 200, body: engineData };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/grounded/account", routes);
  },
};
