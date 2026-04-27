/**
 * Substrate ICC profile route forwarder.
 *
 * Single-active-slot per tenant. Forwards multipart upload + GET / DELETE
 * to the engine's ``/api/v1/icc-profiles/active`` endpoint so the
 * dashboard can let tenants set / view / clear their substrate ICC
 * profile (drives the EPM-A1 substrate-aware path).
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";

function baseUrl(): string {
  return (process.env.LINTPDF_API_URL ?? "https://api.lintpdf.com").replace(
    /\/$/,
    "",
  );
}

function tenantHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return headers;
}

export function iccProfileRoutes(): RouteDefinition[] {
  return [
    {
      method: "POST",
      path: "/icc-profiles/active",
      auth: true,
      permission: "preflight:submit",
      description:
        "Upload + activate the tenant's substrate ICC profile (drives EPM-A1).",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        // The plugin runtime hands us the parsed multipart form via
        // req.body. Forward the request stream as-is to the engine
        // because re-encoding bytes through JSON would balloon the
        // payload. Plugin framework hands us req.rawBody for that.
        const rawBody =
          (req as unknown as { rawBody?: Uint8Array | Buffer }).rawBody ??
          (typeof req.body === "string" ? req.body : undefined);
        if (!rawBody) {
          return {
            status: 400,
            body: { error: "missing multipart body" },
          };
        }
        const headers: Record<string, string> = { ...tenantHeaders() };
        const contentType = req.headers["content-type"];
        if (contentType) {
          headers["Content-Type"] = contentType;
        }
        const resp = await fetch(`${baseUrl()}/api/v1/icc-profiles/active`, {
          method: "POST",
          headers,
          body: rawBody as unknown as ArrayBuffer,
        });
        const text = await resp.text();
        if (!resp.ok) {
          return { status: resp.status, body: { error: text } };
        }
        return {
          status: resp.status,
          body: text ? JSON.parse(text) : null,
        };
      },
    },
    {
      method: "GET",
      path: "/icc-profiles/active",
      auth: true,
      permission: "preflight:view",
      description: "Get metadata for the tenant's active ICC profile (or null).",
      handler: async (): Promise<RouteResponse> => {
        const resp = await fetch(`${baseUrl()}/api/v1/icc-profiles/active`, {
          headers: tenantHeaders(),
        });
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        const text = await resp.text();
        return {
          status: 200,
          body: text ? JSON.parse(text) : null,
        };
      },
    },
    {
      method: "DELETE",
      path: "/icc-profiles/active",
      auth: true,
      permission: "preflight:submit",
      description: "Clear the tenant's active ICC profile.",
      handler: async (): Promise<RouteResponse> => {
        const resp = await fetch(`${baseUrl()}/api/v1/icc-profiles/active`, {
          method: "DELETE",
          headers: tenantHeaders(),
        });
        if (!resp.ok && resp.status !== 204) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 204 };
      },
    },
  ];
}
