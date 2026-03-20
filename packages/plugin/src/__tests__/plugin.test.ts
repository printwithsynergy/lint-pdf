import { describe, it, expect, vi, beforeEach } from "vitest";

describe("groundedPlugin", () => {
  function mockCtx() {
    return {
      addRoutes: vi.fn(),
      addNavItem: vi.fn(),
      addPage: vi.fn(),
      addPermission: vi.fn(),
      addRole: vi.fn(),
      addPublicPath: vi.fn(),
      addMigrations: vi.fn(),
      addMiddleware: vi.fn(),
      addTRPCRouter: vi.fn(),
      getPlugin: vi.fn(),
      on: vi.fn(),
      emit: vi.fn(),
      services: {
        logger: {
          info: vi.fn(),
          warn: vi.fn(),
          error: vi.fn(),
          debug: vi.fn(),
        },
        db: {},
        auth: {},
        config: {},
      },
    };
  }

  beforeEach(() => {
    vi.resetModules();
    delete process.env.GROUNDED_API_URL;
    delete process.env.GROUNDED_WEBHOOK_SECRET;
    delete process.env.GROUNDED_API_KEY;
  });

  it("skips registration if config is invalid", async () => {
    const mod = await import("../index");
    const ctx = mockCtx();
    mod.groundedPlugin.register(ctx);
    expect(ctx.services.logger.warn).toHaveBeenCalled();
    expect(ctx.addRoutes).not.toHaveBeenCalled();
  });

  it("registers routes, nav, pages, permissions, and custom role with valid config", async () => {
    process.env.GROUNDED_API_URL = "https://api.lintpdf.com";
    process.env.GROUNDED_WEBHOOK_SECRET = "a-very-long-test-secret";
    process.env.GROUNDED_API_KEY = "lpdf_test";

    const mod = await import("../index");
    const ctx = mockCtx();
    mod.groundedPlugin.register(ctx);

    // Custom OPERATOR role
    expect(ctx.addRole).toHaveBeenCalledWith("OPERATOR");

    // Core permissions (usage/waitlist moved to sub-plugins)
    expect(ctx.addPermission).toHaveBeenCalledWith("preflight:submit", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
    ]);
    expect(ctx.addPermission).toHaveBeenCalledWith("preflight:view", [
      "ADMIN",
      "OWNER",
      "MEMBER",
      "OPERATOR",
      "VIEWER",
    ]);
    expect(ctx.addPermission).toHaveBeenCalledWith("flight-plan:manage", [
      "ADMIN",
      "OWNER",
    ]);

    // 2 nav items (Preflight + Flight Plans — usage/waitlist moved to sub-plugins)
    expect(ctx.addNavItem).toHaveBeenCalledTimes(2);

    // 3 pages (Preflight list, Job detail, Flight Plans)
    expect(ctx.addPage).toHaveBeenCalledTimes(3);

    // 1 addRoutes call
    expect(ctx.addRoutes).toHaveBeenCalledTimes(1);

    // Public path for webhooks
    expect(ctx.addPublicPath).toHaveBeenCalledWith("/api/grounded/webhooks");

    // 2 hook listeners (job.completed + job.failed)
    expect(ctx.on).toHaveBeenCalledTimes(2);
  });

  it("registers 4 routes (1 webhook + 3 jobs + 1 profiles = 5)", async () => {
    process.env.GROUNDED_API_URL = "https://api.lintpdf.com";
    process.env.GROUNDED_WEBHOOK_SECRET = "a-very-long-test-secret";

    const mod = await import("../index");
    const ctx = mockCtx();
    mod.groundedPlugin.register(ctx);

    const [prefix, routes] = ctx.addRoutes.mock.calls[0];
    expect(prefix).toBe("/api/grounded");
    // 1 webhook + 3 jobs + 1 profiles = 5 (usage/waitlist routes moved to sub-plugins)
    expect(routes.length).toBe(5);
  });

  it("boot logs when client is ready", async () => {
    process.env.GROUNDED_API_URL = "https://api.lintpdf.com";
    process.env.GROUNDED_WEBHOOK_SECRET = "a-very-long-test-secret";

    const mod = await import("../index");
    const ctx = mockCtx();
    mod.groundedPlugin.register(ctx);
    await mod.groundedPlugin.boot?.(ctx);

    expect(ctx.services.logger.info).toHaveBeenCalledWith(
      "LintPDF plugin ready",
    );
  });

  it("shutdown clears client", async () => {
    process.env.GROUNDED_API_URL = "https://api.lintpdf.com";
    process.env.GROUNDED_WEBHOOK_SECRET = "a-very-long-test-secret";

    const mod = await import("../index");
    const ctx = mockCtx();
    mod.groundedPlugin.register(ctx);
    expect(mod.getClient()).not.toBeNull();

    await mod.groundedPlugin.shutdown?.(ctx);
    expect(mod.getClient()).toBeNull();
  });
});
