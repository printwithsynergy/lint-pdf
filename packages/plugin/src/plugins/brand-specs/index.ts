/**
 * BrandSpec plugin — per-customer color specifications.
 *
 * Proxies ``/api/lintpdf/brand-specs/*`` requests through to the
 * engine's ``/api/v1/brand-specs/*`` routes and registers the
 * management page + nav entry. Keeps its own plugin file so the
 * endpoints plugin stays focused on slug-vs-profile bindings
 * and this one owns palette CRUD.
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

async function relay(
  resp: Response,
  successStatus?: number,
): Promise<RouteResponse> {
  if (!resp.ok) {
    const detail = await resp.text();
    return { status: resp.status, body: { error: detail } };
  }
  if (resp.status === 204) {
    return { status: 204 };
  }
  return { status: successStatus ?? resp.status, body: await resp.json() };
}

export const lintpdfBrandSpecsPlugin: PixieDustPlugin = {
  name: "lintpdf-brand-specs",
  version: "0.1.0",
  description: "Per-customer brand specifications for LintPDF",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Re-use the endpoints-manage permission — BrandSpec management is
    // an admin concern, same as custom endpoints and profiles.
    ctx.addPermission("endpoints:manage", ["ADMIN", "OWNER"]);

    ctx.addNavItem({
      label: "Brand Specs",
      href: "/dashboard/brand-specs",
      icon: "swatches",
      section: "admin",
      order: 63,
      requiredPermission: "endpoints:manage",
    });

    ctx.addPage({
      path: "/dashboard/brand-specs",
      title: "Brand Specs",
      layout: "dashboard",
    });

    const routes: RouteDefinition[] = [
      {
        method: "GET" as HttpMethod,
        path: "/brand-specs",
        auth: true,
        permission: "endpoints:manage",
        description: "List BrandSpecs for the authenticated tenant",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          const include = req.query?.include_archived
            ? "?include_archived=true"
            : "";
          return relay(await engineFetch(`/api/v1/brand-specs${include}`));
        }) as RouteHandler,
      },
      {
        method: "POST" as HttpMethod,
        path: "/brand-specs",
        auth: true,
        permission: "endpoints:manage",
        description: "Create a BrandSpec",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          return relay(
            await engineFetch("/api/v1/brand-specs", {
              method: "POST",
              body: JSON.stringify(req.body),
            }),
            201,
          );
        }) as RouteHandler,
      },
      {
        method: "GET" as HttpMethod,
        path: "/brand-specs/:specId",
        auth: true,
        permission: "endpoints:manage",
        description: "Get a BrandSpec",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          return relay(
            await engineFetch(`/api/v1/brand-specs/${req.params.specId}`),
          );
        }) as RouteHandler,
      },
      {
        method: "PATCH" as HttpMethod,
        path: "/brand-specs/:specId",
        auth: true,
        permission: "endpoints:manage",
        description: "Update a BrandSpec",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          return relay(
            await engineFetch(`/api/v1/brand-specs/${req.params.specId}`, {
              method: "PATCH",
              body: JSON.stringify(req.body),
            }),
          );
        }) as RouteHandler,
      },
      {
        method: "DELETE" as HttpMethod,
        path: "/brand-specs/:specId",
        auth: true,
        permission: "endpoints:manage",
        description: "Archive a BrandSpec",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          return relay(
            await engineFetch(`/api/v1/brand-specs/${req.params.specId}`, {
              method: "DELETE",
            }),
          );
        }) as RouteHandler,
      },
      {
        method: "POST" as HttpMethod,
        path: "/brand-specs/:specId/restore",
        auth: true,
        permission: "endpoints:manage",
        description: "Restore an archived BrandSpec",
        handler: (async (req: RouteRequest): Promise<RouteResponse> => {
          return relay(
            await engineFetch(
              `/api/v1/brand-specs/${req.params.specId}/restore`,
              { method: "POST" },
            ),
          );
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/lintpdf", routes);
  },
};
