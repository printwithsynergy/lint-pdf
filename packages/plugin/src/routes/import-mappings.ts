/**
 * Import-mapping proxy routes — forward tenant custom-mapping CRUD and
 * preview calls to the LintPDF engine.
 *
 * Mappings let tenants describe how to pull finding fields out of
 * proprietary preflight XML / JSON without us shipping a new parser.
 */

import type {
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

async function forward(
  resp: Response,
  okStatus = 200,
): Promise<RouteResponse> {
  if (!resp.ok) {
    return { status: resp.status, body: { error: await resp.text() } };
  }
  if (resp.status === 204) {
    return { status: 204 };
  }
  return { status: okStatus, body: await resp.json() };
}

export function importMappingsRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET" as HttpMethod,
      path: "/import-mappings",
      auth: true,
      permission: "branding:manage",
      description: "List tenant-defined import mappings",
      handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
        return forward(await engineFetch("/api/v1/tenant/import-mappings"));
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/import-mappings",
      auth: true,
      permission: "branding:manage",
      description: "Create a tenant-defined import mapping",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        return forward(
          await engineFetch("/api/v1/tenant/import-mappings", {
            method: "POST",
            body: JSON.stringify(req.body),
          }),
          201,
        );
      }) as RouteHandler,
    },
    {
      method: "GET" as HttpMethod,
      path: "/import-mappings/:mappingId",
      auth: true,
      permission: "branding:manage",
      description: "Get a single tenant-defined import mapping",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        return forward(
          await engineFetch(
            `/api/v1/tenant/import-mappings/${req.params.mappingId}`,
          ),
        );
      }) as RouteHandler,
    },
    {
      method: "PUT" as HttpMethod,
      path: "/import-mappings/:mappingId",
      auth: true,
      permission: "branding:manage",
      description: "Update a tenant-defined import mapping",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        return forward(
          await engineFetch(
            `/api/v1/tenant/import-mappings/${req.params.mappingId}`,
            { method: "PUT", body: JSON.stringify(req.body) },
          ),
        );
      }) as RouteHandler,
    },
    {
      method: "DELETE" as HttpMethod,
      path: "/import-mappings/:mappingId",
      auth: true,
      permission: "branding:manage",
      description: "Soft-delete a tenant-defined import mapping",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        return forward(
          await engineFetch(
            `/api/v1/tenant/import-mappings/${req.params.mappingId}`,
            { method: "DELETE" },
          ),
          204,
        );
      }) as RouteHandler,
    },
    {
      method: "POST" as HttpMethod,
      path: "/import-mappings/:mappingId/preview",
      auth: true,
      permission: "branding:manage",
      description:
        "Preview an import mapping against a sample payload (no persist)",
      handler: (async (req: RouteRequest): Promise<RouteResponse> => {
        return forward(
          await engineFetch(
            `/api/v1/tenant/import-mappings/${req.params.mappingId}/preview`,
            { method: "POST", body: JSON.stringify(req.body ?? {}) },
          ),
        );
      }) as RouteHandler,
    },
  ];
}
