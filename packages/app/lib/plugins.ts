/**
 * Plugin Bootstrap — Fairy Ring integration for the LintPDF app.
 *
 * Loads and boots all registered plugins on app startup.
 * Import this file in instrumentation.ts or layout to trigger bootstrap.
 */

import { env } from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database/server";
import {
  PluginLoader,
  createLogger,
  noopLogger,
} from "@thinkneverland/pixie-dust-fairy-ring";
import type {
  PixieDustPlugin,
  PluginServices,
  Logger,
} from "@thinkneverland/pixie-dust-fairy-ring";
import { stripeKitPlugin } from "@thinkneverland/pixie-dust-stripe-kit";
import {
  BrandingPage,
  AppearancePage,
  ProfilePage,
  UsersPage,
  TenantsPage,
  AuditLogPage,
  TeamPage,
  AdminDashboardPage,
  WorkspaceSettingsPage,
  AccountPage,
} from "@thinkneverland/pixie-dust-dashboard";
import { devtoolsPlugin } from "@thinkneverland/pixie-dust-devtools";
import {
  lintpdfPlugin,
  lintpdfUsagePlugin,
  lintpdfApiKeysPlugin,
  lintpdfReportsPlugin,
  lintpdfAccountPlugin,
  lintpdfSiteAdminPlugin,
  lintpdfWebhooksPlugin,
  lintpdfEndpointsPlugin,
  lintpdfSuperAdminPlugin,
} from "@thinkneverland/grounded-plugin";
import { lintpdfBillingPlugin } from "@lintpdf/stripe";

// ============================================
// LOGGER
// ============================================

let logger: Logger;
try {
  logger = createLogger(console, {
    prefix: "[fairy-ring]",
    debug: env.NODE_ENV !== "production",
  });
} catch {
  logger = noopLogger;
}

// ============================================
// SERVICES (shared with all plugins)
// ============================================

const services: PluginServices = {
  db: prisma,
  auth: {},
  config: env,
  logger,
};

// ============================================
// PLUGIN REGISTRY (singleton — stored on globalThis to survive
// Next.js bundle isolation between instrumentation and page rendering)
// ============================================

type PluginRegistry = Awaited<ReturnType<PluginLoader["loadAndBoot"]>>;

declare global {
  var __pixiedust_plugin_registry__: PluginRegistry | null | undefined;
  var __pixiedust_boot_promise__: Promise<void> | null | undefined;
}

/**
 * Dashboard core plugin — registers PD's built-in page components
 * following the reference app pattern.
 */
const dashboardCorePlugin: PixieDustPlugin = {
  name: "dashboard-core",
  version: "1.0.0",
  description: "Registers Pixie Dust built-in dashboard pages",
  register(ctx) {
    // ── Admin pages ──────────────────────────────────
    ctx.addPage({ path: "/dashboard/admin/health", title: "System Health", component: AdminDashboardPage, layout: "dashboard" });
    ctx.addNavItem({ label: "System Health", href: "/dashboard/admin/health", icon: "bar-chart", section: "admin", order: 70, requiredRole: "SUPER_ADMIN" });

    ctx.addPage({ path: "/dashboard/admin/users", title: "Users", component: UsersPage, layout: "dashboard" });
    ctx.addNavItem({ label: "Users", href: "/dashboard/admin/users", icon: "users", section: "admin", order: 10, requiredRole: "SUPER_ADMIN" });

    ctx.addPage({ path: "/dashboard/admin/tenants", title: "Tenants", component: TenantsPage, layout: "dashboard" });
    ctx.addNavItem({ label: "Tenants", href: "/dashboard/admin/tenants", icon: "building-2", section: "admin", order: 20, requiredRole: "SUPER_ADMIN" });

    ctx.addPage({ path: "/dashboard/admin/audit-logs", title: "Audit Logs", component: AuditLogPage, layout: "dashboard" });
    ctx.addNavItem({ label: "Audit Logs", href: "/dashboard/admin/audit-logs", icon: "scroll-text", section: "admin", order: 30, requiredRole: "SUPER_ADMIN" });

    ctx.addPage({ path: "/dashboard/admin/branding", title: "Branding", component: BrandingPage, layout: "dashboard" });
    ctx.addNavItem({ label: "Branding", href: "/dashboard/admin/branding", icon: "palette", section: "admin", order: 40, requiredRole: "SUPER_ADMIN" });

    ctx.addPage({ path: "/dashboard/admin/appearance", title: "Appearance", component: AppearancePage, layout: "dashboard" });
    ctx.addNavItem({ label: "Appearance", href: "/dashboard/admin/appearance", icon: "paintbrush", section: "admin", order: 50, requiredRole: "SUPER_ADMIN" });

    // ── Tenant pages ─────────────────────────────────
    ctx.addPage({ path: "/dashboard/team", title: "Team", component: TeamPage, layout: "dashboard" });
    ctx.addNavItem({ label: "Team", href: "/dashboard/team", icon: "users", section: "tenant", order: 50 });

    ctx.addPage({ path: "/dashboard/settings", title: "Workspace Settings", component: WorkspaceSettingsPage, layout: "dashboard" });
    ctx.addNavItem({ label: "Settings", href: "/dashboard/settings", icon: "settings", section: "tenant", order: 60 });

    // ── User pages ───────────────────────────────────
    ctx.addPage({ path: "/dashboard/profile", title: "Profile", component: ProfilePage, layout: "dashboard" });

    ctx.addPage({ path: "/dashboard/account", title: "Account", component: AccountPage, layout: "dashboard" });
  },
};

/**
 * Registered plugins — loaded in dependency-resolved order.
 */
const plugins: PixieDustPlugin[] = [
  dashboardCorePlugin,
  ...(env.NODE_ENV !== "production" ? [devtoolsPlugin] : []),
  stripeKitPlugin,
  lintpdfPlugin,
  lintpdfUsagePlugin,
  lintpdfApiKeysPlugin,
  lintpdfReportsPlugin,
  lintpdfAccountPlugin,
  lintpdfWebhooksPlugin,
  lintpdfEndpointsPlugin,
  lintpdfSuperAdminPlugin,
  lintpdfSiteAdminPlugin,
  lintpdfBillingPlugin,
];

/**
 * Boot all plugins. Safe to call multiple times — only boots once.
 */
export async function bootPlugins(): Promise<void> {
  if (globalThis.__pixiedust_plugin_registry__) return;
  if (globalThis.__pixiedust_boot_promise__)
    return globalThis.__pixiedust_boot_promise__;

  globalThis.__pixiedust_boot_promise__ = (async () => {
    const loader = new PluginLoader({
      services,
      disabledPlugins: env.DISABLED_PLUGINS,
    });

    globalThis.__pixiedust_plugin_registry__ = (await loader.loadAndBoot(
      plugins,
    )) as PluginRegistry;
    logger.info(`All plugins booted (${plugins.length} registered)`);
  })();

  await globalThis.__pixiedust_boot_promise__;
}

/**
 * Check if plugins have been booted.
 */
export function isBooted(): boolean {
  return !!globalThis.__pixiedust_plugin_registry__;
}

/**
 * Get the plugin registry (available after boot).
 */
export function getRegistry(): PluginRegistry | null {
  return globalThis.__pixiedust_plugin_registry__ ?? null;
}

/**
 * Ensure plugins are booted and return the registry.
 * Safe to call from layouts — boots lazily if instrumentation didn't run first.
 */
export async function ensureRegistry(): Promise<PluginRegistry> {
  if (globalThis.__pixiedust_plugin_registry__) {
    return globalThis.__pixiedust_plugin_registry__;
  }
  await bootPlugins();
  return globalThis.__pixiedust_plugin_registry__!;
}
