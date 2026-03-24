import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { PluginContext } from "@thinkneverland/pixie-dust-fairy-ring";

// We need to test syncPlanToEngine and syncStripeIds which are not exported.
// They are called internally by the webhook handlers, so we test them through
// the plugin's webhook event handlers.

vi.mock("@thinkneverland/pixie-dust-stripe-kit", () => ({
  getStripe: vi.fn(),
  findOrCreateCustomer: vi.fn(),
  createCheckoutSession: vi.fn(),
  createPortalSession: vi.fn(),
  listInvoices: vi.fn(),
  getSubscription: vi.fn(),
}));

vi.mock("../src/metered.js", () => ({
  reportOverageUsage: vi.fn(),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

/** Create a mock PluginContext with all required service stubs. */
function createMockContext() {
  return {
    addRoutes: vi.fn(),
    addNavItem: vi.fn(),
    addPage: vi.fn(),
    addPermission: vi.fn(),
    addRole: vi.fn(),
    addPublicPath: vi.fn(),
    on: vi.fn(),
    emit: vi.fn(),
    services: {
      logger: {
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
      },
      db: {
        subscription: { findFirst: vi.fn() },
        stripeCustomer: { findFirst: vi.fn() },
      },
      auth: {},
      config: {},
    },
  };
}

/** Cast a mock context to PluginContext for use with plugin methods. */
function asPluginContext(
  ctx: ReturnType<typeof createMockContext>,
): PluginContext {
  return ctx as PluginContext;
}

describe("syncPlanToEngine and syncStripeIds (via webhook handlers)", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    mockFetch.mockReset();
    delete process.env.LINTPDF_API_URL;
    delete process.env.LINTPDF_ADMIN_API_KEY;
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  function getWebhookHandler(
    ctx: ReturnType<typeof createMockContext>,
    eventName: string,
  ) {
    const call = ctx.on.mock.calls.find((c: unknown[]) => c[0] === eventName);
    return call?.[1];
  }

  describe("syncPlanToEngine", () => {
    it("calls engine admin API with correct URL and plan", async () => {
      process.env.LINTPDF_API_URL = "https://engine.lintpdf.com";
      process.env.LINTPDF_ADMIN_API_KEY = "admin_key_123";
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "tenant_abc",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );
      await handler({
        data: {
          object: {
            customer: "cus_123",
            items: {
              data: [
                {
                  id: "si_item_1",
                  price: { lookup_key: "lintpdf_growth_monthly" },
                },
              ],
            },
          },
        },
      });

      // syncPlanToEngine should have been called
      expect(mockFetch).toHaveBeenCalledWith(
        "https://engine.lintpdf.com/api/v1/admin/tenants/tenant_abc/plan",
        expect.objectContaining({
          method: "PATCH",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            "X-Admin-Key": "admin_key_123",
          }),
          body: JSON.stringify({ plan: "growth" }),
        }),
      );
    });

    it("uses default localhost URL when LINTPDF_API_URL is not set", async () => {
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "tenant_xyz",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );
      await handler({
        data: {
          object: {
            customer: "cus_456",
            items: {
              data: [
                {
                  id: "si_1",
                  price: { lookup_key: "lintpdf_starter_monthly" },
                },
              ],
            },
          },
        },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/admin/tenants/tenant_xyz/plan",
        expect.anything(),
      );
    });

    it("maps plan lookup keys correctly", async () => {
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t1",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );

      // Test starter plan
      await handler({
        data: {
          object: {
            customer: "cus_1",
            items: {
              data: [
                {
                  id: "si_1",
                  price: { lookup_key: "lintpdf_starter_monthly" },
                },
              ],
            },
          },
        },
      });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({ plan: "starter" }),
        }),
      );

      mockFetch.mockClear();

      // Test enterprise plan
      await handler({
        data: {
          object: {
            customer: "cus_1",
            items: {
              data: [
                {
                  id: "si_1",
                  price: { lookup_key: "lintpdf_enterprise_monthly" },
                },
              ],
            },
          },
        },
      });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({ plan: "enterprise" }),
        }),
      );
    });

    it("defaults to free plan for unknown lookup key", async () => {
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t1",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );
      await handler({
        data: {
          object: {
            customer: "cus_1",
            items: {
              data: [{ id: "si_1", price: { lookup_key: "unknown_plan_key" } }],
            },
          },
        },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({ plan: "free" }),
        }),
      );
    });

    it("logs error when engine API returns non-ok response", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t1",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );
      await handler({
        data: {
          object: {
            customer: "cus_1",
            items: {
              data: [
                {
                  id: "si_1",
                  price: { lookup_key: "lintpdf_growth_monthly" },
                },
              ],
            },
          },
        },
      });

      expect(ctx.services.logger.error).toHaveBeenCalledWith(
        "Failed to sync plan/Stripe IDs to engine",
        expect.objectContaining({
          tenantId: "t1",
          error: expect.stringContaining("Failed to sync plan to engine: 500"),
        }),
      );
    });
  });

  describe("syncStripeIds", () => {
    it("calls engine admin API with stripe customer and subscription item IDs", async () => {
      process.env.LINTPDF_API_URL = "https://engine.lintpdf.com";
      // Return ok for both syncPlanToEngine and syncStripeIds calls
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t_sync",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );
      await handler({
        data: {
          object: {
            customer: "cus_sync_test",
            items: {
              data: [
                {
                  id: "si_sync_item",
                  price: { lookup_key: "lintpdf_growth_monthly" },
                },
              ],
            },
          },
        },
      });

      // Second fetch call should be syncStripeIds
      expect(mockFetch).toHaveBeenCalledWith(
        "https://engine.lintpdf.com/api/v1/admin/tenants/t_sync/stripe",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({
            stripe_customer_id: "cus_sync_test",
            stripe_subscription_item_id: "si_sync_item",
          }),
        }),
      );
    });

    it("logs error when syncStripeIds fails", async () => {
      // syncPlanToEngine succeeds, syncStripeIds fails
      mockFetch
        .mockResolvedValueOnce({ ok: true }) // syncPlanToEngine
        .mockResolvedValueOnce({
          ok: false,
          status: 403,
          statusText: "Forbidden",
        }); // syncStripeIds

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t_fail",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );
      await handler({
        data: {
          object: {
            customer: "cus_fail",
            items: {
              data: [
                {
                  id: "si_fail",
                  price: { lookup_key: "lintpdf_growth_monthly" },
                },
              ],
            },
          },
        },
      });

      expect(ctx.services.logger.error).toHaveBeenCalledWith(
        "Failed to sync plan/Stripe IDs to engine",
        expect.objectContaining({
          tenantId: "t_fail",
          error: expect.stringContaining(
            "Failed to sync Stripe IDs to engine: 403",
          ),
        }),
      );
    });

    it("does not include admin key header when LINTPDF_ADMIN_API_KEY is not set", async () => {
      delete process.env.LINTPDF_ADMIN_API_KEY;
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t_nokey",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.updated",
      );
      await handler({
        data: {
          object: {
            customer: "cus_nokey",
            items: {
              data: [
                {
                  id: "si_nokey",
                  price: { lookup_key: "lintpdf_growth_monthly" },
                },
              ],
            },
          },
        },
      });

      // Check that X-Admin-Key is NOT in the headers
      const fetchCalls = mockFetch.mock.calls;
      for (const call of fetchCalls) {
        const headers = call[1]?.headers;
        expect(headers).not.toHaveProperty("X-Admin-Key");
      }
    });
  });

  describe("subscription.deleted webhook", () => {
    it("syncs plan to free when subscription is deleted", async () => {
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t_deleted",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.deleted",
      );
      await handler({
        data: {
          object: { customer: "cus_deleted" },
        },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/admin/tenants/t_deleted/plan"),
        expect.objectContaining({
          body: JSON.stringify({ plan: "free" }),
        }),
      );

      expect(ctx.services.logger.info).toHaveBeenCalledWith(
        "Tenant downgraded to free",
        { tenantId: "t_deleted" },
      );
    });

    it("logs error when downgrade sync fails", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t_fail_down",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.deleted",
      );
      await handler({
        data: {
          object: { customer: "cus_fail_down" },
        },
      });

      expect(ctx.services.logger.error).toHaveBeenCalledWith(
        "Failed to downgrade tenant plan in engine",
        expect.objectContaining({
          tenantId: "t_fail_down",
          error: expect.stringContaining("500"),
        }),
      );
    });
  });

  describe("engineAdminUrl", () => {
    it("strips trailing slash from LINTPDF_API_URL", async () => {
      process.env.LINTPDF_API_URL = "https://engine.lintpdf.com/";
      mockFetch.mockResolvedValue({ ok: true });

      const ctx = createMockContext();
      const mod = await import("../src/index.js");
      mod.lintpdfBillingPlugin.register?.(asPluginContext(ctx));

      ctx.services.db.stripeCustomer.findFirst.mockResolvedValue({
        tenantId: "t_slash",
      });

      const handler = getWebhookHandler(
        ctx,
        "stripe:customer.subscription.deleted",
      );
      await handler({
        data: { object: { customer: "cus_slash" } },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "https://engine.lintpdf.com/api/v1/admin/tenants/t_slash/plan",
        expect.anything(),
      );
    });
  });
});
