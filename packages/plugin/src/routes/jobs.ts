/**
 * Job proxy routes — forward requests to the LintPDF API.
 */

import type {
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { getClient } from "../index";

export function jobRoutes(): RouteDefinition[] {
  return [
    {
      method: "GET",
      path: "/jobs",
      auth: true,
      permission: "preflight:view",
      description: "List preflight jobs for the current tenant",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const client = getClient();
        if (!client) {
          return { status: 503, body: { error: "LintPDF API not configured" } };
        }
        const page = Number(req.query.page ?? "1");
        const pageSize = Number(req.query.page_size ?? "20");
        const jobs = await client.listJobs(page, pageSize);
        return { status: 200, body: jobs };
      },
    },
    {
      method: "GET",
      path: "/jobs/:jobId",
      auth: true,
      permission: "preflight:view",
      description: "Get a specific preflight job by ID",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const client = getClient();
        if (!client) {
          return { status: 503, body: { error: "LintPDF API not configured" } };
        }
        const job = await client.getJob(req.params.jobId);
        return { status: 200, body: job };
      },
    },
    {
      method: "DELETE",
      path: "/jobs/:jobId",
      auth: true,
      permission: "preflight:submit",
      description: "Delete a preflight job",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const client = getClient();
        if (!client) {
          return { status: 503, body: { error: "LintPDF API not configured" } };
        }
        await client.deleteJob(req.params.jobId);
        return { status: 204 };
      },
    },
  ];
}
