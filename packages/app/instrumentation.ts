/**
 * Next.js Instrumentation — runs once on server startup.
 *
 * Boots all Fairy Ring plugins and wires graceful shutdown handlers.
 * See: https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation
 */

export async function register() {
  // Only run in Node.js runtime (not Edge)
  if (typeof process.on !== "function") {
    return;
  }

  const { bootPlugins, getRegistry } = await import("./lib/plugins");

  await bootPlugins();

  // Wire graceful shutdown
  const shutdown = async () => {
    const registry = getRegistry();
    if (registry) {
      await registry.shutdown();
    }
    process.exit(0);
  };

  process.on("SIGTERM", () => void shutdown());
  process.on("SIGINT", () => void shutdown());
}
