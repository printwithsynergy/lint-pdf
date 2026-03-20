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
import { getClient } from "../../index";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type RouteHandler = (req: RouteRequest) => Promise<RouteResponse>;

export const groundedUsagePlugin: PixieDustPlugin = {
  name: "grounded-usage",
  version: "0.1.0",
  description: "Usage metering and rate-limit visibility for LintPDF preflight",
  dependencies: ["grounded"],

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
      href: "/dashboard/preflight/usage",
      icon: "chart-bar",
      section: "main",
      order: 42,
      requiredPermission: "usage:view",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/preflight/usage",
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
        handler: (async (_req: RouteRequest): Promise<RouteResponse> => {
          const client = getClient();
          if (!client) {
            return {
              status: 503,
              body: { error: "LintPDF API not configured" },
            };
          }
          const usage = await client.getUsage();
          return { status: 200, body: usage };
        }) as RouteHandler,
      },
    ];

    ctx.addRoutes("/api/grounded", routes);

    // Hooks
    ctx.on("grounded:job.completed", (data) => {
      ctx.services.logger.info("Usage plugin: job completed", {
        data: data as Record<string, unknown>,
      });
    });
  },
};
