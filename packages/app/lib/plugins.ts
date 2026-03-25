/**
 * Plugin Bootstrap — Fairy Ring integration for the LintPDF app.
 *
 * Loads and boots all registered plugins on app startup.
 * Import this file in instrumentation.ts or layout to trigger bootstrap.
 */

import { env } from "@thinkneverland/pixie-dust-config";
import { prisma } from "@thinkneverland/pixie-dust-database";
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
 * Registered plugins — loaded in dependency-resolved order.
 */
const plugins: PixieDustPlugin[] = [
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
