/**
 * Workflows routes (Phase 0.7 unified-config substrate).
 *
 * Replaces the legacy CustomEndpoint surface. A Workflow pins a name +
 * profile_id + brand_spec_id + per-call ToggleOverride defaults so
 * tenants can submit jobs against a curated configuration without
 * re-specifying every field.
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

function tenantFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  const apiKey = process.env.LINTPDF_API_KEY;
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }
  return fetch(`${baseUrl()}${path}`, { ...init, headers });
}

export function workflowRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET",
      path: "/workflows",
      auth: true,
      permission: "preflight:view",
      description: "List workflows for the current tenant",
      handler: async (): Promise<RouteResponse> => {
        const resp = await tenantFetch("/api/v1/workflows");
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
    {
      method: "POST",
      path: "/workflows",
      auth: true,
      permission: "preflight:submit",
      description: "Create a workflow",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch("/api/v1/workflows", {
          method: "POST",
          body: JSON.stringify(req.body ?? {}),
        });
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: resp.status, body: await resp.json() };
      },
    },
    {
      method: "PATCH",
      path: "/workflows/:workflowId",
      auth: true,
      permission: "preflight:submit",
      description: "Update a workflow",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/workflows/${req.params.workflowId}`,
          {
            method: "PATCH",
            body: JSON.stringify(req.body ?? {}),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
    {
      method: "DELETE",
      path: "/workflows/:workflowId",
      auth: true,
      permission: "preflight:submit",
      description: "Delete a workflow",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/workflows/${req.params.workflowId}`,
          { method: "DELETE" },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 204 };
      },
    },
    // ---- toggle registry (read-only, drives the per-workflow editor) ----
    {
      method: "GET",
      path: "/toggles",
      auth: true,
      permission: "preflight:view",
      description: "List the toggle registry (used by the per-workflow defaults editor)",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const category =
          (req.query as Record<string, string | undefined> | undefined)
            ?.category ?? "";
        const qs = category ? `?category=${encodeURIComponent(category)}` : "";
        const resp = await tenantFetch(`/api/v1/toggles${qs}`);
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
    // ---- per-workflow override CRUD --------------------------------------
    {
      method: "GET",
      path: "/workflows/:workflowId/toggles",
      auth: true,
      permission: "preflight:view",
      description: "List workflow-scoped toggle overrides",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/workflows/${req.params.workflowId}/toggles`,
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
    {
      method: "PUT",
      path: "/workflows/:workflowId/toggles/:toggleId",
      auth: true,
      permission: "preflight:submit",
      description: "Set a per-workflow toggle default",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/workflows/${req.params.workflowId}/toggles/${req.params.toggleId}`,
          {
            method: "PUT",
            body: JSON.stringify(req.body ?? {}),
          },
        );
        if (!resp.ok) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 200, body: await resp.json() };
      },
    },
    {
      method: "DELETE",
      path: "/workflows/:workflowId/toggles/:toggleId",
      auth: true,
      permission: "preflight:submit",
      description: "Clear a per-workflow toggle default",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const resp = await tenantFetch(
          `/api/v1/workflows/${req.params.workflowId}/toggles/${req.params.toggleId}`,
          { method: "DELETE" },
        );
        if (!resp.ok && resp.status !== 204) {
          return { status: resp.status, body: { error: await resp.text() } };
        }
        return { status: 204 };
      },
    },
  ];
}
