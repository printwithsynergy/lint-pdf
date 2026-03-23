/**
 * LintPDF PDF Preflight — Fairy Ring plugin for Pixie Dust.
 *
 * Core plugin: preflight job management, flight plans, and webhook ingestion.
 * Sub-plugins handle usage, waitlist, billing, reports, team, account, and site admin.
 */

import type {
  PixieDustPlugin,
  PluginContext,
} from "@thinkneverland/pixie-dust-fairy-ring";

import { GroundedClient } from "./client";
import { groundedConfigSchema } from "./config";
import { webhookRoutes } from "./routes/index";
import { jobRoutes } from "./routes/jobs";
import { profileRoutes } from "./routes/profiles";
import { aiConfigRoutes } from "./routes/ai-config";
import { colorConfigRoutes } from "./routes/color-config";

// ── Public exports ──────────────────────────────────────────

export const PLUGIN_NAME = "grounded" as const;

export { GroundedClient } from "./client";
export { groundedConfigSchema, type GroundedPluginConfig } from "./config";
export { validateWebhookSignature, parseWebhookEvent } from "./webhook";
export type {
  PreflightJob,
  PreflightFinding,
  PreflightSummary,
  PreflightJobList,
  PreflightProfile,
  PreflightProfileList,
  JobStatus,
  Severity,
  PixieDustPayload,
  PixieDustUsage,
  UsageInfo,
  PluginConfig,
} from "./types";

// ── Sub-plugin exports ──────────────────────────────────────

export { groundedUsagePlugin } from "./plugins/usage/index";
export { groundedApiKeysPlugin } from "./plugins/api-keys/index";
export { groundedReportsPlugin } from "./plugins/reports/index";
export { groundedTeamPlugin } from "./plugins/team/index";
export { groundedAccountPlugin } from "./plugins/account/index";
export { groundedSiteAdminPlugin } from "./plugins/site-admin/index";
export { groundedWebhooksPlugin } from "./plugins/webhooks/index";
export { groundedEndpointsPlugin } from "./plugins/endpoints/index";
export { groundedSuperAdminPlugin } from "./plugins/super-admin/index";

// ── Client singleton ────────────────────────────────────────

let _client: GroundedClient | null = null;

export function getClient(): GroundedClient | null {
  return _client;
}

// ── Engine tenant ID resolver ──────────────────────────────

let _db: { tenant: { findUnique: (args: Record<string, unknown>) => Promise<{ engineTenantId: string | null } | null> } } | null = null;

export function setPluginDb(db: typeof _db): void {
  _db = db;
}

/**
 * Resolve a Prisma tenant ID (cuid) to the engine's UUID tenant ID.
 * Returns the engine UUID or falls back to the cuid if no mapping exists.
 */
export async function resolveEngineTenantId(tenantId: string): Promise<string> {
  if (!_db) return tenantId;
  try {
    const tenant = await _db.tenant.findUnique({
      where: { id: tenantId } as Record<string, unknown>,
      select: { engineTenantId: true } as Record<string, unknown>,
    } as Record<string, unknown>) as { engineTenantId: string | null } | null;
    return tenant?.engineTenantId ?? tenantId;
  } catch {
    return tenantId;
  }
}

// ── Core plugin ─────────────────────────────────────────────

export const groundedPlugin: PixieDustPlugin = {
  name: "grounded",
  version: "0.1.0",
  description: "PDF preflight engine — inspect, report, never modify",
  dependencies: [],

  register(ctx: PluginContext): void {
    if (_client !== null) {
      ctx.services.logger.warn(
        "LintPDF plugin: already registered, skipping duplicate",
      );
      return;
    }

    const env = process.env as Record<string, string>;
    const parsed = groundedConfigSchema.safeParse({
      apiUrl: env.GROUNDED_API_URL ?? "https://api.lintpdf.com",
      webhookSecret: env.GROUNDED_WEBHOOK_SECRET ?? "",
      apiKey: env.GROUNDED_API_KEY,
    });

    if (!parsed.success) {
      ctx.services.logger.warn("LintPDF plugin: missing config, skipping");
      return;
    }

    const config = parsed.data;
    _client = new GroundedClient(config);

    // Store DB reference for engine tenant ID resolution
    setPluginDb(ctx.services.db as typeof _db);

    // ── Custom role ──
    ctx.addRole("OPERATOR");

    // ── Permissions ──
    ctx.addPermission("preflight:submit", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
    ]);
    ctx.addPermission("preflight:view", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
      "VIEWER",
    ]);
    ctx.addPermission("flight-plan:manage", ["ADMIN", "OWNER"]);

    // ── Navigation ──
    ctx.addNavItem({
      label: "Preflight",
      href: "/dashboard/preflight",
      icon: "plane",
      section: "main",
      order: 40,
      requiredPermission: "preflight:view",
    });
    ctx.addNavItem({
      label: "Flight Plans",
      href: "/dashboard/flight-plans",
      icon: "clipboard-list",
      section: "main",
      order: 41,
      requiredPermission: "flight-plan:manage",
    });

    // ── Pages ──
    ctx.addPage({
      path: "/dashboard/preflight",
      title: "Preflight Jobs",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/preflight/[jobId]",
      title: "Job Details",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/flight-plans",
      title: "Flight Plans",
      layout: "dashboard",
    });

    // ── Public paths (HMAC-authenticated, not session-authenticated) ──
    ctx.addPublicPath("/api/grounded/webhooks");

    // ── Routes ──
    ctx.addRoutes("/api/grounded", [
      ...webhookRoutes(config, ctx),
      ...jobRoutes(),
      ...profileRoutes(),
      ...aiConfigRoutes(),
      ...colorConfigRoutes(),
    ]);

    // ── Hooks ──
    ctx.on("grounded:job.completed", (data) => {
      ctx.services.logger.info("Preflight completed", { data });
    });
    ctx.on("grounded:job.failed", (data) => {
      ctx.services.logger.info("Preflight failed", { data });
    });
  },

  boot(ctx: PluginContext): void {
    if (_client) {
      ctx.services.logger.info("LintPDF plugin ready");
    }
  },

  shutdown(_ctx: PluginContext): void {
    _client = null;
  },
};
