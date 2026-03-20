/**
 * Webhook receiver route for Grounded events.
 */

import type {
  PluginContext,
  RouteDefinition,
  RouteRequest,
  RouteResponse,
} from "@thinkneverland/pixie-dust-fairy-ring";
import type { GroundedPluginConfig } from "../config";
import type { PixieDustPayload } from "../types";
import { validateWebhookSignature } from "../webhook";

export function webhookRoutes(config: GroundedPluginConfig, ctx: PluginContext): RouteDefinition[] {
  return [
    {
      method: "POST",
      path: "/webhooks",
      auth: false, // Uses HMAC signature verification, not session auth
      description: "Receive Grounded webhook events (HMAC-signed)",
      handler: async (req: RouteRequest): Promise<RouteResponse> => {
        const signature = req.headers["x-grounded-signature"] ?? "";
        const body = typeof req.body === "string" ? req.body : JSON.stringify(req.body);

        if (!validateWebhookSignature(body, signature, config.webhookSecret)) {
          ctx.services.logger.warn("Grounded webhook: invalid signature");
          return { status: 401, body: { error: "Invalid signature" } };
        }

        const payload = req.body as PixieDustPayload;

        if (!payload.event || !payload.job_id) {
          return { status: 400, body: { error: "Invalid payload" } };
        }

        // Map backend event names to plugin hook names
        const eventMap: Record<string, string> = {
          "preflight.complete": "grounded:job.completed",
          "preflight.failed": "grounded:job.failed",
        };

        const hookName = eventMap[payload.event];
        if (!hookName) {
          ctx.services.logger.warn(`Grounded webhook: unknown event type '${payload.event}'`);
          return { status: 422, body: { error: `Unknown event type: ${payload.event}` } };
        }

        await ctx.emit(hookName, payload);

        ctx.services.logger.info(`Grounded webhook: ${payload.event}`, {
          jobId: payload.job_id,
          passed: payload.passed,
        });

        return { status: 200, body: { received: true } };
      },
    },
  ];
}
