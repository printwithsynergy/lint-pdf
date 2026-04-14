/**
 * LintPDF PDF Preflight — Fairy Ring plugin for Pixie Dust.
 *
 * Core plugin: preflight job management, rulesets, and webhook ingestion.
 * Sub-plugins handle usage, waitlist, billing, reports, team, account, and site admin.
 */

import type {
  PixieDustPlugin,
  PluginContext,
} from "@thinkneverland/pixie-dust-fairy-ring";

import { LintPDFClient } from "./client";
import { lintpdfConfigSchema } from "./config";
import { webhookRoutes } from "./routes/index";
import { jobRoutes } from "./routes/jobs";
import { profileRoutes } from "./routes/profiles";
import { aiConfigRoutes } from "./routes/ai-config";
import { colorConfigRoutes } from "./routes/color-config";
import { viewerRoutes } from "./routes/viewer";
import { brandingRoutes } from "./routes/branding";
import { importMappingsRoutes } from "./routes/import-mappings";
import { approvalRoutes } from "./routes/approvals";
import { annotationRoutes } from "./routes/annotations";

// ── Public exports ──────────────────────────────────────────

export const PLUGIN_NAME = "lintpdf" as const;

export { LintPDFClient } from "./client";
export { lintpdfConfigSchema, type LintPDFPluginConfig } from "./config";
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

export { lintpdfUsagePlugin } from "./plugins/usage/index";
export { lintpdfApiKeysPlugin } from "./plugins/api-keys/index";
export { lintpdfReportsPlugin } from "./plugins/reports/index";
export { lintpdfAccountPlugin } from "./plugins/account/index";
export { lintpdfSiteAdminPlugin } from "./plugins/site-admin/index";
export { lintpdfWebhooksPlugin } from "./plugins/webhooks/index";
export { lintpdfEndpointsPlugin } from "./plugins/endpoints/index";
export { lintpdfSuperAdminPlugin } from "./plugins/super-admin/index";

// ── Client singleton ────────────────────────────────────────

let _client: LintPDFClient | null = null;

export function getClient(): LintPDFClient | null {
  return _client;
}

// ── Engine tenant ID resolver ──────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _pluginDb: any = null;

export function setPluginDb(db: unknown): void {
  _pluginDb = db;
}

/**
 * Resolve a Prisma tenant ID (cuid) to the engine's UUID tenant ID.
 * Returns the engine UUID or falls back to the cuid if no mapping exists.
 */
export async function resolveEngineTenantId(tenantId: string): Promise<string> {
  if (!_pluginDb) return process.env.ENGINE_ADMIN_TENANT_ID ?? tenantId;
  try {
    const tenant = await _pluginDb.tenant.findUnique({
      where: { id: tenantId },
      select: { engineTenantId: true },
    });
    return tenant?.engineTenantId ?? process.env.ENGINE_ADMIN_TENANT_ID ?? tenantId;
  } catch {
    return process.env.ENGINE_ADMIN_TENANT_ID ?? tenantId;
  }
}

// ── Core plugin ─────────────────────────────────────────────

export const lintpdfPlugin: PixieDustPlugin = {
  name: "lintpdf",
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
    const parsed = lintpdfConfigSchema.safeParse({
      apiUrl: env.LINTPDF_API_URL ?? "https://api.lintpdf.com",
      webhookSecret: env.LINTPDF_WEBHOOK_SECRET ?? "",
      apiKey: env.LINTPDF_API_KEY,
    });

    if (!parsed.success) {
      ctx.services.logger.warn("LintPDF plugin: missing config, skipping");
      return;
    }

    const config = parsed.data;
    _client = new LintPDFClient(config);

    // Store DB reference for engine tenant ID resolution
    setPluginDb(ctx.services.db);

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
    ctx.addPermission("ruleset:manage", ["ADMIN", "OWNER"]);
    ctx.addPermission("branding:manage", ["ADMIN", "OWNER"]);
    ctx.addPermission("annotation:create", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
    ]);

    // ── Navigation ──
    ctx.addNavItem({
      label: "Preflight",
      href: "/dashboard/preflight",
      icon: "compass",
      section: "main",
      order: 40,
      requiredPermission: "preflight:view",
    });
    ctx.addNavItem({
      label: "Rulesets",
      href: "/dashboard/rulesets",
      icon: "list",
      section: "main",
      order: 41,
      requiredPermission: "ruleset:manage",
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
      path: "/dashboard/rulesets",
      title: "Rulesets",
      layout: "dashboard",
    });
    ctx.addPage({
      path: "/dashboard/preflight/[jobId]/viewer",
      title: "PDF Viewer",
      layout: "dashboard",
    });

    // ── Public paths (HMAC-authenticated, not session-authenticated) ──
    ctx.addPublicPath("/api/lintpdf/webhooks");
    ctx.addPublicPath("/api/lintpdf/viewer/public");

    // ── Routes ──
    ctx.addRoutes("/api/lintpdf", [
      ...webhookRoutes(config, ctx),
      ...jobRoutes(),
      ...profileRoutes(),
      ...aiConfigRoutes(),
      ...colorConfigRoutes(),
      ...viewerRoutes(ctx.services.db as Parameters<typeof viewerRoutes>[0]),
      ...brandingRoutes(),
      ...importMappingsRoutes(),
      ...annotationRoutes(ctx.services.db as Parameters<typeof annotationRoutes>[0]),
      ...approvalRoutes(),
    ]);

    // ── Hooks ──
    ctx.on("lintpdf:job.completed", (data) => {
      ctx.services.logger.info("Preflight completed", { data });
    });
    ctx.on("lintpdf:job.failed", (data) => {
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
