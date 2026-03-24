/**
 * Webhook management plugin — manage outbound webhook endpoints via the dashboard.
 */

import type {
  PixieDustPlugin,
  PluginContext,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { webhookMgmtRoutes } from "../../routes/webhooks-mgmt";

export const lintpdfWebhooksPlugin: PixieDustPlugin = {
  name: "lintpdf-webhooks",
  version: "0.1.0",
  description: "Manage outbound webhook endpoints for LintPDF event delivery",
  dependencies: ["lintpdf"],

  register(ctx: PluginContext): void {
    // Permissions
    ctx.addPermission("webhooks:manage", ["ADMIN", "OWNER"]);
    ctx.addPermission("webhooks:view", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
      "VIEWER",
    ]);

    // Navigation
    ctx.addNavItem({
      label: "Webhooks",
      href: "/dashboard/webhooks",
      icon: "webhook",
      section: "admin",
      order: 65,
      requiredPermission: "webhooks:manage",
    });

    // Pages
    ctx.addPage({
      path: "/dashboard/webhooks",
      title: "Webhooks",
      layout: "dashboard",
    });

    // Routes
    ctx.addRoutes("/api/lintpdf", webhookMgmtRoutes());
  },
};
